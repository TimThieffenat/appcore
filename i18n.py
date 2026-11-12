"""Languages of the app: English (the text written in the code), French, Spanish,
Italian, Portuguese (Brazil) and German. Each app picks its own
(LANGUAGES in its app_info.py).

    tr("Play")                      -> "Lecture" in French
    tr("Bar {n}", n=3)              -> "Mesure 3": the {…} fields are filled in
    ntr("{n} bar", "{n} bars", n)   -> singular or plural depending on n and the language
    N_("Minor pentatonic")          -> the text as is: marks a data text
                                       (list, library) translated later, when
                                       it is shown, with tr()

Two catalogues per language, merged at start-up:
- appcore/locales/<code>.py: the base's texts (settings, error report,
  note names, chord names…), shared by all apps;
- the app's locales/<code>.py: its own texts. An app entry
  replaces the base's one (for a different translation in that app).

Each catalogue is a dictionary T, English text -> translation (for a
plural: a pair (singular, plural), stored under the English singular
text). A missing text is shown in English: nothing breaks if one is missing.

Rule: settings and files always keep the English text (the "key"); only
the display is translated. Changing language therefore loses nothing.
`python appcore/tools/i18n_check.py` (from the app's folder) lists the
texts to translate and what is missing, for the base and for the app.
"""

from __future__ import annotations

import importlib

from appcore import app

SYSTEM = "system"   # default setting: the phone's language
# All languages the base knows (each written in its own language)
ALL_LANGUAGES = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "pt": "Português (Brasil)",
    "de": "Deutsch",
}
# Those the app offers (LANGUAGES of app_info.py)
LANGUAGES = {code: ALL_LANGUAGES[code] for code in app.languages() if code in ALL_LANGUAGES}
# Languages where notes are named Do Ré Mi: that is their default setting
SOLFEGE_LANGUAGES = {"fr", "es", "it", "pt"}
# Languages where 0 takes the singular ("0 mesure"); elsewhere only 1 is singular
_ZERO_SINGULAR = {"fr", "pt"}

_language = "en"
_catalog: dict = {}


def system_language() -> str:
    """The phone's (or computer's) language, if the app speaks it; else English."""
    try:
        from PySide6.QtCore import QLocale
        names = list(QLocale.system().uiLanguages()) or [QLocale.system().name()]
    except Exception:  # noqa: BLE001 — without Qt (tools, tests): English
        return "en"
    for name in names:
        code = str(name).replace("_", "-").split("-")[0].lower()
        if code in LANGUAGES:
            return code
    return "en"


def resolve(choice) -> str:
    """"language" setting (SYSTEM or a code) -> language code."""
    choice = str(choice or SYSTEM)
    return choice if choice in LANGUAGES else system_language()


def _load(module: str) -> dict:
    try:
        catalog = importlib.import_module(module).T
    except (ImportError, AttributeError):
        return {}
    return catalog if isinstance(catalog, dict) else {}


def catalog_for(code: str) -> dict:
    """A language's catalogue: the base's one, completed (and corrected) by the app's."""
    if code == "en":
        return {}
    merged = dict(_load(f"appcore.locales.{code}"))
    merged.update(_load(f"locales.{code}"))
    return merged


def set_language(code: str) -> None:
    global _language, _catalog
    code = code if code in LANGUAGES else "en"
    catalog = catalog_for(code)
    if code != "en" and not catalog:
        code = "en"
    _language, _catalog = code, catalog


def language() -> str:
    return _language


def tr(text: str, /, **fields) -> str:
    """Translated text (with its {name} fields filled in)."""
    out = _catalog.get(text, text)
    if isinstance(out, tuple):      # plural entry used in the singular
        out = out[0]
    if fields:
        try:
            return out.format(**fields)
        except (KeyError, IndexError, ValueError):
            return text.format(**fields)   # broken translation: English
    return out


def ntr(one: str, other: str, n: int, /, **fields) -> str:
    """Singular / plural: ntr("{n} bar", "{n} bars", count). {n} is filled in."""
    singular = n == 1 or (n == 0 and _language in _ZERO_SINGULAR)
    entry = _catalog.get(one)
    if isinstance(entry, tuple) and len(entry) == 2:
        out = entry[0] if singular else entry[1]
    else:
        out = one if n == 1 else other
    fields.setdefault("n", n)
    try:
        return out.format(**fields)
    except (KeyError, IndexError, ValueError):
        return (one if n == 1 else other).format(**fields)


# Languages writing decimals with a comma (1,5)
_DECIMAL_COMMA = {"fr", "es", "it", "pt", "de"}


def decimal(value: float, digits: int = 1) -> str:
    """Decimal number written as in the app's language (1.5 / 1,5)."""
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if _language in _DECIMAL_COMMA else text


def N_(text: str, /) -> str:
    """Marks a text translated when shown (see tr)."""
    return text
