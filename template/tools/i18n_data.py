"""Texts of the app's data tables, for appcore/tools/i18n_check.py.

The names of a library (styles, levels, trophies…) are declared here,
straight from their modules, without having to mark them one by one:

    def texts(add):
        import levels
        add("levels", *(name for name, _ in levels.LEVELS))
"""


def texts(add) -> None:
    pass
