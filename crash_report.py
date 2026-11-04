"""Journal de l'app et rapport d'erreur : quand l'app plante, elle dit pourquoi,
et le rapport part par e-mail en un geste.

Fichiers (dossier logs/ de l'app sur Android, ~/.<nom de l'app> sur ordinateur,
par exemple ~/.rifffinder) :

- `app.log` : le journal, ce que l'app a fait (démarrage chronométré, pages,
  réglages changés, son, et ce que l'app y écrit elle-même, avertissements
  de Qt, erreurs). 150 Ko au plus, plus l'ancien `app.log.1` ;
- `crash.log` : les erreurs Python, avec la pile d'appels ;
- `native.log` : si le processus meurt (plantage dans Qt ou Android),
  faulthandler y écrit la pile Python du moment ;
- `qt.log` : les avertissements de Qt du lancement (souvent la cause d'un
  plantage natif) ;
- `startup.txt` : l'étape du démarrage en cours ; s'il est encore là au
  lancement suivant, l'app s'est arrêtée pendant le démarrage ;
- `exit_reasons.txt` (Android 11 et plus) : pourquoi Android a arrêté l'app
  les dernières fois (plantage Java ou natif, « ne répond pas », mémoire…),
  écrit par l'activité Java (android/java/…/ExitReasons.java) avant le
  démarrage de Python, avec la trace du plantage (`exit_<date>.trace`).

Une erreur au démarrage s'affiche tout de suite (au lieu de fermer l'app). Un
plantage s'affiche au lancement suivant. Réglages › « Error report » montre le
rapport à tout moment. « Send by email » ouvre l'app d'e-mail du téléphone avec
le rapport, adressé à SUPPORT_EMAIL (app_info.py) : rien ne part sans que
l'utilisateur appuie sur Envoyer. Le rapport ne contient que des informations
techniques (versions, modèle du téléphone, réglages, erreurs, journal) : ni
données de l'utilisateur, ni sons, ni noms de fichiers.

Ce module ne dépend que de la bibliothèque standard, de PySide6 et de
appcore/app.py (qui lit app_info.py sans rien importer d'autre) : il doit
marcher même si le reste de l'app ne se charge pas.
"""

from __future__ import annotations

import faulthandler
import logging
import os
import platform
import re
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path
from urllib.parse import quote

MAX_LOG = 40_000        # octets gardés par fichier d'erreurs
LAUNCH_MARK = "=== launch"  # sépare les lancements dans crash.log et app.log
STARTUP_GRACE_MS = 3000  # l'app est « démarrée » 3 s après l'affichage de la fenêtre
JOURNAL = "app.log"
JOURNAL_MAX = 150_000   # au-delà, le journal devient app.log.1 (un seul ancien gardé)
EXIT_FILE = "exit_reasons.txt"       # écrit par l'activité Java au démarrage
EXIT_PREV = "exit_reasons_prev.txt"  # le dernier lu, pour le rapport
KEEP_TRACES = 3         # traces de plantage Android gardées
QT_MESSAGES_MAX = 300   # avertissements de Qt écrits dans le journal, par lancement
# Réglages recopiés dans le rapport (pour refaire le problème dans les mêmes
# conditions) : ceux du socle, le son, puis REPORT_SETTINGS de app_info.py
SETTING_KEYS = ("language", "theme", "notation")

# Causes d'arrêt d'Android (ApplicationExitInfo.REASON_*) qui sont un problème :
# plantage Java, plantage natif, « ne répond pas », échec au lancement, ressources
PROBLEM_REASONS = {4, 5, 6, 7, 9}
LOW_MEMORY = 3          # manque de mémoire : un problème si l'app était à l'écran
VISIBLE = 200           # importance ≤ 200 : l'app était à l'écran

# Taille des parties du rapport (caractères) : à l'écran, et dans l'e-mail
# (une adresse « mailto: » trop longue est coupée par certaines apps d'e-mail)
SCREEN_BUDGET = {"previous": 20_000, "errors": 15_000, "journal": 20_000, "android": 8_000}
EMAIL_BUDGET = {"previous": 7_000, "errors": 5_000, "journal": 7_000, "android": 2_500}

log = logging.getLogger("crash_report")

