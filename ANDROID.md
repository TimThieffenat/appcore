# Compiler une app en application Android (APK / AAB)

La compilation est la même pour toutes les apps du socle. Tout ce qui est
propre à une app vient de son `app_info.py` : nom (celui de l'APK), version,
paquet Google Play (`ANDROID_PACKAGE`), autorisations (`ANDROID_PERMISSIONS`),
alias et fichier de la clé d'envoi (`KEY_ALIAS`, `KEYSTORE_NAME`), dossiers à
embarquer en plus (`EXTRA_DIRS`), bibliothèques Java (`GRADLE_DEPENDENCIES`,
`LIBRARY_PERMISSIONS`). Les scripts sont dans `appcore/android/` et se
lancent **depuis le dossier de l'app**. Ci-dessous, `MonApp` = le nom de l'app
(RiffFinder, PerfectPitch…).

L'APK se fabrique **sous Linux** : c'est une contrainte de l'outil officiel de
Qt (`pyside6-android-deploy`). Deux façons de faire depuis Windows :

- **A. Dans le cloud avec GitHub** : rien à installer, le plus simple.
- **B. Sur ton PC avec WSL2** : un Ubuntu dans Windows, plus rapide pour itérer.

La compilation utilise les versions figées par l'outil de Qt : **PySide6
6.12.0, buildozer 1.6.0, NDK r28c, JDK 17**, Python 3.11 pour l'outil (sur le
PC) et **Python 3.14** dans l'app (celui de python-for-android v2026.05.09,
choisi par l'outil de Qt 6.12 ; les wheels Android de 6.12 sont « abi3 » et
marchent avec tout Python ≥ 3.10). `PYSIDE_VERSION=6.11.2` reprend l'ancienne
combinaison (buildozer 1.5.0, NDK r27c, Python 3.11 dans l'app).

**Pages mémoire de 16 Ko** (Android 15+, exigées par Google Play) : avec le NDK
r28c, tout ce que python-for-android compile (Python et ses modules, ssl,
crypto, sqlite, libffi, le lanceur) est aligné sur 16 Ko, et les bibliothèques
Qt / shiboken de PySide6 6.12 le sont aussi. `appcore/android/check_16k.py`
vérifie l'APK (et l'AAB) à la fin et liste ce qui ne l'est pas, y compris les
modules rangés dans `libpybundle.so`.

**Taille** : l'outil de Qt embarque toute la roue PySide6 (Qt 3D, Charts,
QML, WebView…), en double : une fois dans les bibliothèques de l'app, une fois
dans `libpybundle.so`, décompressé au premier lancement.
`appcore/android/slim_bundle.py`, appelé par la recette PySide6 (correctif
« slim »), ne garde que ce que Qt charge et ce dont ces bibliothèques ont
besoin (en lisant leurs dépendances ELF). Sur l'APK 1.1.0 de RiffFinder :
100 Mo de bibliothèques et 214 Mo de paquet Python en moins.
`APPCORE_SLIM= bash appcore/android/build_apk.sh` (variable vide) garde tout.

L'APK vise les téléphones **arm64** (quasiment tous les téléphones récents) et
**Android 16 (API 36)**, la version exigée par Google Play ; sans ce réglage,
le téléphone prévient que l'app est « conçue pour une ancienne version
d'Android ». Elle s'installe à partir d'**Android 9 (API 28)** : c'est le
minimum de Qt 6.8 et suivants, et Google Play refuse un minimum sous Android 7
(API 24) (« La protection automatique Play nécessite le SDK 24 »).

> L'outil Android de Qt pour Python est encore un « aperçu technique ».
> `appcore/android/build_apk.sh` applique les contournements connus
> (voir `appcore/android/patch_deploy_tools.py` et `p4a_hook.py`).

---

## A. Compiler dans le cloud (GitHub Actions)

