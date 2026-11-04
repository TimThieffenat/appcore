"""Démarrage d'une app (ordinateur et Android) : tout ce que faisait main.py.

Le main.py de chaque app se réduit à :

    import sys
    from appcore import boot          # en premier : installe le rapport d'erreur

    def pages():
        from appcore.i18n import N_
        from page_home import HomePage
        from page_settings import SettingsPage
        return [(N_("Home"), "play", HomePage), (N_("Settings"), "settings", SettingsPage)]

    if __name__ == "__main__":
        sys.exit(boot.run(pages))

Sur Android, le fichier doit s'appeler main.py (exigence de l'outil de
compilation) et l'application s'affiche en plein écran.

Le rapport d'erreur (crash_report) est installé à l'import de ce module, avant
tout le reste : si l'app ne peut pas démarrer, elle affiche pourquoi au lieu
de se fermer.

run(pages, qss=..., setup=..., started=..., on_language=..., window_class=...) :
- pages() : la liste (libellé N_(), icône, classe) des pages du rail ; appelée
  à chaque construction de la fenêtre (changement de langue compris) ;
- qss : feuille de style de l'app, ajoutée à celle du socle (voir style.py) ;
- setup(app) : juste après la langue et la police, avant le thème et la
  fenêtre (reprendre des données, préparer un profil…) ;
- started(window) : une fois la première fenêtre affichée (achats, rappels…) ;
  une erreur y est notée dans le journal sans empêcher l'app de démarrer ;
- on_language(code) : la langue vient de changer, juste avant que la fenêtre
  soit refaite (textes gardés hors de l'interface : notifications…) ;
- window_class : une sous-classe de appcore.main_window.MainWindow, si l'app
  ajoute des choses à la fenêtre (ouvrir une fiche depuis une autre page…).
"""

import logging
import sys
from pathlib import Path

from appcore import crash_report

crash_report.install()
log = logging.getLogger("main")

from PySide6.QtCore import QSettings, QTimer  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from appcore import app as app_config  # noqa: E402


def _show_startup_error(app: QApplication, text: str) -> int:
    """L'app n'a pas pu démarrer : on montre l'erreur au lieu de se fermer."""
    crash_report.record_fatal(text)
    from appcore.i18n import tr
    view = crash_report.report_view(
        crash_report.full_report(), tr("{app} could not start", app=app_config.name()),
        on_close=app.quit)
    view.setWindowTitle(app_config.name())
    view.resize(900, 420)
    if crash_report.on_android():
        view.showFullScreen()
    else:
        view.show()
    return app.exec()


class Windows:
    """La fenêtre principale. Changer de langue la refait entièrement (tous les
    textes sont écrits à la construction des pages) : chaque page relit ses
    réglages et ses fichiers, rien n'est perdu."""

    def __init__(self, app: QApplication, pages, window_class=None, on_language=None) -> None:
        self.app = app
        self.pages = pages
        self.window_class = window_class
        self.on_language = on_language
        self.window = None

    def open(self, page: int = 0) -> None:
        from appcore.app_signals import bus
        from appcore.main_window import MainWindow
        from appcore.ui_common import is_android

        old = self.window
        if old is not None:
            old.pause_app()     # son, micro, minuteries de l'ancienne fenêtre
            try:
                self.app.applicationStateChanged.disconnect(old.on_app_state_changed)
            except (RuntimeError, TypeError):
                pass
            # signaux du bus (sauf la langue) : seules les pages y sont branchées
            for name in bus_page_signals():
                try:
                    getattr(bus, name).disconnect()
                except (RuntimeError, TypeError):
                    pass
        crash_report.step("building the pages")
        window = (self.window_class or MainWindow)(self.pages())
        window.show_page(page)
        # arrière-plan / retour (Android) : couper son, micro et animations
        self.app.applicationStateChanged.connect(window.on_app_state_changed)
        crash_report.step("showing the window")
        self.window = window
        if is_android():
            # Plein écran « immersif » : cache la barre d'état et la barre de navigation
            window.showFullScreen()
        else:
            if old is not None:
                window.setGeometry(old.geometry())
            window.show()
        if old is not None:
            old.hide()
            old.deleteLater()

    def change_language(self) -> None:
        """Nouvelle langue : la fenêtre est refaite, sur la page Settings."""
        from appcore.main_window import settings_index

        log.info("language changed: the window is rebuilt")
        if self.on_language is not None:
            try:
                from appcore import i18n
                self.on_language(i18n.language())
            except Exception:  # noqa: BLE001 — la fenêtre doit être refaite quand même
                log.warning("on_language failed", exc_info=True)
        index = settings_index(self.window.pages) if self.window is not None else 0
        QTimer.singleShot(0, lambda: self.open(index))


def bus_page_signals() -> list[str]:
    """Les signaux du bus auxquels les pages se branchent (tous sauf la langue)."""
    from PySide6.QtCore import Signal

    from appcore.app_signals import _Bus
    return [name for name, value in vars(_Bus).items()
            if isinstance(value, Signal) and name != "language_changed"]