_dir: Path | None = None
_native_file = None
_qt_file = None
_previous = ""          # rapport du lancement précédent (vide : tout allait bien)
_installed = False
_started = time.monotonic()
_android_log_since = time.time()   # le journal d'Android du rapport commence ici
_startup_logged = False


# =========================================================================================
# Dossier et fichiers
# =========================================================================================

def on_android() -> bool:
    return (hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ
            or "ANDROID_PRIVATE" in os.environ)


def log_dir() -> Path:
    """Un dossier où l'on peut écrire : files/logs sur Android (privé à l'app,
    gardé quand l'app est mise à jour, et connu de l'activité Java),
    ~/.<nom de l'app> sur un ordinateur."""
    global _dir
    if _dir is not None:
        return _dir
    candidates = []
    if on_android():
        if os.environ.get("ANDROID_PRIVATE"):
            candidates.append(Path(os.environ["ANDROID_PRIVATE"]) / "logs")
        candidates.append(Path(__file__).resolve().parent.parent)   # dossier de l'app
    folder_name = _app_slug()
    candidates += [Path.home() / f".{folder_name}", Path(tempfile.gettempdir()) / folder_name]
    for folder in candidates:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            probe = folder / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            _dir = folder
            return folder
        except OSError:
            continue
    _dir = Path(tempfile.gettempdir())
    return _dir


def _read(name: str) -> str:
    try:
        return (log_dir() / name).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _unlink(name: str) -> None:
    try:
        (log_dir() / name).unlink()
    except OSError:
        pass


def _tail(text: str, limit: int = MAX_LOG) -> str:
    """La fin d'un texte (le plus récent), coupée au début d'une ligne."""
    if len(text) <= limit:
        return text
    cut = text[-limit:]
    return "…\n" + cut[cut.find("\n") + 1:] if "\n" in cut else "…" + cut


def _head(text: str, limit: int) -> str:
    """Le début d'un texte (le plus important d'abord)."""
    return text if len(text) <= limit else text[:limit].rsplit("\n", 1)[0] + "\n…"


def _append(name: str, text: str) -> None:
    try:
        path = log_dir() / name
        old = _read(name)
        path.write_text(_tail(old + text, MAX_LOG), encoding="utf-8")
    except OSError:
        pass


def _stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _elapsed_ms() -> int:
    return int((time.monotonic() - _started) * 1000)


# =========================================================================================
# Le téléphone, l'app, les réglages
# =========================================================================================

def _system_property(name: str) -> str:
    """Propriété d'Android (modèle, version…), sans autorisation particulière."""
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so")
        get = getattr(libc, "__system_property_get")
        buffer = ctypes.create_string_buffer(128)
        get(name.encode("ascii"), buffer)
        value = buffer.value.decode("utf-8", errors="replace").strip()
        if value:
            return value
    except Exception:  # noqa: BLE001
        pass
    try:
        import subprocess
        out = subprocess.run(["getprop", name], capture_output=True, timeout=2)
        return out.stdout.decode("utf-8", errors="replace").strip()
    except Exception:  # noqa: BLE001
        return ""


def device_name() -> str:
    """« Google Pixel 7 », « samsung SM-A515F »… ou le système de l'ordinateur."""
    if on_android():
        maker = _system_property("ro.product.manufacturer")
        model = _system_property("ro.product.model")
        if model.lower().startswith(maker.lower()):
            maker = ""
        return " ".join(p for p in (maker, model) if p) or "Android"
    return f"{platform.system()} {platform.release()}".strip()


def device_summary() -> str:
    if on_android():
        release = _system_property("ro.build.version.release") or "?"
        api = _system_property("ro.build.version.sdk")
        if not api and hasattr(sys, "getandroidapilevel"):
            api = str(sys.getandroidapilevel())
        abi = _system_property("ro.product.cpu.abi") or platform.machine()
        return f"{device_name()} · Android {release} (API {api or '?'}) · {abi}"
    return f"{platform.platform()} · {platform.machine()}"


def _app_slug() -> str:
    try:
        from appcore import app as config
        return config.slug()
    except Exception:  # noqa: BLE001
        return "app"


def app_title() -> str:
    """« RiffFinder 1.2.0 » (le nom et la version de app_info.py)."""
    try:
        from appcore import app as config
        return f"{config.name()} {config.version()}"
    except Exception:  # noqa: BLE001
        return "?"


