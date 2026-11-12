# Building an app as an Android application (APK / AAB)

The build is the same for every app of the base. Everything specific to an
app comes from its `app_info.py`: name (the APK's), version, Google Play
package (`ANDROID_PACKAGE`), permissions (`ANDROID_PERMISSIONS`), alias and
file of the upload key (`KEY_ALIAS`, `KEYSTORE_NAME`), extra folders to
bundle (`EXTRA_DIRS`), Java libraries (`GRADLE_DEPENDENCIES`,
`LIBRARY_PERMISSIONS`). The scripts are in `appcore/android/` and are run
**from the app's folder**. Below, `MyApp` = the app's name
(RiffFinder, PerfectPitch…).

The APK is built **on Linux**: this is a constraint of Qt's official tool
(`pyside6-android-deploy`). Two ways to do it from Windows:

- **A. In the cloud with GitHub**: nothing to install, the simplest.
- **B. On your PC with WSL2**: an Ubuntu inside Windows, faster to iterate.

The build uses the versions pinned by Qt's tool: **PySide6
6.12.0, buildozer 1.6.0, NDK r28c, JDK 17**, Python 3.11 for the tool (on the
PC) and **Python 3.14** in the app (python-for-android v2026.05.09's, chosen
by Qt 6.12's tool; the 6.12 Android wheels are "abi3" and work with any
Python ≥ 3.10). `PYSIDE_VERSION=6.11.2` brings back the old combination
(buildozer 1.5.0, NDK r27c, Python 3.11 in the app).

**16 KB memory pages** (Android 15+, required by Google Play): with NDK
r28c, everything python-for-android builds (Python and its modules, ssl,
crypto, sqlite, libffi, the launcher) is aligned on 16 KB, and PySide6 6.12's
Qt / shiboken libraries are too. `appcore/android/check_16k.py` checks the
APK (and the AAB) at the end and lists what is not, including the modules
stored in `libpybundle.so`.

**Size**: Qt's tool bundles the whole PySide6 wheel (Qt 3D, Charts,
QML, WebView…), twice: once in the app's libraries, once in
`libpybundle.so`, unpacked at first start. `appcore/android/slim_bundle.py`,
called by the PySide6 recipe ("slim" fix), only keeps what Qt loads and what
those libraries need (by reading their ELF dependencies). On RiffFinder's
1.1.0 APK: 100 MB of libraries and 214 MB of Python package less.
`APPCORE_SLIM= bash appcore/android/build_apk.sh` (empty variable) keeps everything.

The APK targets **arm64** phones (nearly all recent phones) and
**Android 16 (API 36)**, the version required by Google Play; without this
setting, the phone warns that the app is "built for an older version of
Android". It installs from **Android 9 (API 28)**: that is the minimum of
Qt 6.8 and later, and Google Play refuses a minimum below Android 7
(API 24) ("Play automatic protection requires SDK 24").

> Qt's Android tool for Python is still a "technical preview".
> `appcore/android/build_apk.sh` applies the known workarounds
> (see `appcore/android/patch_deploy_tools.py` and `p4a_hook.py`).

---

## A. Building in the cloud (GitHub Actions)

1. The app's repository on GitHub holds the base as a **submodule**
   (`appcore/`). If the base's repository is **private**, GitHub Actions must be
   able to read it: create a token (GitHub › Settings › Developer settings ›
   Personal access tokens › Fine-grained, "Contents" read access to the
   `appcore` repository **and to the app's repository**, since the same token
   checks out both) and add it to the app's repository: **Settings > Secrets
   and variables > Actions > New repository secret**, name `APPCORE_TOKEN`.
   If the base is public, nothing to do.
2. The build workflows are in the app's `.github/workflows/` (copies of
   `appcore/templates/github/workflows/`, the same for every app):
   `android.yml` (test APK), `release.yml` (signed AAB for Google Play) and
   `keystore.yml` (create the upload key, once).
3. **Signing (once)**: for the phone to accept each new version over the
   old one, the APK must always be signed with the same key. If you created
   the Google Play key (`keystore.yml` workflow), add these secrets to the
   repository:
   - `KEYSTORE_B64`: the content of the `upload.jks.b64` file;
   - `KEYSTORE_PASSWORD`: the password of that key.

   Without these secrets, a test key is created and kept in GitHub's cache
   (it disappears if you do not build for 7 days). The run's log says
   "Signing: upload key" or "test key".
