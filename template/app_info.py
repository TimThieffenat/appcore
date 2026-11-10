"""The application's name, version and settings, read by the base (appcore/app.py)
and by the Android build (appcore/android/app_config.py).

Nothing but constants (no import): the scripts read this file without
running the app. Only NAME is required; a missing constant takes the base's
default value (DEFAULTS in appcore/app.py), given here in a comment.
"""

# The app's name: shown, and the APK's name. A valid Java identifier (letters,
# digits, _; no spaces). The app's folder on desktop is
# ~/.<name in lower case>, settings are stored under this name.
NAME = "__APP_NAME__"
VERSION = "0.1.0"        # the displayed number (Google Play's versionCode is separate)
# Recipient of error reports (the report's "Send by email" button)
SUPPORT_EMAIL = "__EMAIL__"

# Languages offered (English, the language of the code, is always there). The
# base's texts are translated into these 6 languages; the app's, in locales/<code>.py.
LANGUAGES = ("en", "fr")                    # default: all 6 (en fr es it pt de)
# App settings copied into the error report (on top of language, theme,
# note names and instrument), to reproduce a problem in the same conditions
REPORT_SETTINGS = ()

# Sound (appcore/sound.py): key of the instrument setting, instruments offered
# ("steel", "nylon": recorded guitars; "keys": synthesised keyboard),
# and notes prepared in the background at start-up, most used first.
SOUND_SETTING = "sound/instrument"
VOICES = ("steel", "nylon", "keys")
WARM_UP_NOTES = tuple(range(48, 77)) + tuple(range(36, 48)) + tuple(range(77, 89))

# Former names of the app: at the first start under the new name, its settings
# and data are taken over (on desktop).
OLD_NAMES = ()

# --- Android ----------------------------------------------------------------------
# Google Play identifier: final after the first release.
ANDROID_PACKAGE = "com.__app_slug__.app"    # default: com.<name in lower case>.app
JAVA_PACKAGE = "org.__app_slug__"           # package of the Java activity (screen kept on…)
# Permissions (without the android.permission. prefix). MODIFY_AUDIO_SETTINGS is for
# sound (granted without asking); RECORD_AUDIO for a microphone (tuner…).
ANDROID_PERMISSIONS = ("MODIFY_AUDIO_SETTINGS",)
# Google Play upload key: alias in the file, and file name in ~
KEY_ALIAS = "__app_slug__"
KEYSTORE_NAME = "__app_slug__-upload.jks"
# App folders copied into the APK on top of locales/ and sounds/ (libraries…)
EXTRA_DIRS = ()
# Java libraries added by Gradle (Google Play Billing, WorkManager…),
# for the app's Java (android/java/<package>/, plugged in by AppHooks.java),
# and the permissions they add to the APK by themselves (expected by the
# end-of-build check), without the android.permission. prefix.
GRADLE_DEPENDENCIES = ()      # e.g. ("com.android.billingclient:billing:8.3.0",)
LIBRARY_PERMISSIONS = ()      # e.g. ("com.android.vending.BILLING",)
