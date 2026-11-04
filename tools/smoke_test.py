"""Essai complet de l'interface d'une app, sans rien toucher : outil de développement.

Depuis le dossier de l'app :

    python appcore/tools/smoke_test.py

Ouvre la fenêtre de l'app hors écran (format téléphone 850 × 390), en français,
affiche chaque page du rail, le rapport d'erreur, puis la première page au
format ordinateur, en sombre et en clair ; puis, dans chacune des autres
langues de l'app, la première page et les réglages. Une capture de chaque écran
est enregistrée dans build/smoke/. Le son est coupé (lecture « visuelle »). Les réglages
utilisés sont à part (« <App>-smoke ») : les vrais ne sont pas touchés.

La fenêtre est celle de l'app : `MainWindow` de son main.py s'il y en a une
(sous-classe de celle du socle), sinon celle du socle.

Si l'app a un fichier tools/smoke_extra.py, ses fonctions (toutes facultatives) :
- prepare() : avant tout (données de test à part, par exemple un profil temporaire) ;
- before_theme(theme) : avant de construire la fenêtre de chaque thème ;
- tour(window, shot, pump, theme, log) : à chaque thème, après les pages
  (parcours propre à l'app : une manche de jeu, un morceau…) ;
- tour_language(window, shot, pump, code, log) : dans chaque autre langue.

Toute erreur est écrite dans build/smoke/smoke.log (et le script s'arrête en erreur).
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
if sys.platform == "win32":   # hors écran, Qt ne trouve pas seul les polices de Windows
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
        raise SystemExit("à lancer depuis le dossier de l'app (celui de main.py et app_info.py)")
    OUT.mkdir(parents=True, exist_ok=True)
    # Journal et rapport d'erreur de l'essai dans build/smoke/logs : ceux de la
    # vraie app ne sont pas touchés (main.py installe le rapport en s'important)
    from appcore import crash_report
    crash_report._dir = OUT / "logs"
    crash_report._dir.mkdir(parents=True, exist_ok=True)
    import main as app_main   # les pages, la feuille de style et la préparation de l'app
    from PySide6.QtCore import QCoreApplication, QSettings, QStandardPaths
    from PySide6.QtWidgets import QApplication

    from appcore import app as config
    from appcore import i18n, sound, symbol_font
    from appcore.main_window import MainWindow, settings_index
    from appcore.style import add_qss, apply_theme

    window_class = getattr(app_main, "MainWindow", None) or MainWindow

    app = QApplication(sys.argv)
    app.setOrganizationName(config.name() + "-smoke")    # réglages à part
    app.setApplicationName(config.name() + "-smoke")
    QStandardPaths.setTestModeEnabled(True)               # dossiers de test
    QSettings().clear()
    i18n.set_language("fr")
    log(f"{config.name()} {config.version()} · langues {', '.join(i18n.LANGUAGES)}")
    log(f"police de symboles : {symbol_font.install(app)} ({', '.join(symbol_font.families())})")
    sound.playback().player.audio_ok = False             # silence : lecture visuelle
    add_qss(getattr(app_main, "QSS", ""))
    extra = _extra()
    if extra is not None and hasattr(extra, "prepare"):
        extra.prepare()            # avant setup : données de test (profil temporaire…)
    if callable(getattr(app_main, "setup", None)):
        app_main.setup(app)

    def pump(times: int = 3) -> None:
        for _ in range(times):
            QCoreApplication.processEvents()

    def shot(window, name: str) -> None:
        pump()
        window.grab().save(str(OUT / f"{name}.png"))
        log(f"  capture {name}.png")

    def hook(name: str, *args) -> None:
        if extra is not None and hasattr(extra, name):
            getattr(extra, name)(*args)

    for theme in ("dark", "light"):
        log(f"=== thème {theme}")
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
            log("  parcours de l'app (tools/smoke_extra.py)")
            window.show_page(0)
            hook("tour", window, shot, pump, theme, log)
        # rapport d'erreur (Réglages › Rapport d'erreur) et adresse de l'e-mail
        report = crash_report.full_report()
        view = crash_report.show_over(window, report, i18n.tr("Error report"), can_clear=True)
        shot(window, f"{theme}_90_rapport")
        view.hide()
        view.deleteLater()
        url = crash_report.email_url(crash_report.full_report(compact=True), "test")
        log(f"  rapport : {len(report)} caractères, adresse de l'e-mail : {len(url)} caractères")
        window.show_page(0)
        window.resize(1280, 720)
        pump(5)
        shot(window, f"{theme}_95_ordinateur")
        window.close()
        window.deleteLater()
        pump(5)
    # --- Les autres langues : la première page et les réglages
    apply_theme(app, "dark")
    for code in [c for c in i18n.LANGUAGES if c not in ("en", "fr")]:
        log(f"=== langue {code}")
        i18n.set_language(code)
        hook("before_theme", "dark")
        window = window_class(app_main.pages())
        window.resize(850, 390)
        window.show()
        pump(10)
        shot(window, f"lang_{code}_1_{window.pages[0][0].lower().replace(' ', '_')}")
        window.show_page(settings_index(window.pages))
        shot(window, f"lang_{code}_2_reglages")
        window.show_page(0)
        hook("tour_language", window, shot, pump, code, log)
        window.close()
        window.deleteLater()
        pump(5)
    i18n.set_language("fr")
    crash_report.startup_done()
    log("OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        OUT.mkdir(parents=True, exist_ok=True)
        log("ERREUR\n" + traceback.format_exc())
        sys.exit(1)
