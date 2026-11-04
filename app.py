"""Ce que le socle sait de l'app qui l'utilise : tout vient de `app_info.py`.

Chaque app a, à sa racine, un fichier `app_info.py` fait de simples constantes
(aucun import) : le socle (et les scripts de compilation Android, voir
android/app_config.py) les lit. Seul NAME est obligatoire ; tout le reste a
une valeur par défaut, donnée ici.

    from appcore import app
    app.name()          -> "RiffFinder"
    app.slug()          -> "rifffinder" (dossiers, journal, préfixes)
    app.get("CAPO_MAX", 9)

Le détail de chaque constante est dans template/app_info.py.
"""

from __future__ import annotations

import importlib
import types

# Valeurs par défaut des constantes de app_info.py
DEFAULTS = {
    "NAME": "App",
    "VERSION": "0.1.0",
    "SUPPORT_EMAIL": "",
    # Langues proposées (codes de appcore/i18n.py) ; l'anglais est toujours là
    "LANGUAGES": ("en", "fr", "es", "it", "pt", "de"),
    # Réglages recopiés dans le rapport d'erreur, en plus de ceux du socle
    "REPORT_SETTINGS": (),
    # Son : clé du réglage et instruments proposés (voir appcore/guitar_synth.py)
    "SOUND_SETTING": "sound/instrument",
    "VOICES": ("steel", "nylon"),
    "WARM_UP_NOTES": tuple(range(40, 77)) + tuple(range(77, 89)) + (38, 39),
    # Anciens noms de l'app : réglages et données repris au premier lancement
    "OLD_NAMES": (),
    # Android
    "ANDROID_PACKAGE": "",          # défaut : com.<slug>.app
    "JAVA_PACKAGE": "",             # défaut : org.<slug>
    "ANDROID_PERMISSIONS": ("MODIFY_AUDIO_SETTINGS",),
    "KEY_ALIAS": "",                # défaut : <slug>
    "KEYSTORE_NAME": "",            # défaut : <slug>-upload.jks
    "EXTRA_DIRS": (),               # dossiers de l'app à copier dans l'APK, en plus
    "GRADLE_DEPENDENCIES": (),      # bibliothèques Java (Gradle) du Java de l'app
    "LIBRARY_PERMISSIONS": (),      # autorisations que ces bibliothèques ajoutent (attendues)
}

_info = None


def info():
    """Le module app_info de l'app (un module vide s'il n'y en a pas : outils, tests)."""
    global _info
    if _info is None:
        try:
            _info = importlib.import_module("app_info")
        except ImportError:
            _info = types.ModuleType("app_info")
    return _info


def get(name: str, default=None):
    """Une constante de app_info.py (sinon `default`, sinon celle du socle)."""
    if default is None:
        default = DEFAULTS.get(name)
    return getattr(info(), name, default)


def name() -> str:
    return str(get("NAME"))


def version() -> str:
    return str(get("VERSION"))


def slug() -> str:
    """Le nom en minuscules, sans espace : dossiers (~/.rifffinder), journal…"""
    return "".join(c for c in name().lower() if c.isalnum()) or "app"


def support_email() -> str:
    return str(get("SUPPORT_EMAIL") or "")


def languages() -> tuple[str, ...]:
    codes = tuple(get("LANGUAGES") or ())
    return ("en",) + tuple(c for c in codes if c != "en")