def setting_keys() -> tuple[str, ...]:
    try:
        from appcore import app as config
        return SETTING_KEYS + (str(config.get("SOUND_SETTING")),) + tuple(config.get("REPORT_SETTINGS"))
    except Exception:  # noqa: BLE001
        return SETTING_KEYS


def versions_summary() -> str:
    app = app_title()
    try:
        import appcore
        core = getattr(appcore, "VERSION", "?")
    except Exception:  # noqa: BLE001
        core = "?"
    try:
        import PySide6
        pyside = getattr(PySide6, "__version__", "?")
    except Exception:  # noqa: BLE001
        pyside = "?"
    try:
        from PySide6.QtCore import qVersion
        qt = qVersion()
    except Exception:  # noqa: BLE001
        qt = "?"
    return (f"{app} · appcore {core} · Python {platform.python_version()} · "
            f"PySide6 {pyside} · Qt {qt}")


def settings_summary() -> str:
    """Langue et réglages (vide tant que l'application Qt n'est pas créée)."""
    try:
        from PySide6.QtCore import QCoreApplication, QSettings
        if QCoreApplication.instance() is None:
            return ""
        settings = QSettings()
        parts = []
        for key in setting_keys():
            value = settings.value(key)
            if value is not None:
                parts.append(f"{key}={value}")
    except Exception:  # noqa: BLE001
        return ""
    i18n = sys.modules.get("appcore.i18n")
    if i18n is not None and hasattr(i18n, "language"):
        parts.insert(0, f"shown in {i18n.language()}")
    return ", ".join(parts) or "(defaults)"


def screen_summary() -> str:
    try:
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return ""
        size = screen.size()
        return (f"{size.width()}x{size.height()} px, ratio {screen.devicePixelRatio():g}, "
                f"{screen.logicalDotsPerInch():.0f} dpi")
    except Exception:  # noqa: BLE001
        return ""


def environment() -> list[str]:
    lines = [versions_summary(), "Device: " + device_summary()]
    screen = screen_summary()
    if screen:
        lines.append("Screen: " + screen)
    settings = settings_summary()
    if settings:
        lines.append("Settings: " + settings)
    lines.append(f"Report made {_stamp()}, {_elapsed_ms() // 1000} s after launch")
    return lines


def log_context() -> None:
    """Réglages et écran dans le journal (une fois la fenêtre affichée)."""
    settings, screen = settings_summary(), screen_summary()
    if settings:
        log.info("settings: %s", settings)
    if screen:
        log.info("screen: %s", screen)


# =========================================================================================
# Installation (tout au début de main.py)
# =========================================================================================

def install() -> None:
    """À appeler avant d'importer le reste de l'app."""
    global _native_file, _qt_file, _previous, _installed
    if _installed:
        return
    _installed = True
    folder = log_dir()
    _setup_journal(folder)
    log.info("%s %s ===", LAUNCH_MARK, _stamp())
    log.info("%s", versions_summary())
    log.info("device: %s", device_summary())
    _previous = _collect_previous()
    # Plantage natif : faulthandler écrit la pile dans native.log (vide si tout va bien)
    try:
        _native_file = open(folder / "native.log", "w", encoding="utf-8")  # noqa: SIM115
        faulthandler.enable(file=_native_file, all_threads=True)
    except Exception:  # noqa: BLE001
        _native_file = None
    # Messages de Qt de ce lancement (le précédent est gardé dans qt_prev.log)
    try:
        if (folder / "qt.log").exists():
            os.replace(folder / "qt.log", folder / "qt_prev.log")
        _qt_file = open(folder / "qt.log", "w", encoding="utf-8", buffering=1)  # noqa: SIM115
    except Exception:  # noqa: BLE001
        _qt_file = None
    _append("crash.log", f"{LAUNCH_MARK} {_stamp()} ===\n")
    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
    step("starting")


class _JournalHandler(logging.FileHandler):
    """Le journal app.log : au-delà de JOURNAL_MAX octets, il devient app.log.1
    (l'ancien app.log.1 est remplacé) et un nouveau commence."""

    def emit(self, record) -> None:   # appelé sous le verrou du handler
        try:
            if self.stream is not None and self.stream.tell() > JOURNAL_MAX:
                self.stream.close()
                self.stream = None      # FileHandler.emit le rouvre
                os.replace(self.baseFilename, self.baseFilename + ".1")
        except (OSError, ValueError):
            pass
        super().emit(record)


