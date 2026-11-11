"""Entry point of __APP_NAME__ (desktop and Android).

Start-up, the window with an icon rail, the error report, language,
theme… are the base's (appcore/boot.py). The app gives it its pages and its
style sheet. On Android, this file must be called main.py.
"""

import sys

from appcore import boot  # first: installs the error report before anything else

# The app's own style sheet (added to the base's, appcore/style.py):
# same {name} colours as the theme, doubled braces.
QSS = """
QLabel#hero {{ font-size: 30px; font-weight: 700; color: {accent_text}; }}
"""


def pages():
    """The rail's pages: (label, icon, page). To add a page: create
    its class in a page_xxx.py file, then add it here. Icons are
    the base's (appcore/icons.py) or from icons.py."""
    import icons  # noqa: F401 — the app's icons (registered in the base)
    from appcore.i18n import N_
    from page_home import HomePage
    from page_settings import SettingsPage

    return [
        (N_("Home"), "home", HomePage),
        (N_("Settings"), "settings", SettingsPage),
    ]


def setup(app) -> None:
    """Right before the theme and the window: read a profile, prepare data…"""


def _qt_modules_for_android():
    """Never called: Qt's Android tool looks in the project's imports for
    which Qt modules to bundle; this one lists those the base needs."""
    from PySide6 import QtCore, QtGui, QtMultimedia, QtWidgets  # noqa: F401


if __name__ == "__main__":
    sys.exit(boot.run(pages, qss=QSS, setup=setup))
