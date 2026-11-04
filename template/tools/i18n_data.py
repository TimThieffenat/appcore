"""Textes des tableaux de données de l'app, pour appcore/tools/i18n_check.py.

Les noms d'une bibliothèque (styles, niveaux, trophées…) se déclarent ici,
directement depuis leurs modules, sans avoir à les marquer un par un :

    def texts(add):
        import levels
        add("levels", *(name for name, _ in levels.LEVELS))
"""


def texts(add) -> None:
    pass