def _setup_journal(folder: Path) -> None:
    root = logging.getLogger()
    if any(isinstance(h, _JournalHandler) for h in root.handlers):
        return
    fmt = logging.Formatter("%(asctime)s.%(msecs)03d %(levelname).1s %(name)s: %(message)s",
                            "%m-%d %H:%M:%S")
    try:
        handler = _JournalHandler(folder / JOURNAL, encoding="utf-8")
        handler.setFormatter(fmt)
        root.addHandler(handler)
    except OSError:
        pass
    # Avertissements et erreurs aussi dans la console (logcat sur Android)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(fmt)
    root.addHandler(console)
    root.setLevel(logging.INFO)
    logging.captureWarnings(True)     # warnings.warn(...) -> journal


def _journal_handler() -> _JournalHandler | None:
    return next((h for h in logging.getLogger().handlers if isinstance(h, _JournalHandler)), None)


def journal_tail(limit: int) -> str:
    """La fin du journal (ancien fichier compris), le plus récent en dernier."""
    handler = _journal_handler()
    if handler is not None:
        handler.flush()
    text = _read(JOURNAL + ".1") + _read(JOURNAL)
    return _tail(text.strip(), limit) if text.strip() else "(empty)"


def _collect_previous() -> str:
    """Ce qui s'est mal passé au lancement précédent ("" si rien)."""
    parts = []
    native = _read("native.log").strip()
    startup = _read("startup.txt").strip()
    fatal = _read("fatal.txt").strip()
    exits = _take_exit_reasons()
    problems = [e for e in exits if _is_problem(e)]
    if fatal:
        parts.append("The app could not start:\n" + fatal)
    if native:
        parts.append("The app stopped (native crash). Python stack at that moment:\n" + native)
    if startup and not fatal:
        parts.append(f"The app stopped while starting, at step: {startup}")
    if problems:
        parts.append("Android says the app stopped:\n"
                     + "\n\n".join(e["text"] for e in problems))
    if not parts:
        return ""
    crashes = _logcat("-b", "crash", "-v", "time", "-t", "300").strip()
    if crashes:
        parts.append("Android crash log (this app):\n" + _tail(crashes, 8000))
    qt = _read("qt.log").strip()
    if qt:
        lines = qt.splitlines()[-40:]
        parts.append("Last Qt messages:\n" + "\n".join(lines))
    errors = _read("crash.log").rsplit(LAUNCH_MARK, 1)[-1].split("\n", 1)[-1].strip()
    if errors:  # celles du lancement précédent seulement
        parts.append("Python errors of that launch:\n" + _tail(errors, 6000))
    for name in ("fatal.txt", "startup.txt"):
        _unlink(name)
    log.warning("the previous launch went wrong: %s", parts[0].splitlines()[0])
    return "\n\n".join(parts)


def previous_crash() -> str:
    return _previous


def step(name: str) -> None:
    """Note l'étape du démarrage en cours (effacée quand l'app a bien démarré)."""
    try:
        (log_dir() / "startup.txt").write_text(f"{name} ({_stamp()})", encoding="utf-8")
    except OSError:
        pass
    log.info("startup: %s (%d ms)", name, _elapsed_ms())


def startup_done() -> None:
    global _startup_logged
    _unlink("startup.txt")
    if not _startup_logged:
        _startup_logged = True
        log.info("startup finished (%d ms)", _elapsed_ms())


def record_fatal(text: str) -> None:
    """Erreur qui empêche le démarrage : gardée pour le prochain lancement aussi."""
    _append("crash.log", f"[{_stamp()}] startup failed\n{text}\n")
    try:
        (log_dir() / "fatal.txt").write_text(text, encoding="utf-8")
    except OSError:
        pass
    log.error("the app could not start: %s", _last_line(text))


def _last_line(text: str) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1].strip() if lines else "?"


def _excepthook(kind, value, tb) -> None:
    text = "".join(traceback.format_exception(kind, value, tb))
    _append("crash.log", f"[{_stamp()}]\n{text}\n")
    log.error("Python error (details below, in Python errors): %s", _last_line(text))
    sys.__excepthook__(kind, value, tb)


def _thread_excepthook(args) -> None:
    text = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    name = getattr(args.thread, "name", "?")
    _append("crash.log", f"[{_stamp()}] in thread {name}\n{text}\n")
    log.error("Python error in thread %s: %s", name, _last_line(text))
    threading.__excepthook__(args)


