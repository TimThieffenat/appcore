"""Point d'entrée de __APP_NAME__ (ordinateur et Android).

Le démarrage, la fenêtre à rail d'icônes, le rapport d'erreur, la langue, le
thème… sont ceux du socle (appcore/boot.py). L'app lui donne ses pages et sa
feuille de style. Sur Android, ce fichier doit s'appeler main.py.
"""

import sys

from appcore import boot  # en premier : installe le rapport d'erreur avant tout le reste

# Feuille de style propre à l'app (ajoutée à celle du socle, appcore/style.py) :
# mêmes couleurs {nom} que le thème, accolades doublées.
QSS = """
QLabel#hero {{ font-size: 30px; font-weight: 700; color: {accent_text}; }}
"""


def pages():
    """Les pages du rail : (libellé, icône, page). Pour ajouter une page : créer
    sa classe dans un fichier page_xxx.py, puis l'ajouter ici. Les icônes sont
    celles du socle (appcore/icons.py) ou de icons.py."""
    import icons  # noqa: F401 — les icônes de l'app (enregistrées dans le socle)
    from appcore.i18n import N_
    from page_home import HomePage
    from page_settings import SettingsPage

    return [
        (N_("Home"), "home", HomePage),
        (N_("Settings"), "settings", SettingsPage),
    ]


def setup(app) -> None:
    """Juste avant le thème et la fenêtre : lire un profil, préparer des données…"""


def _qt_modules_for_android():
    """Jamais appelée : l'outil Android de Qt cherche dans les imports du projet
    quels modules Qt embarquer ; celui-ci liste ceux dont le socle a besoin."""
    from PySide6 import QtCore, QtGui, QtMultimedia, QtWidgets  # noqa: F401


if __name__ == "__main__":
    sys.exit(boot.run(pages, qss=QSS, setup=setup))