4. On the repository page: **Actions** tab > **Android APK** > **Run workflow**
   (leave the "targetSdk" field at 36 unless you have a particular need).
5. Wait for the end (30 to 60 min the first time, faster afterwards thanks to the cache).
6. Open the finished run, **Artifacts** section: download **MyApp-apk**
   (a .zip holding the APK).

## B. Building on your PC (WSL2 + Ubuntu)

1. In PowerShell **as administrator**:
   ```
   wsl --install -d Ubuntu-24.04
   ```
   Restart, then open "Ubuntu" from the Start menu (choose a user name
   and a password).
2. In Ubuntu, install the tools (only once):
   ```
   sudo apt-get update
   sudo apt-get install -y autoconf automake libtool libltdl-dev pkg-config openjdk-17-jdk zip unzip ccache curl git rsync
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Close and reopen Ubuntu (so that `uv` is found).
3. Copy the project into Linux (much faster than building on D:),
   base included:
   ```
   rsync -a --exclude .git --exclude build --exclude dist /mnt/d/Projects/MyApp/ ~/MyApp/
   cd ~/MyApp
   bash appcore/android/build_apk.sh
   ```
   The first time: 20 to 40 min and several GB downloaded (SDK, NDK, Qt).
4. The APK lands in `~/MyApp/dist/`. To get it back on Windows:
   ```
   cp dist/*.apk /mnt/d/Projects/MyApp/
   ```

After changing the code (the app's or the base's), run the same `rsync`
command again then `bash appcore/android/build_apk.sh`: everything already
downloaded is reused. A build environment from before the base
(`build/android/venv` patched by the app's old scripts) is rebuilt
automatically the first time.

## Installing the APK on the phone

- Copy the `.apk` file to the phone (USB cable, Google Drive, email…),
  open it and allow "Install unknown apps" when Android asks.
- **"App not installed" / "conflicts with an existing package"**: the
  installed version was signed with another key. Uninstall it one
  last time, then install the new one; afterwards updates go through
  directly. Uninstalling erases the app's data: export what you want to
  keep first.
- Or, with the phone plugged in over USB with debugging enabled: `adb install -r MyApp.apk`.

The application opens **full screen, in landscape** (both ways), and
the screen **stays on** while it is shown, even without touching it (as
during a video). As soon as you switch to another app, the phone goes back to
sleep as usual. This is the base's small Java activity
(`appcore/android/java/KeepAwakeActivity.java.in`), which `build_apk.sh` puts in
the app's Java package (`JAVA_PACKAGE`) and adds to the APK.

**An app's Java** (Google Play purchases, notifications…): its files go
in the app's `android/java/<package>/` (same package as `JAVA_PACKAGE`, for
example `android/java/org/myapp/`); `build_apk.sh` adds them next to the
base's (an app file with the same name replaces the base's). To react to the
moments of the activity's life, the app writes an `AppHooks.java`
with the static methods `onCreate(Activity)`, `onResume(Activity)` and
`onRequestPermissionsResult(Activity, int, String[], int[])` (without it, the
base provides an empty one); an error in these methods is logged
without stopping the app. The Java libraries it uses are declared in
`GRADLE_DEPENDENCIES` (`app_info.py`, e.g.
`"com.android.billingclient:billing:8.3.0"`), added to `build.gradle` by
the fix to Qt's tool; the permissions these libraries add by themselves
(BILLING, WAKE_LOCK…) go in `LIBRARY_PERMISSIONS`, so that the end-of-build
check does not flag them. Full example: PerfectPitch (Pro purchase, evening
reminder).

## If something goes wrong

- **The application closes at start-up, or crashes**: start it again. An error at
  start-up is shown in a "MyApp could not start" window; a crash is shown at
  the next start ("MyApp stopped last time"). Tap **Send by email**: the
  phone's email app opens with the report, addressed to `SUPPORT_EMAIL`
  (`app_info.py`); all that is left is to tap Send. The same report is in
  **Settings › Error report**, with the app's log (what it did just before)
  and, since Android 11, the exit reason given by Android (Java or native crash
  with its stack, "not responding", memory). **Clear** empties the log once the
  report is sent. If nothing shows at all: plug the phone in and run
  `adb logcat | grep -iE "python|qt|shiboken|AndroidRuntime|MyApp"`.
- **No sound**: sound goes through Qt Multimedia. The log says what the audio
  output answered ("sound: …" or "no sound: …" lines); without sound,
  everything stays visual: the Play buttons still move the highlighting on.
  Check the phone's **media** volume first.
- **The first sound is a little slow**: notes are computed at first use
  then cached (the app's folder). At start-up, the app prepares them in the
  background (`WARM_UP_NOTES`); later starts are immediate.
- **Downloading the wheels fails (404 error)**: check the version
  available on https://download.qt.io/official_releases/QtForPython/pyside6/
  then run `PYSIDE_VERSION=6.x.y bash appcore/android/build_apk.sh`. Then keep
  the same version everywhere. The script tries both wheel names
  (`cp310-abi3` since 6.12, `cp311-cp311` before).
- **Gradle error "Could not resolve …"** (a library of
  `GRADLE_DEPENDENCIES`): Gradle downloads it (google() and mavenCentral()
  repositories): the build needs Internet, and the exact name with its version
  (`group:name:version`). `APPCORE_GRADLE_DEPS= bash
  appcore/android/build_apk.sh` (empty variable) builds without them, for a
  test (the Java using them will no longer compile).
- **The app closes right at start-up**: at start-up, Qt loads a list of
  libraries and stops at the first one missing from the APK ("QtLoader: Can't
  find …"), or crashes if they are out of order (Multimedia before Core:
  SIGSEGV in QJniEnvironment). `appcore/android/p4a_hook.py` fixes the list
  and its order before Gradle ("[APPCORE-PATCH]" lines of the log) and
  `appcore/android/check_qt_libs.py` checks the APK / AAB at the end: the
  build stops with an error if one is missing, rather than producing an
  app that closes.
- **A Qt module is missing at start-up** (`ModuleNotFoundError: PySide6.Qt…`):
  the slimming removed too much. Run again with `APPCORE_SLIM=` (empty)
  to confirm; the list of what is removed is in the build log
  ("- libs/…" lines). Qt's tool chooses the modules to bundle from the
  project's imports: each app's `main.py` lists the base's
  (`_qt_modules_for_android`); an app using another Qt module simply
  imports it in its code.
- **End of build "not fully 16 KB compatible"**: the list shown
  gives the files aligned on 4 KB. Check that the NDK used is really
  r28c (`NDK_VERSION`) and that PySide6 is 6.12.
- **Permissions**: the APK only asks for those of `ANDROID_PERMISSIONS`.
  Those added by default by Qt's tool (camera, Bluetooth, Internet, network
  state, storage) are removed by `appcore/android/patch_deploy_tools.py`;
  the end of `build_apk.sh` shows the APK's list and warns if another one
  comes back. Without the Internet permission, the app cannot send anything
  itself: the error report goes through the email app.
- **♭ ♯ symbols shown as boxes**: the app ships its symbols fonts
  (the app's, `symbol_font_data.py`, and the base's). If a new
  symbol shows as a box, run `python appcore/tools/build_font.py` again
  from the app's folder (see the base's README) and rebuild.
- **Language**: the app starts in the phone's language if it offers it
  (`LANGUAGES`), otherwise in English. The translations (`locales/` of the app and of
  `appcore/`) are copied into the APK by `build_apk.sh`: if they are missing,
  everything is shown in English.

## Publishing on Google Play

The Play Store asks for a **signed .aab** package with the upload key:

1. `VERSION` in `app_info.py`: the displayed number ("1.2.0").
2. **Actions** tab > **Android AAB (Play Store)** > **Run workflow**, with
   **version_code** = the last one sent to Google Play **+ 1** (an integer;
   the Play Console refuses a number already used).
3. At the end of the log: permissions, 16 KB pages, Qt libraries
   ("✓ … present").
4. Download the **MyApp-aab** artifact and upload the `.aab` to the Play
   Console (closed testing, then production), with the release notes.

Locally (WSL): `bash appcore/android/build_apk.sh` once, then
`VERSION_CODE=… bash appcore/android/release_aab.sh` (key in
`~/<KEYSTORE_NAME>`, created once with `bash appcore/android/make_keystore.sh`).

**Never change** `ANDROID_PACKAGE` or the upload key of a published app:
Google Play would treat it as another app.