# =========================================================================================
# Causes d'arrêt données par Android (écrites par android/java/…/ExitReasons.java)
# =========================================================================================

_EXIT_KEYS = re.compile(r"^reason=(-?\d+) importance=(-?\d+)(?: status=(-?\d+))?(?: trace=(\S+))?\s*$")


def parse_exit_reasons(text: str) -> list[dict]:
    """Les arrêts décrits par l'activité Java : un bloc « === date · cause »
    par arrêt, avec une ligne « reason=… importance=… [trace=fichier] »."""
    exits = []
    for block in re.split(r"(?m)^(?==== )", text):
        block = block.strip()
        if not block.startswith("=== "):
            continue
        entry = {"reason": -1, "importance": 0, "trace": None}
        lines = []
        for line in block.splitlines():
            match = _EXIT_KEYS.match(line.strip())
            if match:
                entry["reason"] = int(match.group(1))
                entry["importance"] = int(match.group(2))
                entry["trace"] = match.group(4)
            else:
                lines.append(line)
        entry["text"] = "\n".join(lines)
        exits.append(entry)
    return exits


def _is_problem(entry: dict) -> bool:
    return entry["reason"] in PROBLEM_REASONS or (
        entry["reason"] == LOW_MEMORY and 0 < entry["importance"] <= VISIBLE)


def _take_exit_reasons() -> list[dict]:
    """Lit (puis range) ce que l'activité Java a écrit sur les derniers arrêts."""
    text = _read(EXIT_FILE)
    if not text.strip():
        return []
    folder = log_dir()
    exits = parse_exit_reasons(text)
    for entry in exits:
        if entry["trace"] and "/" not in entry["trace"]:
            summary = trace_summary(folder / entry["trace"])
            if summary:
                entry["text"] += "\n" + summary
        first = entry["text"].splitlines()[0].lstrip("= ") if entry["text"] else "?"
        (log.warning if _is_problem(entry) else log.info)("previous stop (Android): %s", first)
    try:
        (folder / EXIT_PREV).write_text("\n\n".join(e["text"] for e in exits), encoding="utf-8")
    except OSError:
        pass
    _unlink(EXIT_FILE)
    traces = sorted(folder.glob("exit_*.trace"), key=lambda p: p.name, reverse=True)
    for old in traces[KEEP_TRACES:]:
        try:
            old.unlink()
        except OSError:
            pass
    return exits


def trace_summary(path: Path, max_lines: int = 120) -> str:
    """Trace d'un arrêt : texte pour « ne répond pas » (ANR), tombstone
    (protobuf) pour un plantage natif."""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if not data:
        return ""
    sample = data[:4096]
    if b"\x00" not in sample and sum(32 <= b < 127 or b in b"\r\n\t" for b in sample) > 0.9 * len(sample):
        lines = data.decode("utf-8", errors="replace").splitlines()
        more = "\n…" if len(lines) > max_lines else ""
        return "Trace:\n" + "\n".join(lines[:max_lines]) + more
    return "Native crash:\n" + tombstone_summary(data)


