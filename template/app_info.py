"""Nom, version et réglages de l'application, lus par le socle (appcore/app.py)
et par la compilation Android (appcore/android/app_config.py).

Rien que des constantes (aucun import) : les scripts lisent ce fichier sans
lancer l'app. Seul NAME est obligatoire ; une constante absente prend la valeur
par défaut du socle (DEFAULTS de appcore/app.py), indiquée ici en commentaire.
"""

# Nom de l'app : affiché, et nom de l'APK. Un identifiant Java valide (lettres,
# chiffres, _ ; pas d'espace). Le dossier de l'app sur ordinateur est
# ~/.<nom en minuscules>, les réglages sont rangés sous ce nom.
NAME = "__APP_NAME__"
VERSION = "0.1.0"        # le numéro affiché (le versionCode de Google Play est à part)
# Destinataire des rapports d'erreur (bouton « Send by email » du rapport)
SUPPORT_EMAIL = "__EMAIL__"

# Langues proposées (l'anglais, langue du code, est toujours là). Les textes du
# socle sont traduits dans ces 6 langues ; ceux de l'app, dans locales/<code>.py.
LANGUAGES = ("en", "fr")                    # défaut : les 6 (en fr es it pt de)
# Réglages de l'app recopiés dans le rapport d'erreur (en plus de langue, thème,
# noms des notes et instrument), pour refaire un problème dans les mêmes conditions
REPORT_SETTINGS = ()

# Son (appcore/sound.py) : clé du réglage de l'instrument, instruments proposés
# (« steel », « nylon » : guitares enregistrées ; « keys » : clavier synthétisé),
# et notes préparées en arrière-plan au démarrage, les plus utilisées d'abord.
SOUND_SETTING = "sound/instrument"
VOICES = ("steel", "nylon", "keys")
WARM_UP_NOTES = tuple(range(48, 77)) + tuple(range(36, 48)) + tuple(range(77, 89))

# Anciens noms de l'app : au premier lancement sous le nouveau nom, ses réglages
# et ses données sont repris (sur ordinateur).
OLD_NAMES = ()

# --- Android ----------------------------------------------------------------------
# Identifiant Google Play : définitif après la première publication.
ANDROID_PACKAGE = "com.__app_slug__.app"    # défaut : com.<nom en minuscules>.app
JAVA_PACKAGE = "org.__app_slug__"           # paquet de l'activité Java (écran allumé…)
# Autorisations (sans le préfixe android.permission.). MODIFY_AUDIO_SETTINGS sert
# au son (accordée sans rien demander) ; RECORD_AUDIO pour un micro (accordeur…).
ANDROID_PERMISSIONS = ("MODIFY_AUDIO_SETTINGS",)
# Clé d'envoi Google Play : alias dans le fichier, et nom du fichier dans ~
KEY_ALIAS = "__app_slug__"
KEYSTORE_NAME = "__app_slug__-upload.jks"
# Dossiers de l'app à copier dans l'APK en plus de locales/ et sounds/ (bibliothèques…)
EXTRA_DIRS = ()
# Bibliothèques Java ajoutées par Gradle (Google Play Billing, WorkManager…),
# pour le Java de l'app (android/java/<paquet>/, branché par AppHooks.java),
# et les autorisations qu'elles ajoutent d'elles-mêmes à l'APK (attendues par la
# vérification de fin de compilation), sans le préfixe android.permission.
GRADLE_DEPENDENCIES = ()      # ex. ("com.android.billingclient:billing:8.3.0",)
LIBRARY_PERMISSIONS = ()      # ex. ("com.android.vending.BILLING",)