1. Le dépôt de l'app sur GitHub contient le socle en **sous-module**
   (`appcore/`). Si le dépôt du socle est **privé**, GitHub Actions doit pouvoir
   le lire : crée un jeton (GitHub › Settings › Developer settings › Personal
   access tokens › Fine-grained, accès en lecture « Contents » au dépôt
   `appcore`) et ajoute-le dans le dépôt de l'app : **Settings > Secrets and
   variables > Actions > New repository secret**, nom `APPCORE_TOKEN`. Si le
   socle est public, rien à faire.
2. Les recettes de compilation sont dans `.github/workflows/` de l'app (copies
   de `appcore/templates/github/workflows/`, les mêmes pour toutes les apps) :
   `android.yml` (APK de test), `release.yml` (AAB signé pour Google Play) et
   `keystore.yml` (créer la clé d'envoi, une fois).
3. **Signature (une fois)** : pour que le téléphone accepte chaque nouvelle
   version par-dessus l'ancienne, l'APK doit toujours être signé avec la même
   clé. Si tu as créé la clé Google Play (recette `keystore.yml`), ajoute dans
   le dépôt les secrets :
   - `KEYSTORE_B64` : le contenu du fichier `upload.jks.b64` ;
   - `KEYSTORE_PASSWORD` : le mot de passe de cette clé.

   Sans ces secrets, une clé de test est créée et gardée dans le cache de GitHub
   (elle disparaît si tu ne compiles pas pendant 7 jours). Le résumé du run
   indique « Signature : clé d'envoi » ou « clé de test ».
4. Sur la page du dépôt : onglet **Actions** > **Android APK** > **Run workflow**
   (le champ « targetSdk » reste à 36, sauf besoin particulier).
5. Attends la fin (30 à 60 min la première fois, plus rapide ensuite grâce au cache).
6. Ouvre le run terminé, section **Artifacts** : télécharge **MonApp-apk**
   (un .zip qui contient l'APK).

## B. Compiler sur ton PC (WSL2 + Ubuntu)

1. Dans PowerShell **en administrateur** :
   ```
   wsl --install -d Ubuntu-24.04
   ```
   Redémarre, puis ouvre « Ubuntu » depuis le menu Démarrer (choisis un nom
   d'utilisateur et un mot de passe).
2. Dans Ubuntu, installe les outils (une seule fois) :
   ```
   sudo apt-get update
   sudo apt-get install -y autoconf automake libtool libltdl-dev pkg-config openjdk-17-jdk zip unzip ccache curl git rsync
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Ferme puis rouvre Ubuntu (pour que `uv` soit trouvé).
3. Copie le projet dans Linux (beaucoup plus rapide que de compiler sur D:),
   socle compris :
   ```
   rsync -a --exclude .git --exclude build --exclude dist /mnt/d/Projects/MonApp/ ~/MonApp/
   cd ~/MonApp
   bash appcore/android/build_apk.sh
   ```
   La première fois : 20 à 40 min et plusieurs Go téléchargés (SDK, NDK, Qt).
4. L'APK arrive dans `~/MonApp/dist/`. Pour le récupérer sous Windows :
   ```
   cp dist/*.apk /mnt/d/Projects/MonApp/
   ```

Après une modification du code (de l'app ou du socle), relance la même commande
`rsync` puis `bash appcore/android/build_apk.sh` : tout ce qui est déjà
téléchargé est réutilisé. Un environnement de compilation d'avant le socle
(`build/android/venv` corrigé par les anciens scripts de l'app) est refait tout
seul la première fois.

## Installer l'APK sur le téléphone

- Copie le fichier `.apk` sur le téléphone (câble USB, Google Drive, e-mail…),
  ouvre-le et autorise « Installer des applications inconnues » quand Android le demande.
- **« Application non installée » / « conflit avec un paquet existant »** : la
  version installée a été signée avec une autre clé. Désinstalle-la une
  dernière fois, puis installe la nouvelle ; ensuite les mises à jour passent
  directement. Désinstaller efface les données de l'app : exporte d'abord ce
  que tu veux garder.
- Ou, téléphone branché en USB avec le débogage activé : `adb install -r MonApp.apk`.

L'application s'ouvre en **plein écran, en paysage** (dans les deux sens), et
l'écran **reste allumé** tant qu'elle est affichée, même sans y toucher (comme
pendant une vidéo). Dès qu'on passe à une autre app, le téléphone se remet en
veille normalement. C'est la petite activité Java du socle
(`appcore/android/java/KeepAwakeActivity.java.in`), que `build_apk.sh` met dans
le paquet Java de l'app (`JAVA_PACKAGE`) et ajoute à l'APK.

**Le Java d'une app** (achats Google Play, notifications…) : ses fichiers vont
dans `android/java/<paquet>/` de l'app (même paquet que `JAVA_PACKAGE`, par
exemple `android/java/org/monapp/`) ; `build_apk.sh` les ajoute à côté de ceux
du socle (un fichier de l'app du même nom remplace celui du socle). Pour
réagir aux moments de la vie de l'activité, l'app écrit un `AppHooks.java`
avec les méthodes statiques `onCreate(Activity)`, `onResume(Activity)` et
`onRequestPermissionsResult(Activity, int, String[], int[])` (sans lui, le
socle en met un vide) ; une erreur dans ces méthodes est notée dans le journal
sans arrêter l'app. Les bibliothèques Java qu'il utilise se déclarent dans
`GRADLE_DEPENDENCIES` (`app_info.py`, ex.
`"com.android.billingclient:billing:8.3.0"`), ajoutées au `build.gradle` par
le correctif de l'outil de Qt ; les autorisations que ces bibliothèques
ajoutent d'elles-mêmes (BILLING, WAKE_LOCK…) vont dans `LIBRARY_PERMISSIONS`,
pour que la vérification de fin de compilation ne les signale pas. Exemple
complet : PerfectPitch (achat Pro, rappel du soir).

## Si quelque chose ne va pas

- **L'application se ferme au démarrage, ou plante** : relance-la. Une erreur au
  démarrage s'affiche dans une fenêtre « MonApp could not start » ; un
  plantage s'affiche au lancement suivant (« MonApp stopped last time »).
  Appuie sur **Envoyer par e-mail** : l'app d'e-mail du téléphone s'ouvre avec le
  rapport, adressé à `SUPPORT_EMAIL` (`app_info.py`) ; il n'y a plus qu'à
  appuyer sur Envoyer. Le même rapport est dans **Réglages › Rapport d'erreur**,
  avec le journal de l'app (ce qu'elle a fait juste avant) et, depuis
  Android 11, la cause de l'arrêt donnée par Android (plantage Java ou natif
  avec sa pile, « ne répond pas », mémoire). **Effacer** vide le journal une
  fois le rapport envoyé. Si rien ne s'affiche du tout : branche le téléphone et lance
  `adb logcat | grep -iE "python|qt|shiboken|AndroidRuntime|MonApp"`.
- **Pas de son** : le son passe par Qt Multimedia. Si le module manque, l'app
  le note dans le journal (« no sound ») et tout reste visuel : les boutons
  Lecture font quand même avancer le surlignage.
- **Le premier son est un peu lent** : les notes sont calculées au premier usage
  puis gardées en cache (dossier de l'app). Au démarrage, l'app les prépare en
  arrière-plan (`WARM_UP_NOTES`) ; les lancements suivants sont immédiats.
- **Le téléchargement des wheels échoue (erreur 404)** : vérifie la version
  disponible sur https://download.qt.io/official_releases/QtForPython/pyside6/
  puis lance `PYSIDE_VERSION=6.x.y bash appcore/android/build_apk.sh`. Garde
  alors la même version partout. Le script essaie les deux noms de wheels
  (`cp310-abi3` depuis 6.12, `cp311-cp311` avant).
- **Erreur Gradle « Could not resolve … »** (une bibliothèque de
  `GRADLE_DEPENDENCIES`) : Gradle la télécharge (dépôts google() et
  mavenCentral()) : il faut Internet pendant la compilation, et le nom exact
  avec sa version (`groupe:nom:version`). `APPCORE_GRADLE_DEPS= bash
  appcore/android/build_apk.sh` (variable vide) compile sans elles, pour un
  essai (le Java qui s'en sert ne compilera plus).
- **L'app se ferme dès son lancement** : au démarrage, Qt charge une liste de
  bibliothèques et s'arrête à la première absente de l'APK (« QtLoader: Can't
  find … »), ou plante si elles sont dans le désordre (Multimedia avant Core :
  SIGSEGV dans QJniEnvironment). `appcore/android/p4a_hook.py` corrige la liste
  et son ordre avant Gradle (lignes « [APPCORE-PATCH] » du journal) et
  `appcore/android/check_qt_libs.py` vérifie l'APK / l'AAB à la fin : la
  compilation s'arrête en erreur s'il en manque une, plutôt que de produire une
  app qui se ferme.
- **Un module Qt manque au démarrage** (`ModuleNotFoundError: PySide6.Qt…`) :
  l'allègement a retiré trop de choses. Relance avec `APPCORE_SLIM=` (vide)
  pour confirmer ; la liste de ce qui est retiré est dans le journal de
  compilation (lignes « - libs/… »). L'outil de Qt choisit les modules à
  embarquer d'après les imports du projet : le `main.py` de chaque app liste
  ceux du socle (`_qt_modules_for_android`) ; une app qui utilise un autre
  module Qt l'importe simplement dans son code.
- **Fin de compilation « pas entièrement compatible 16 Ko »** : la liste
  affichée donne les fichiers alignés sur 4 Ko. Vérifie que le NDK utilisé est
  bien r28c (`NDK_VERSION`) et que PySide6 est en 6.12.
- **Autorisations** : l'APK ne demande que celles de `ANDROID_PERMISSIONS`.
  Celles ajoutées d'office par l'outil de Qt (caméra, Bluetooth, Internet, état
  du réseau, stockage) sont retirées par `appcore/android/patch_deploy_tools.py` ;
  la fin de `build_apk.sh` affiche la liste de l'APK et prévient si une autre
  réapparaît. Sans autorisation Internet, l'app ne peut rien envoyer elle-même :
  le rapport d'erreur passe par l'app d'e-mail.
- **Symboles ♭ ♯ affichés en carrés** : l'app embarque ses polices de symboles
  (celle de l'app, `symbol_font_data.py`, et celle du socle). Si un nouveau
  symbole s'affiche en carré, relance `python appcore/tools/build_font.py`
  depuis le dossier de l'app (voir README du socle) et recompile.
- **Langue** : l'app démarre dans la langue du téléphone si elle la propose
  (`LANGUAGES`), sinon en anglais. Les traductions (`locales/` de l'app et de
  `appcore/`) sont copiées dans l'APK par `build_apk.sh` : si elles manquent,
  tout s'affiche en anglais.

## Publier sur Google Play

Le Play Store demande un paquet **.aab signé** avec la clé d'envoi :

1. `VERSION` dans `app_info.py` : le numéro affiché (« 1.2.0 »).
2. Onglet **Actions** > **Android AAB (Play Store)** > **Run workflow**, avec
   **version_code** = le dernier envoyé sur Google Play **+ 1** (un entier ;
   la Play Console refuse un numéro déjà utilisé).
3. À la fin du journal : autorisations, pages de 16 Ko, bibliothèques de Qt
   (« ✓ … présente(s) »).
4. Télécharge l'artefact **MonApp-aab** et envoie le `.aab` dans la Play
   Console (test fermé, puis production), avec les notes de version.

En local (WSL) : `bash appcore/android/build_apk.sh` une fois, puis
`VERSION_CODE=… bash appcore/android/release_aab.sh` (clé dans
`~/<KEYSTORE_NAME>`, créée une fois avec `bash appcore/android/make_keystore.sh`).

**Ne change jamais** `ANDROID_PACKAGE` ni la clé d'envoi d'une app publiée :
Google Play la traiterait comme une autre app.
