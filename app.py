"""What the base knows about the app using it: everything comes from `app_info.py`.

Each app has, at its root, an `app_info.py` file made of plain constants
(no import): the base (and the Android build scripts, see
android/app_config.py) reads them. Only NAME is required; everything else has
a default value, given here.

    from appcore import app
    app.name()          -> "RiffFinder"
    app.slug()          -> "rifffinder" (folders, log, prefixes)
    app.get("CAPO_MAX", 9)

Each constant is described in template/app_info.py.
"""

from __future__ import annotations

import importlib
import types

# Default values of the app_info.py constants
DEFAULTS = {
    "NAME": "App",
    "VERSION": "0.1.0",
    "SUPPORT_EMAIL": "",
    # Languages offered (codes from appcore/i18n.py); English is always there
    "LANGUAGES": ("en", "fr", "es", "it", "pt", "de"),
    # Settings copied into the error report, on top of the base's ones
    "REPORT_SETTINGS": (),
    # Sound: setting key and instruments offered (see appcore/guitar_synth.py)
    "SOUND_SETTING": "sound/instrument",
    "VOICES": ("steel", "nylon"),
    "WARM_UP_NOTES": tuple(range(40, 77)) + tuple(range(77, 89)) + (38, 39),
    # Former names of the app: settings and data taken over at first start
    "OLD_NAMES": (),
    # Android
    "ANDROID_PACKAGE": "",          # default: com.<slug>.app
    "JAVA_PACKAGE": "",             # default: org.<slug>
    "ANDROID_PERMISSIONS": ("MODIFY_AUDIO_SETTINGS",),
    "KEY_ALIAS": "",                # default: <slug>
    "KEYSTORE_NAME": "",            # default: <slug>-upload.jks
    "EXTRA_DIRS": (),               # extra app folders copied into the APK
    "GRADLE_DEPENDENCIES": (),      # Java libraries (Gradle) used by the app's Java
    "LIBRARY_PERMISSIONS": (),      # permissions those libraries add (expected)
}

_info = None


def info():
    """The app's app_info module (an empty module if there is none: tools, tests)."""
    global _info
    if _info is None:
        try:
            _info = importlib.import_module("app_info")
        except ImportError:
            _info = types.ModuleType("app_info")
    return _info


def get(name: str, default=None):
    """A constant from app_info.py (else `default`, else the base's one)."""
    if default is None:
        default = DEFAULTS.get(name)
    return getattr(info(), name, default)


def name() -> str:
    return str(get("NAME"))


def version() -> str:
    return str(get("VERSION"))


def slug() -> str:
    """The name in lower case, no spaces: folders (~/.rifffinder), log…"""
    return "".join(c for c in name().lower() if c.isalnum()) or "app"


def support_email() -> str:
    return str(get("SUPPORT_EMAIL") or "")


def languages() -> tuple[str, ...]:
    codes = tuple(get("LANGUAGES") or ())
    return ("en",) + tuple(c for c in codes if c != "en")