def _varint(data: bytes, i: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        if i >= len(data) or shift > 70:
            raise ValueError("bad varint")
        byte = data[i]
        i += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, i
        shift += 7


def _proto_fields(data: bytes) -> list[tuple[int, object]]:
    """Champs d'un message protobuf : (numéro, entier ou octets). S'arrête sans
    erreur sur un message tronqué (la trace est limitée en taille)."""
    fields: list[tuple[int, object]] = []
    i = 0
    try:
        while i < len(data):
            key, i = _varint(data, i)
            number, wire = key >> 3, key & 7
            if wire == 0:
                value, i = _varint(data, i)
            elif wire == 2:
                length, i = _varint(data, i)
                if i + length > len(data):
                    break
                value, i = data[i:i + length], i + length
            elif wire == 1:
                value, i = int.from_bytes(data[i:i + 8], "little"), i + 8
            elif wire == 5:
                value, i = int.from_bytes(data[i:i + 4], "little"), i + 4
            else:
                break
            fields.append((number, value))
    except ValueError:
        pass
    return fields


def _int(fields: list[tuple[int, object]], number: int) -> int | None:
    """Premier champ entier `number` d'un message (None s'il manque)."""
    return next((v for n, v in fields if n == number and isinstance(v, int)), None)


def _bytes(fields: list[tuple[int, object]], number: int) -> bytes | None:
    """Premier champ texte / sous-message `number` d'un message."""
    return next((v for n, v in fields if n == number and isinstance(v, bytes)), None)


def _text(value) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else ""


def tombstone_summary(data: bytes, max_frames: int = 40) -> str:
    """Signal, message d'abandon et pile du fil qui a planté, lus dans le
    tombstone d'Android (system/core/debuggerd/proto/tombstone.proto). Si la
    lecture échoue : les textes lisibles de la trace."""
    lines = []
    try:
        top = _proto_fields(data)
        crashed = _int(top, 6)
        signal = _bytes(top, 10)
        if signal is not None:
            s = _proto_fields(signal)
            text = f"Signal {_int(s, 1)} ({_text(_bytes(s, 2))})"
            code = _text(_bytes(s, 4))
            if code:
                text += f", code {code}"
            if _int(s, 8):
                text += f", fault address 0x{_int(s, 9) or 0:x}"
            lines.append(text)
        abort = _text(_bytes(top, 14))
        if abort:
            lines.append("Abort message: " + abort)
        threads = {}
        for number, entry in top:
            if number == 16 and isinstance(entry, bytes):
                e = _proto_fields(entry)
                value = _bytes(e, 2)
                if value is not None:
                    threads[_int(e, 1)] = value
        thread = threads.get(crashed) or next(iter(threads.values()), None)
        frames = 0
        if thread is not None:
            t = _proto_fields(thread)
            lines.append(f"Thread {_int(t, 1)} \"{_text(_bytes(t, 2))}\":")
            for number, frame in t:
                if number != 4 or not isinstance(frame, bytes):
                    continue
                if frames >= max_frames:
                    lines.append("  …")
                    break
                f = _proto_fields(frame)
                where = _text(_bytes(f, 6)).rsplit("/", 1)[-1] or "?"
                function = _text(_bytes(f, 4))
                line = f"  #{frames:02d} pc {_int(f, 1) or 0:08x}  {where}"
                if function:
                    line += f" ({function}+{_int(f, 5) or 0})"
                lines.append(line)
                frames += 1
        if frames:
            return "\n".join(lines)
    except Exception:  # noqa: BLE001 — format inattendu : les textes lisibles
        pass
    strings = []
    for raw in re.findall(rb"[\x20-\x7e]{6,}", data):
        text = raw.decode("ascii")
        if text not in strings:
            strings.append(text)
        if len(strings) >= 80:
            break
    return "\n".join(lines + ["(readable text of the trace)"] + strings)


def _logcat(*args: str, timeout: float = 3.0) -> str:
    """Journal d'Android : sans autorisation, une app n'y lit que ses propres lignes."""
    if not on_android():
        return ""
    exe = "/system/bin/logcat" if os.path.exists("/system/bin/logcat") else "logcat"
    try:
        import subprocess
        out = subprocess.run([exe, "-d", *args], capture_output=True, timeout=timeout)
    except Exception:  # noqa: BLE001 — pas de logcat : le rapport s'en passe
        return ""
    return out.stdout.decode("utf-8", errors="replace")


def android_log(limit: int) -> str:
    """Avertissements et erreurs d'Android pour l'app, depuis ce lancement."""
    since = time.strftime("%m-%d %H:%M:%S.000", time.localtime(_android_log_since))
    text = _logcat("-v", "time", "-T", since, "*:W").strip()
    return _tail(text, limit) if text else ""


# =========================================================================================
# Messages de Qt
# =========================================================================================

def install_qt_messages(app) -> None:
    """Garde les avertissements de Qt dans qt.log et dans le journal (et
    toujours dans la console / logcat). Retiré à la fermeture : rien n'est
    appelé pendant l'arrêt de Qt."""
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except ImportError:
        return
    qt_log = logging.getLogger("qt")
    state = {"last": None, "repeats": 0, "count": 0}

    def handler(mode, context, message) -> None:
        try:
            if mode == QtMsgType.QtDebugMsg:
                return
            name = getattr(mode, "name", str(mode)).replace("Qt", "").replace("Msg", "")
            line = f"{time.strftime('%H:%M:%S')} {name}: {message}"
            sys.stderr.write(line + "\n")
            if _qt_file is not None:
                _qt_file.write(line + "\n")
            # Journal : un message répété n'est écrit qu'une fois, et pas plus de
            # QT_MESSAGES_MAX par lancement
            if message == state["last"]:
                state["repeats"] += 1
                return
            if state["repeats"]:
                qt_log.info("(previous message repeated %d times)", state["repeats"])
            state["last"], state["repeats"] = message, 0
            state["count"] += 1
            if state["count"] <= QT_MESSAGES_MAX:
                level = logging.INFO if name == "Info" else logging.WARNING \
                    if name == "Warning" else logging.ERROR
                qt_log.log(level, "%s", message)
        except Exception:  # noqa: BLE001 — ne jamais lever dans le gestionnaire
            pass

    try:
        qInstallMessageHandler(handler)
        app.aboutToQuit.connect(lambda: qInstallMessageHandler(None))
    except Exception:  # noqa: BLE001
        pass


# =========================================================================================
# Rapport complet (bouton des réglages, e-mail)
# =========================================================================================

def full_report(compact: bool = False) -> str:
    """Tout ce qu'on sait, pour l'envoyer à qui corrige l'app. `compact` : la
    version de l'e-mail (parties plus courtes)."""
    budget = EMAIL_BUDGET if compact else SCREEN_BUDGET
    parts = ["\n".join(environment())]
    if _previous:
        parts.append("=== Previous launch ===\n" + _head(_previous, budget["previous"]))
    errors = python_errors()
    parts.append("=== Python errors (recent launches) ===\n"
                 + (_tail(errors, budget["errors"]) if errors else "(none)"))
    stops = _read(EXIT_PREV).strip()
    if stops and stops.splitlines()[0] not in _previous:
        parts.append("=== Last stop recorded by Android ===\n" + _head(stops, budget["previous"] // 2))
    parts.append("=== App log (most recent last) ===\n" + journal_tail(budget["journal"]))
    android = android_log(budget["android"])
    if android:
        parts.append("=== Android log for the app, this launch (warnings, errors) ===\n" + android)
    return "\n\n".join(parts)


def python_errors() -> str:
    """Les erreurs de crash.log, chaque lancement qui en a eu sous sa date."""
    blocks = re.split(rf"(?m)^(?={re.escape(LAUNCH_MARK)})", _read("crash.log"))
    kept = []
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if any(not line.startswith(LAUNCH_MARK) for line in lines):
            kept.append("\n".join(lines))
    return "\n".join(kept).strip()


def clear_logs() -> None:
    """Efface les erreurs, le journal et les traces (après un envoi, par exemple)."""
    global _previous, _android_log_since
    _previous = ""
    _android_log_since = time.time()
    for name in ("crash.log", "qt_prev.log", "fatal.txt", EXIT_PREV, JOURNAL + ".1"):
        _unlink(name)
    for trace in log_dir().glob("exit_*.trace"):
        try:
            trace.unlink()
        except OSError:
            pass
    handler = _journal_handler()
    if handler is not None:
        handler.acquire()
        try:
            if handler.stream is not None:
                handler.stream.seek(0)
                handler.stream.truncate()
        except (OSError, ValueError):
            pass
        finally:
            handler.release()
    log.info("logs cleared (%s)", versions_summary())


def support_email() -> str:
    try:
        from appcore import app as config
        return config.support_email()
    except Exception:  # noqa: BLE001
        return ""


def email_subject() -> str:
    app = app_title()
    kind = "crash report" if _previous else "error report"
    return f"{app} {kind} ({device_name()})"


def email_url(report: str, intro: str = "") -> str:
    """Adresse « mailto: » : destinataire, sujet et texte déjà remplis."""
    body = (intro + "\n\n\n" if intro else "") + "---- report ----\n" + report
    return (f"mailto:{support_email()}?subject={quote(email_subject(), safe='')}"
            f"&body={quote(body, safe='')}")


def send_by_email(report: str, intro: str = "") -> bool:
    """Ouvre l'app d'e-mail avec le rapport (l'utilisateur le relit et l'envoie).
    False si aucune app d'e-mail ne s'est ouverte."""
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        opened = bool(QDesktopServices.openUrl(QUrl(email_url(report, intro))))
    except Exception:  # noqa: BLE001
        log.exception("the email app could not be opened")
        opened = False
    log.info("report handed to the email app" if opened else "no email app to send the report")
    return opened


# =========================================================================================
# Fenêtre du rapport
# =========================================================================================

def report_view(text: str, title: str, on_close=None, parent=None, can_clear: bool = False):
    """Panneau : titre, explication, texte du rapport (sélectionnable), boutons
    « Send by email », Copy, (Clear) et Close. Ne dépend que de PySide6."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QGuiApplication
    from PySide6.QtWidgets import (
        QFrame,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )

    try:   # textes de l'écran traduits ; le rapport lui-même reste en anglais
        from appcore.i18n import tr
    except Exception:  # noqa: BLE001 — le rapport doit s'afficher quoi qu'il arrive
        def tr(text: str, /, **fields) -> str:
            return text.format(**fields) if fields else text

    email = support_email()
    current = {"text": text}
    view = QFrame(parent)
    view.setObjectName("overlay")
    heading = QLabel(title)
    heading.setObjectName("panelTitle")
    heading.setWordWrap(True)
    hint = QLabel(tr("Send by email opens your email app with this report, addressed to "
                     "{email}. Nothing is sent until you press Send.", email=email))
    hint.setObjectName("muted")
    hint.setWordWrap(True)
    body = QLabel(text)
    body.setTextFormat(Qt.TextFormat.PlainText)
    body.setWordWrap(True)
    body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    mono = QFont("monospace")
    mono.setStyleHint(QFont.StyleHint.Monospace)
    mono.setPixelSize(11)
    body.setFont(mono)
    holder = QWidget()
    holder_layout = QVBoxLayout(holder)
    holder_layout.setContentsMargins(4, 4, 4, 4)
    holder_layout.addWidget(body)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(holder)
    try:
        from PySide6.QtWidgets import QScroller
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
    except Exception:  # noqa: BLE001
        pass
    send_button = QPushButton(tr("Send by email"))
    copy_button = QPushButton(tr("Copy"))
    clear_button = None
    if can_clear:
        clear_button = QPushButton(tr("Clear"))
        clear_button.setToolTip(tr("Erase the errors and the log (after sending them)"))
    close_button = QPushButton(tr("Close"))
    status = QLabel("")
    status.setObjectName("muted")
    status.setWordWrap(True)

    def send() -> None:
        # le texte complet est copié aussi : si l'app d'e-mail coupe le rapport, on le colle
        QGuiApplication.clipboard().setText(current["text"])
        report = full_report(compact=True)
        intro = tr("What were you doing when the problem happened? (optional)")
        if send_by_email(report, intro):
            status.setText(tr("Your email app opens. The report is also copied, in case it is cut."))
        else:
            status.setText(tr("No email app found. The report is copied: paste it in an email "
                              "to {email}.", email=email))

    def copy() -> None:
        QGuiApplication.clipboard().setText(current["text"])
        status.setText(tr("Copied."))

    def clear() -> None:
        clear_logs()
        current["text"] = full_report()
        body.setText(current["text"])
        status.setText(tr("Cleared."))

    def close() -> None:
        view.hide()
        if on_close is not None:
            on_close()

    send_button.clicked.connect(lambda *_: send())
    copy_button.clicked.connect(lambda *_: copy())
    close_button.clicked.connect(lambda *_: close())
    buttons = QHBoxLayout()
    buttons.addWidget(send_button)
    buttons.addWidget(copy_button)
    buttons.addWidget(status, 1)
    if clear_button is not None:
        clear_button.clicked.connect(lambda *_: clear())
        buttons.addWidget(clear_button)
    buttons.addWidget(close_button)
    layout = QVBoxLayout(view)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(6)
    layout.addWidget(heading)
    layout.addWidget(hint)
    layout.addWidget(scroll, 1)
    layout.addLayout(buttons)
    view.send_button, view.copy_button, view.clear_button = send_button, copy_button, clear_button
    view.status = status
    return view


def show_over(window, text: str, title: str, can_clear: bool = False):
    """Affiche le rapport par-dessus la fenêtre principale."""
    view = report_view(text, title, parent=window, can_clear=can_clear)
    margin = 10
    view.setGeometry(margin, margin, max(200, window.width() - 2 * margin),
                     max(150, window.height() - 2 * margin))
    view.show()
    view.raise_()
    return view
