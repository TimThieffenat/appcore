"""Start-up of an app (desktop and Android): everything main.py used to do.

Each app's main.py comes down to:

    import sys
    from appcore import boot          # first: installs the error report

    def pages():
        from appcore.i18n import N_
        from page_home import HomePage
        from page_settings import SettingsPage
        return [(N_("Home"), "play", HomePage), (N_("Settings"), "settings", SettingsPage)]

    if __name__ == "__main__":
        sys.exit(boot.run(pages))

On Android the file must be called main.py (required by the build tool)
and the application is shown full screen.

The error report (crash_report) is installed when this module is imported,
before anything else: if the app cannot start, it shows why instead of
closing.

run(pages, qss=..., setup=..., started=..., on_language=..., window_class=...):
- pages(): the list (N_() label, icon, class) of the rail's pages; called
  every time the window is built (language change included);
- qss: the app's style sheet, added to the base's one (see style.py);
- setup(app): right after the language and font, before the theme and the
  window (take over data, prepare a profile…);
- started(window): once the first window is shown (purchases, reminders…);
  an error there is logged without stopping the app from starting;
- on_language(code): the language just changed, right before the window
  is rebuilt (texts kept outside the interface: notifications…);
- window_class: a subclass of appcore.main_window.MainWindow, if the app
  adds things to the window (open a sheet from another page…).
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
    """The app could not start: show the error instead of closing."""
    crash_report.record_fatal(text)
    from appcore.i18n import tr
    view = crash_report.report_view(
        crash_report.full_report(), tr("{app} could not start", app=app_config.name()),
        on_close=app.quit)
    view.setWindowTitle(app_config.name())
    view.resize(*(app_config.phone_size() if app_config.portrait() else (900, 420)))
    if crash_report.on_android():
        view.showFullScreen()
    else:
        view.show()
    return app.exec()


class Windows:
    """The main window. Changing language rebuilds it entirely (all texts are
    written when the pages are built): each page reads its settings and files
    again, nothing is lost."""

    def __init__(self, app: QApplication, pages, window_class=None, on_language=None) -> None:
        self.app = app
        self.pages = pages
        self.window_class = window_class
        self.on_language = on_language
        self.window = None

    def open(self, page: int | None = None) -> None:
        """Opens (or rebuilds) the window, on `page` (by default the home page)."""
        from appcore.app_signals import bus
        from appcore.main_window import MainWindow
        from appcore.ui_common import is_android

        old = self.window
        if old is not None:
            old.pause_app()     # sound, microphone, timers of the old window
            try:
                self.app.applicationStateChanged.disconnect(old.on_app_state_changed)
            except (RuntimeError, TypeError):
                pass
            # bus signals (except the language): only pages are connected to them
            for name in bus_page_signals():
                try:
                    getattr(bus, name).disconnect()
                except (RuntimeError, TypeError):
                    pass
        crash_report.step("building the pages")
        window = (self.window_class or MainWindow)(self.pages())
        window.show_page(window.home if page is None else page)
        # background / back (Android): stop sound, microphone and animations
        self.app.applicationStateChanged.connect(window.on_app_state_changed)
        crash_report.step("showing the window")
        self.window = window
        if is_android():
            # "Immersive" full screen: hides the status bar and the navigation bar
            window.showFullScreen()
        else:
            if old is not None:
                window.setGeometry(old.geometry())
            window.show()
        if old is not None:
            old.hide()
            old.deleteLater()

    def change_language(self) -> None:
        """New language: the window is rebuilt, on the Settings page."""
        from appcore.main_window import settings_index

        log.info("language changed: the window is rebuilt")
        if self.on_language is not None:
            try:
                from appcore import i18n
                self.on_language(i18n.language())
            except Exception:  # noqa: BLE001 — the window must be rebuilt anyway
                log.warning("on_language failed", exc_info=True)
        index = settings_index(self.window.pages) if self.window is not None else 0
        QTimer.singleShot(0, lambda: self.open(index))


def bus_page_signals() -> list[str]:
    """The bus signals pages connect to (all but the language)."""
    from PySide6.QtCore import Signal

    from appcore.app_signals import _Bus
    return [name for name, value in vars(_Bus).items()
            if isinstance(value, Signal) and name != "language_changed"]


def adopt_old_data(app: QApplication) -> None:
    """The app was renamed (OLD_NAMES of app_info.py): at the first start under
    the new name, the settings and data saved under the old one are taken over
    (on desktop; on Android the renamed app is another app, with no access to
    the old one). Nothing is deleted: the old folder stays in place."""
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
    """The app's folder (the one holding main.py and app_info.py)."""
    main = sys.modules.get("__main__")
    path = getattr(main, "__file__", None)
    return Path(path).absolute().parent if path else Path(__file__).absolute().parent.parent


def run(pages, qss: str = "", setup=None, started=None, on_language=None,
        window_class=None) -> int:
    """Runs the app; returns the exit code (for sys.exit)."""
    app = QApplication(sys.argv)
    name = app_config.name()
    app.setOrganizationName(name)
    app.setApplicationName(name)
    app.setApplicationVersion(app_config.version())
    try:
        adopt_old_data(app)
    except Exception:  # noqa: BLE001 — a failed take-over must not prevent start-up
        log.warning("old settings and data not taken over", exc_info=True)
    crash_report.install_qt_messages(app)
    app.aboutToQuit.connect(crash_report.startup_done)  # closed right away: not a crash
    # Language: the one chosen in Settings, else the phone's
    from appcore import i18n
    choice = QSettings().value("language", i18n.SYSTEM)
    i18n.set_language(i18n.resolve(choice))
    log.info("language: %s (setting: %s, phone: %s)", i18n.language(), choice,
             i18n.system_language())
    crash_report.step("loading the symbols font")
    try:
        # built-in symbols (♭ ♯ → ↶ ♬ ✕…): never empty boxes, whatever the phone
        from appcore import symbol_font
        if not symbol_font.install(app):
            log.warning("symbols font not loaded")
    except Exception:  # noqa: BLE001 — without it, the app works with the system fonts
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
        # by default, the phone's theme (light or dark), followed live
        style.apply_theme(app, QSettings().value("theme", style.SYSTEM))
        style.follow_system(app, bus.settings_changed.emit)
        bus.language_changed.connect(windows.change_language)
        windows.open()
        if started is not None:
            crash_report.step("starting the app's services")
            try:
                started(windows.window)
            except Exception:  # noqa: BLE001 — never a reason not to start
                log.warning("started() failed", exc_info=True)
        crash_report.log_context()
    except Exception:  # noqa: BLE001 — anything rather than an app closing silently
        import traceback
        return _show_startup_error(app, traceback.format_exc())

    crash_report.step("first seconds")
    QTimer.singleShot(crash_report.STARTUP_GRACE_MS, crash_report.startup_done)
    # Prepare the instrument's notes in the background, once the window is shown
    QTimer.singleShot(400, sound.start_warm_up)
    previous = crash_report.previous_crash()
    if previous:  # the previous start crashed: say so, with the report
        QTimer.singleShot(800, lambda: crash_report.show_over(
            windows.window, crash_report.full_report(),
            i18n.tr("{app} stopped last time", app=name)))
    return app.exec()