def adopt_old_data(app: QApplication) -> None:
    """L'app a changé de nom (OLD_NAMES de app_info.py) : au premier lancement
    sous le nouveau nom, on reprend les réglages et les données enregistrés sous
    l'ancien (sur ordinateur ; sur Android l'app renommée est une autre app, sans
    accès à l'ancienne). Rien n'est effacé : l'ancien dossier reste en place."""
    import shutil

    from PySide6.QtCore import QStandardPaths

    old_names = tuple(app_config.get("OLD_NAMES") or ())
    if not old_names:
        return
    location = QStandardPaths.StandardLocation.AppDataLocation
    settings = QSettings()
    new_dir = Path(QStandardPaths.writableLocation(location) or ".")
    new_empty = not new_dir.exists() or not any(new_dir.iterdir())
    name = app_config.name()
    for old in old_names:
        app.setOrganizationName(old)
        app.setApplicationName(old)
        old_settings = QSettings()
        old_dir = Path(QStandardPaths.writableLocation(location) or ".")
        app.setOrganizationName(name)
        app.setApplicationName(name)
        keys = old_settings.allKeys()
        if keys and not settings.allKeys():
            for key in keys:
                settings.setValue(key, old_settings.value(key))
            settings.sync()
        if new_empty and old_dir != new_dir and old_dir.is_dir() and any(old_dir.iterdir()):
            shutil.copytree(old_dir, new_dir, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("sound_cache"))
            new_empty = False


def app_root() -> Path:
    """Le dossier de l'app (celui de main.py et de app_info.py)."""
    main = sys.modules.get("__main__")
    path = getattr(main, "__file__", None)
    return Path(path).absolute().parent if path else Path(__file__).absolute().parent.parent


def run(pages, qss: str = "", setup=None, started=None, on_language=None,
        window_class=None) -> int:
    """Lance l'app ; renvoie le code de sortie (pour sys.exit)."""
    app = QApplication(sys.argv)
    name = app_config.name()
    app.setOrganizationName(name)
    app.setApplicationName(name)
    app.setApplicationVersion(app_config.version())
    try:
        adopt_old_data(app)
    except Exception:  # noqa: BLE001 — une reprise ratée ne doit pas empêcher de démarrer
        log.warning("old settings and data not taken over", exc_info=True)
    crash_report.install_qt_messages(app)
    app.aboutToQuit.connect(crash_report.startup_done)  # fermée tout de suite : pas un plantage
    # Langue : celle choisie dans Settings, sinon celle du téléphone
    from appcore import i18n
    choice = QSettings().value("language", i18n.SYSTEM)
    i18n.set_language(i18n.resolve(choice))
    log.info("language: %s (setting: %s, phone: %s)", i18n.language(), choice,
             i18n.system_language())
    crash_report.step("loading the symbols font")
    try:
        # symboles (♭ ♯ → ↶ ♬ ✕…) intégrés : jamais de carrés vides, quel que soit le téléphone
        from appcore import symbol_font
        if not symbol_font.install(app):
            log.warning("symbols font not loaded")
    except Exception:  # noqa: BLE001 — sans elle, l'app marche avec les polices du système
        log.warning("symbols font not loaded", exc_info=True)

    icon = app_root() / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    windows = Windows(app, pages, window_class, on_language)
    try:
        crash_report.step("loading the app")
        from appcore import sound, style
        from appcore.app_signals import bus

        if qss:
            style.add_qss(qss)
        if setup is not None:
            crash_report.step("setting up the app")
            setup(app)
        crash_report.step("applying the theme")
        # par défaut, le thème du téléphone (clair ou sombre), suivi en direct
        style.apply_theme(app, QSettings().value("theme", style.SYSTEM))
        style.follow_system(app, bus.settings_changed.emit)
        bus.language_changed.connect(windows.change_language)
        windows.open()
        if started is not None:
            crash_report.step("starting the app's services")
            try:
                started(windows.window)
            except Exception:  # noqa: BLE001 — jamais une raison de ne pas démarrer
                log.warning("started() failed", exc_info=True)
        crash_report.log_context()
    except Exception:  # noqa: BLE001 — tout plutôt qu'une app qui se ferme sans rien dire
        import traceback
        return _show_startup_error(app, traceback.format_exc())

    crash_report.step("first seconds")
    QTimer.singleShot(crash_report.STARTUP_GRACE_MS, crash_report.startup_done)
    # Prépare les notes de l'instrument en arrière-plan, une fois la fenêtre affichée
    QTimer.singleShot(400, sound.start_warm_up)
    previous = crash_report.previous_crash()
    if previous:  # le lancement précédent a planté : on le dit, avec le rapport
        QTimer.singleShot(800, lambda: crash_report.show_over(
            windows.window, crash_report.full_report(),
            i18n.tr("{app} stopped last time", app=name)))
    return app.exec()
