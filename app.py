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
    # Screen: "landscape" (phone in landscape, icon rail on the left) or
    # "portrait" (navigation bar at the bottom); and the home page (its
    # index in main.py's pages()): opened at start-up, Back returns to it
    "ORIENTATION": "landscape",
    "HOME_PAGE": 0,
    # Android
    "ANDROID_PACKAGE": "",          # default: com.<slug>.app
    "JAVA_PACKAGE": "",             # default: org.<slug>
    "ANDROID_PERMISSIONS": ("MODIFY_AUDIO_SETTINGS",),
    "KEY_ALIAS": "",                # default: <slug>
    "KEYSTORE_NAME": "",            # default: <slug>-upload.jks
    "EXTRA_DIRS": (),               # extra app folders copied into the APK
    "GRADLE_DEPENDENCIES": (),      # Java libraries (Gradle) used by the app's Java
    "LIBRARY_PERMISSIONS": (),      # permissions those libraries add (expected)
    # Pro version (pro.py): Google Play product ID of the one-time purchase ("":
    # no Pro version), fingerprint and prefix of the reviewers' unlock code,
    # instruments reserved to Pro
    "PRO_PRODUCT": "",
    "UNLOCK_CODE_SHA256": "",
    "UNLOCK_CODE_PREFIX": "",       # default: the first letters of the name
    "PRO_VOICES": (),
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


def portrait() -> bool:
    """The app is designed for a phone in portrait (navigation bar at the bottom)."""
    return str(get("ORIENTATION")).lower() == "portrait"


def home_page(pages=None) -> int:
    """The home page: opened at start-up, the one Back returns to. HOME_PAGE is
    its position, or the name of its icon ("chords"; needs `pages`, the list
    of (label, icon, class) given to the window)."""
    value = get("HOME_PAGE")
    if isinstance(value, str) and not value.strip().isdigit():
        for index, page in enumerate(pages or ()):
            if page[1] == value.strip():
                return index
        return 0
    try:
        index = max(0, int(value))
    except (TypeError, ValueError):
        return 0
    return min(index, max(0, len(pages) - 1)) if pages else index


def phone_size() -> tuple[int, int]:
    """Size of a phone (in points), for the interface check and the window."""
    return (390, 844) if portrait() else (850, 390)


def languages() -> tuple[str, ...]:
    codes = tuple(get("LANGUAGES") or ())
    return ("en",) + tuple(c for c in codes if c != "en")
