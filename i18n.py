"""Langues de l'app : anglais (le texte écrit dans le code), français, espagnol,
italien, portugais (Brésil) et allemand. Chaque app choisit les siennes
(LANGUAGES dans son app_info.py).

    tr("Play")                      -> « Lecture » en français
    tr("Bar {n}", n=3)              -> « Mesure 3 » : les champs {…} sont remplis
    ntr("{n} bar", "{n} bars", n)   -> singulier ou pluriel selon n et la langue
    N_("Minor pentatonic")          -> le texte tel quel : marque un texte de
                                       données (liste, bibliothèque) traduit plus
                                       tard, au moment de l'afficher, avec tr()

Deux catalogues par langue, fusionnés au démarrage :
- appcore/locales/<code>.py : les textes du socle (réglages, rapport d'erreur,
  noms des notes, des accords…), partagés par toutes les apps ;
- locales/<code>.py de l'app : ses propres textes. Une entrée de l'app
  remplace celle du socle (pour une traduction différente dans cette app).

Chaque catalogue est un dictionnaire T, texte anglais -> traduction (pour un
pluriel : un couple (singulier, pluriel), rangé sous le texte anglais au
singulier). Un texte absent s'affiche en anglais : rien ne casse s'il en manque un.

Règle : les réglages et les fichiers gardent toujours le texte anglais (la
« clé ») ; seul l'affichage est traduit. Changer de langue ne perd donc rien.
`python appcore/tools/i18n_check.py` (depuis le dossier de l'app) liste les
textes à traduire et ce qui manque, pour le socle et pour l'app.
"""

from __future__ import annotations

import importlib

from appcore import app

SYSTEM = "system"   # réglage par défaut : la langue du téléphone
# Toutes les langues que le socle connaît (chaque langue écrite dans sa langue)
ALL_LANGUAGES = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "pt": "Português (Brasil)",
    "de": "Deutsch",
}
# Celles que l'app propose (LANGUAGES de app_info.py)
LANGUAGES = {code: ALL_LANGUAGES[code] for code in app.languages() if code in ALL_LANGUAGES}
# Langues où l'on nomme les notes Do Ré Mi : c'est leur réglage par défaut
SOLFEGE_LANGUAGES = {"fr", "es", "it", "pt"}
# Langues où 0 se dit au singulier (« 0 mesure ») ; ailleurs, seul 1 est au singulier
_ZERO_SINGULAR = {"fr", "pt"}

_language = "en"
_catalog: dict = {}


def system_language() -> str:
    """Langue du téléphone (ou de l'ordinateur), si l'app la parle ; sinon anglais."""
    try:
        from PySide6.QtCore import QLocale
        names = list(QLocale.system().uiLanguages()) or [QLocale.system().name()]
    except Exception:  # noqa: BLE001 — sans Qt (outils, tests) : anglais
        return "en"
    for name in names:
        code = str(name).replace("_", "-").split("-")[0].lower()
        if code in LANGUAGES:
            return code
    return "en"


def resolve(choice) -> str:
    """Réglage « language » (SYSTEM ou un code) -> code de langue."""
    choice = str(choice or SYSTEM)
    return choice if choice in LANGUAGES else system_language()


def _load(module: str) -> dict:
    try:
        catalog = importlib.import_module(module).T
    except (ImportError, AttributeError):
        return {}
    return catalog if isinstance(catalog, dict) else {}


def catalog_for(code: str) -> dict:
    """Le catalogue d'une langue : celui du socle, complété (et corrigé) par celui de l'app."""
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
    """Texte traduit (et ses champs {nom} remplis)."""
    out = _catalog.get(text, text)
    if isinstance(out, tuple):      # entrée de pluriel utilisée au singulier
        out = out[0]
    if fields:
        try:
            return out.format(**fields)
        except (KeyError, IndexError, ValueError):
            return text.format(**fields)   # traduction abîmée : l'anglais
    return out


def ntr(one: str, other: str, n: int, /, **fields) -> str:
    """Singulier / pluriel : ntr("{n} bar", "{n} bars", count). {n} est rempli."""
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


# Langues qui écrivent les décimales avec une virgule (1,5)
_DECIMAL_COMMA = {"fr", "es", "it", "pt", "de"}


def decimal(value: float, digits: int = 1) -> str:
    """Nombre à virgule écrit comme dans la langue de l'app (1.5 / 1,5)."""
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if _language in _DECIMAL_COMMA else text


def N_(text: str, /) -> str:
    """Marque un texte à traduire à l'affichage (voir tr)."""
    return text
