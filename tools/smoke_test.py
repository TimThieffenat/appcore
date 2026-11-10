"""Full check of an app's interface, touching nothing: development tool.

From the app's folder:

    python appcore/tools/smoke_test.py

Opens the app's window off screen (phone format 850 × 390), in English,
shows each page of the rail, the error report, then the first page in
desktop format, in dark and in light; then, in each of the app's other
languages, the first page and the settings. A screenshot of each screen
is saved in build/smoke/. Sound is off ("visual" playback). The settings
used are separate ("<App>-smoke"): the real ones are not touched.

The window is the app's: the `MainWindow` of its main.py if there is one
(subclass of the base's), else the base's.

If the app has a tools/smoke_extra.py file, its functions (all optional):
- prepare(): before anything (separate test data, for example a temporary profile);
- before_theme(theme): before building the window of each theme;
- tour(window, shot, pump, theme, log): for each theme, after the pages
  (the app's own tour: a game round, a song…);
- tour_language(window, shot, pump, code, log): in each other language.

Any error is written to build/smoke/smoke.log (and the script exits with an error).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if sys.platform == "win32":   # off screen, Qt does not find Windows' fonts by itself
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                                                         "Fonts"))
OUT = ROOT / "build" / "smoke"
LOG = OUT / "smoke.log"
_lines: list[str] = []


def log(text: str) -> None:
    print(text, flush=True)
    _lines.append(text)
    LOG.write_text("\n".join(_lines) + "\n", encoding="utf-8")


def _extra():
    path = ROOT / "tools" / "smoke_extra.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("smoke_extra", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if not (ROOT / "app_info.py").is_file() or not (ROOT / "main.py").is_file():
        raise SystemExit("run from the app's folder (the one holding main.py and app_info.py)")
    OUT.mkdir(parents=True, exist_ok=True)
    # The check's log and error report go to build/smoke/logs: those of the
    # real app are not touched (main.py installs the report when imported)
    from appcore import crash_report
    crash_report._dir = OUT / "logs"
    crash_report._dir.mkdir(parents=True, exist_ok=True)
    import main as app_main   # the pages, the style sheet and the app's set-up
    from PySide6.QtCore import QCoreApplication, QSettings, QStandardPaths
    from PySide6.QtWidgets import QApplication

    from appcore import app as config
    from appcore import i18n, sound, symbol_font
    from appcore.main_window import MainWindow, settings_index
    from appcore.style import add_qss, apply_theme

    window_class = getattr(app_main, "MainWindow", None) or MainWindow

    app = QApplication(sys.argv)
    app.setOrganizationName(config.name() + "-smoke")    # separate settings
    app.setApplicationName(config.name() + "-smoke")
    QStandardPaths.setTestModeEnabled(True)               # test folders
    QSettings().clear()
    i18n.set_language("en")
    log(f"{config.name()} {config.version()} · languages {', '.join(i18n.LANGUAGES)}")
    log(f"symbols font: {symbol_font.install(app)} ({', '.join(symbol_font.families())})")
    sound.playback().player.audio_ok = False             # silence: visual playback
    add_qss(getattr(app_main, "QSS", ""))
    extra = _extra()
    if extra is not None and hasattr(extra, "prepare"):
        extra.prepare()            # before setup: test data (temporary profile…)
    if callable(getattr(app_main, "setup", None)):
        app_main.setup(app)

    def pump(times: int = 3) -> None:
        for _ in range(times):
            QCoreApplication.processEvents()

    def shot(window, name: str) -> None:
        pump()
        window.grab().save(str(OUT / f"{name}.png"))
        log(f"  screenshot {name}.png")

    def hook(name: str, *args) -> None:
        if extra is not None and hasattr(extra, name):
            getattr(extra, name)(*args)

    for theme in ("dark", "light"):
        log(f"=== theme {theme}")
        hook("before_theme", theme)
        apply_theme(app, theme)
        window = window_class(app_main.pages())
        window.resize(850, 390)
        window.show()
        pump(10)
        for index, (label, _, _) in enumerate(window.pages):
            window.show_page(index)
            pump(5)
            shot(window, f"{theme}_{index:02d}_{label.lower().replace(' ', '_')}")
        if extra is not None and hasattr(extra, "tour"):
            log("  the app's tour (tools/smoke_extra.py)")
            window.show_page(0)
            hook("tour", window, shot, pump, theme, log)
        # error report (Settings › Error report) and email address
        report = crash_report.full_report()
        view = crash_report.show_over(window, report, i18n.tr("Error report"), can_clear=True)
        shot(window, f"{theme}_90_report")
        view.hide()
        view.deleteLater()
        url = crash_report.email_url(crash_report.full_report(compact=True), "test")
        log(f"  report: {len(report)} characters, email address: {len(url)} characters")
        window.show_page(0)
        window.resize(1280, 720)
        pump(5)
        shot(window, f"{theme}_95_desktop")
        window.close()
        window.deleteLater()
        pump(5)
    # --- The other languages: the first page and the settings
    apply_theme(app, "dark")
    for code in [c for c in i18n.LANGUAGES if c != "en"]:
        log(f"=== language {code}")
        i18n.set_language(code)
        hook("before_theme", "dark")
        window = window_class(app_main.pages())
        window.resize(850, 390)
        window.show()
        pump(10)
        shot(window, f"lang_{code}_1_{window.pages[0][0].lower().replace(' ', '_')}")
        window.show_page(settings_index(window.pages))
        shot(window, f"lang_{code}_2_settings")
        window.show_page(0)
        hook("tour_language", window, shot, pump, code, log)
        window.close()
        window.deleteLater()
        pump(5)
    i18n.set_language("en")
    crash_report.startup_done()
    log("OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        OUT.mkdir(parents=True, exist_ok=True)
        log("ERROR\n" + traceback.format_exc())
        sys.exit(1)
