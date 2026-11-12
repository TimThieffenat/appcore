#!/usr/bin/env bash
#
# Builds the application as an Android APK (arm64) with pyside6-android-deploy.
#
# Run on Linux: Ubuntu 24.04 in WSL2 on Windows, or GitHub Actions,
# from the app's folder (the one holding main.py and app_info.py):
#
#   bash appcore/android/build_apk.sh
#
# Safe to run again: everything already downloaded is reused.
# Everything specific to the app (name, package, permissions, folders to
# bundle…) comes from its app_info.py (see android/app_config.py).
#
# Pinned versions (those of Qt's tool, see ANDROID.md):
# PySide6 6.12.0 · buildozer 1.6.0 · cython 0.29.33 · NDK r28c · JDK 17
# Python 3.11 for the tool (on the PC); Python 3.14 in the app (chosen by
# Qt's tool through python-for-android v2026.05.09).
# NDK r28c: everything python-for-android builds (Python, ssl, crypto,
# sqlite, libffi, the launcher) is aligned on 16 KB pages (Android 15+,
# required by Google Play); PySide6 6.12's Qt libraries are too.
# android/check_16k.py checks it at the end.
# PYSIDE_VERSION=6.11.2 brings back the old combination (buildozer 1.5.0, NDK
# r27c, Python 3.11 in the app), without 16 KB pages.
# Target Android: API 36 (APPCORE_ANDROID_API variable to change it).
# Minimum Android: API 28 = Android 9, Qt 6.8+'s minimum (APPCORE_ANDROID_MINAPI).
#
# --keep-deployment-files keeps buildozer.spec and the deployment/ folder:
# android/release_aab.sh needs them to make the Google Play AAB.
#
set -euo pipefail

PYSIDE_VERSION=${PYSIDE_VERSION:-6.12.0}
CORE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)    # the base (appcore/)
ROOT=${APP_ROOT:-$(cd "$CORE/.." && pwd)}                # the app's folder
[ -f "$ROOT/app_info.py" ] || { echo "app_info.py not found in $ROOT" >&2; exit 1; }
# The app's name, package, permissions… (app_info.py); the name must be a
# valid Java identifier (it is the APK's name)
CONFIG=$(python3 "$CORE/android/app_config.py" "$ROOT") || exit 1
eval "$CONFIG"
ANDROID_ARCH=${ANDROID_ARCH:-aarch64}    # aarch64 = recent phones (arm64-v8a)
case "$PYSIDE_VERSION" in
    6.11.*) DEFAULT_NDK=r27c; BUILDOZER_VERSION=1.5.0 ;;
    *)      DEFAULT_NDK=r28c; BUILDOZER_VERSION=1.6.0 ;;   # versions of Qt 6.12's tool
esac
NDK_VERSION=${NDK_VERSION:-$DEFAULT_NDK}
ANT_VERSION=${ANT_VERSION:-1.9.4}
CMDLINE_TOOLS=${CMDLINE_TOOLS:-commandlinetools-linux-6514223_latest.zip}
CYTHON_VERSION=0.29.33

BUILD=${BUILD_DIR:-$ROOT/build/android}
VENV=$BUILD/venv
APP=$BUILD/app
PY=$VENV/bin/python
DIST=$ROOT/dist

CACHE=$HOME/.pyside6_android_deploy
NDK_DIR=$CACHE/android-ndk/android-ndk-$NDK_VERSION
PLATFORM=$HOME/.buildozer/android/platform
SDK_DIR=$PLATFORM/android-sdk
ANT_DIR=$PLATFORM/apache-ant-$ANT_VERSION
QT_DOWNLOADS=https://download.qt.io/official_releases/QtForPython

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
step "1/8 Checking system tools"
# ---------------------------------------------------------------------------
[ "$(uname -s)" = "Linux" ] || fail "run on Linux (Ubuntu in WSL2 on Windows)."
PACKAGES=(autoconf automake libtool libltdl-dev pkg-config openjdk-17-jdk zip unzip ccache curl git)
# libltdl-dev provides the LT_SYS_SYMBOL_USCORE macro, which libffi needs
# (without it: "possibly undefined macro: LT_SYS_SYMBOL_USCORE").
missing=()
for pkg in "${PACKAGES[@]}"; do
    dpkg -s "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
done
if [ ${#missing[@]} -gt 0 ] && [ -n "${CI:-}" ]; then
    # On GitHub Actions: install what is missing ourselves.
    sudo apt-get update -qq
    sudo apt-get install -y "${missing[@]}"
    missing=()
fi
[ ${#missing[@]} -eq 0 ] || fail "missing packages. Install them with:
    sudo apt-get update && sudo apt-get install -y ${missing[*]}"

export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}
[ -x "$JAVA_HOME/bin/javac" ] || fail "JDK 17 not found in $JAVA_HOME"
export PATH="$JAVA_HOME/bin:$PATH"

# Possible proxy: Java does not read http(s)_proxy, give it to Gradle.
PROXY=${https_proxy:-${http_proxy:-}}
if [ -n "$PROXY" ]; then
    host=$(printf '%s' "$PROXY" | sed -E 's#^[a-z]+://##; s#/.*$##; s#:.*$##')
    port=$(printf '%s' "$PROXY" | sed -E 's#^[a-z]+://##; s#/.*$##; s#^[^:]*:##')
    [ "$port" = "$host" ] && port=80
    mkdir -p "$HOME/.gradle"
    if ! grep -q "systemProp.https.proxyHost" "$HOME/.gradle/gradle.properties" 2>/dev/null; then
        printf 'systemProp.http.proxyHost=%s\nsystemProp.http.proxyPort=%s\nsystemProp.https.proxyHost=%s\nsystemProp.https.proxyPort=%s\n' \
            "$host" "$port" "$host" "$port" >> "$HOME/.gradle/gradle.properties"
    fi
    SDK_PROXY=(--proxy=http "--proxy_host=$host" "--proxy_port=$port")
else
    SDK_PROXY=()
fi

# ---------------------------------------------------------------------------
step "2/8 Python 3.11 environment (for the build tool)"
# ---------------------------------------------------------------------------
mkdir -p "$BUILD"
# A venv patched by the app's old scripts (before the base: tags
# THECORDS-PATCH, PERFECTPITCH-PATCH…) cannot receive the base's fixes:
# it is rebuilt (only the Python packages are downloaded again).
if [ -d "$VENV" ] && grep -rqsE "(THECORDS|PERFECTPITCH|[A-Z]+)-PATCH" \
        "$VENV"/lib/python3.11/site-packages/PySide6/scripts/deploy_lib/android/buildozer.py \
        && ! grep -qs "APPCORE-PATCH" \
        "$VENV"/lib/python3.11/site-packages/PySide6/scripts/deploy_lib/android/buildozer.py; then
    echo "Old build environment (from before appcore): rebuilding it."
    rm -rf "$VENV"
fi
if [ ! -x "$PY" ]; then
    if command -v uv >/dev/null; then
        uv venv --python 3.11 "$VENV"
    elif command -v python3.11 >/dev/null; then
        python3.11 -m venv "$VENV"
    else
        fail "Python 3.11 not found. The simplest: install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh   (then reopen the terminal)"
    fi
fi
"$PY" -c 'import sys; assert sys.version_info[:2] == (3, 11)' || fail "the venv is not Python 3.11"
# buildozer runs "pip install --user": user packages must be visible.
sed -i 's/^include-system-site-packages *=.*/include-system-site-packages = true/' "$VENV/pyvenv.cfg"

install() {
    if command -v uv >/dev/null; then uv pip install --python "$PY" -q "$@"
    else "$PY" -m pip install -q "$@"; fi
}
# EXACT versions: otherwise the tool reinstalls buildozer and undoes the fixes.
install pip "pyside6==$PYSIDE_VERSION" "buildozer==$BUILDOZER_VERSION" "cython==$CYTHON_VERSION"
REQS=$("$PY" -c "import PySide6, pathlib; print(pathlib.Path(PySide6.__file__).parent / 'scripts' / 'requirements-android.txt')")
[ -f "$REQS" ] && install -r "$REQS"

# ---------------------------------------------------------------------------
step "3/8 Fixing the deployment tool"
# ---------------------------------------------------------------------------
SITE=$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
"$PY" "$CORE/android/patch_deploy_tools.py" "$SITE"

# ---------------------------------------------------------------------------
step "4/8 Wheels Android de PySide6 ($ANDROID_ARCH)"
# ---------------------------------------------------------------------------
# Wheel names: "cp310-abi3" since 6.12 (valid for any Python
# >= 3.10), "cp311-cp311" before.
wheel() {   # wheel pyside6|shiboken6: downloads if needed, prints the path
    local tag file
    for tag in cp310-abi3 cp311-cp311; do
        file=$BUILD/$1-$PYSIDE_VERSION-$PYSIDE_VERSION-$tag-android_$ANDROID_ARCH.whl
        if [ -s "$file" ] || curl -sSL --fail -o "$file" "$QT_DOWNLOADS/$1/$(basename "$file")" 2>/dev/null; then
            echo "$file"; return 0
        fi
        rm -f "$file"
    done
    return 1
}
WHEEL_PYSIDE=$(wheel pyside6) || fail "Android wheel pyside6 $PYSIDE_VERSION not found on $QT_DOWNLOADS"
WHEEL_SHIBOKEN=$(wheel shiboken6) || fail "Android wheel shiboken6 $PYSIDE_VERSION not found on $QT_DOWNLOADS"
echo "$(basename "$WHEEL_PYSIDE")"; echo "$(basename "$WHEEL_SHIBOKEN")"

# ---------------------------------------------------------------------------
step "5/8 Android NDK $NDK_VERSION"
# ---------------------------------------------------------------------------
# The tool cannot download the NDK itself (known bug): do it here.
if [ ! -d "$NDK_DIR" ]; then
    mkdir -p "$CACHE/android-ndk"
    curl -sSL --fail -o "$CACHE/android-ndk/ndk.zip" \
        "https://dl.google.com/android/repository/android-ndk-$NDK_VERSION-linux.zip"
    unzip -q "$CACHE/android-ndk/ndk.zip" -d "$CACHE/android-ndk"
    rm -f "$CACHE/android-ndk/ndk.zip"
fi

# ---------------------------------------------------------------------------
step "6/8 Apache Ant and Android SDK"
# ---------------------------------------------------------------------------
if [ ! -d "$ANT_DIR" ]; then
    mkdir -p "$PLATFORM"
    curl -sSL --fail -o "$PLATFORM/ant.tar.gz" \
        "https://archive.apache.org/dist/ant/binaries/apache-ant-$ANT_VERSION-bin.tar.gz"
    tar xzf "$PLATFORM/ant.tar.gz" -C "$PLATFORM"
    rm -f "$PLATFORM/ant.tar.gz"
fi
if [ ! -x "$SDK_DIR/tools/bin/sdkmanager" ]; then
    # unpacked in a temporary folder: a failed download must not
    # leave a half-installed SDK
    rm -rf "$SDK_DIR" "$SDK_DIR.tmp"
    mkdir -p "$SDK_DIR.tmp"
    curl -sSL --fail -o "$SDK_DIR.tmp/tools.zip" "https://dl.google.com/android/repository/$CMDLINE_TOOLS"
    unzip -q "$SDK_DIR.tmp/tools.zip" -d "$SDK_DIR.tmp"
    rm -f "$SDK_DIR.tmp/tools.zip"
    mv "$SDK_DIR.tmp" "$SDK_DIR"
fi
if [ ! -d "$SDK_DIR/platform-tools" ]; then
    # "yes | command" + pipefail: yes gets "Broken pipe" as soon as
    # sdkmanager has finished reading, and the pipeline then counts as failed
    # even if the installation succeeded. pipefail is turned off here: the
    # pipeline's status becomes sdkmanager's, which is what we want.
    set +o pipefail
    yes | "$SDK_DIR/tools/bin/sdkmanager" --sdk_root="$SDK_DIR" "${SDK_PROXY[@]}" --licenses >/dev/null || true
    yes | "$SDK_DIR/tools/bin/sdkmanager" --sdk_root="$SDK_DIR" "${SDK_PROXY[@]}" platform-tools >/dev/null || true
    set -o pipefail
fi
[ -d "$SDK_DIR/platform-tools" ] || fail "sdkmanager did not install platform-tools (see the messages above)"

# ---------------------------------------------------------------------------
step "7/8 Copying the application"
# ---------------------------------------------------------------------------
rm -rf "$APP"
mkdir -p "$APP/appcore"
cp "$ROOT"/*.py "$APP"/
# The base: its code, translations and recorded guitars (not its
# tools, tests, templates or build scripts)
cp "$CORE"/*.py "$APP/appcore/"
cp -r "$CORE/locales" "$CORE/sounds" "$APP/appcore/"
# The app's folders: translations, sounds, and those of EXTRA_DIRS (app_info.py)
for dir in locales sounds $APP_EXTRA_DIRS; do
    if [ -d "$ROOT/$dir" ]; then
        mkdir -p "$APP/$(dirname "$dir")"
        cp -r "$ROOT/$dir" "$APP/$dir"
    fi
done
find "$APP" -name "__pycache__" -prune -exec rm -rf {} +
find "$APP/appcore/sounds" -type f ! -name "*.snd" -delete
[ -d "$APP/sounds" ] && find "$APP/sounds" -type f ! -name "*.snd" -delete
[ -f "$ROOT/icon.png" ] && cp "$ROOT/icon.png" "$APP"/
rm -f "$APP/pysidedeploy.spec"   # an old file prevents finding the NDK
echo "$APP_NAME $APP_VERSION · package $APP_PACKAGE · permissions: $APP_PERMISSIONS"
# Java part (screen always on, exit reasons for the error
# report, file picker result passed to Qt): the base's
# templates, in the app's Java package, plus the app's own Java
# (its android/java/: in-app purchase, notifications… and its
# AppHooks.java hooks). Outside the app's folder, so it is not copied into the
# APK's Python files. The app's Java libraries (GRADLE_DEPENDENCIES)
# are added by Gradle: see the "gradle-deps" fix of patch_deploy_tools.py
rm -rf "$BUILD/java"
JAVA_DIR="$BUILD/java/$(echo "$JAVA_PACKAGE" | tr . /)"
mkdir -p "$JAVA_DIR"
if [ -d "$ROOT/android/java" ]; then
    cp -r "$ROOT/android/java/." "$BUILD/java/"
fi
for template in "$CORE"/android/java/*.java.in; do
    target="$JAVA_DIR/$(basename "$template" .in)"
    if [ -f "$target" ]; then
        echo "Java: the app's $(basename "$target") (instead of the base's template)"
        continue
    fi
    sed -e "s/@JAVA_PACKAGE@/$JAVA_PACKAGE/g" -e "s/@APP_NAME@/$APP_NAME/g" \
        -e "s/@APP_SLUG@/$APP_SLUG/g" "$template" > "$target"
done
export APPCORE_JAVA_SRC="$BUILD/java"
export APPCORE_ENTRYPOINT="$JAVA_PACKAGE.KeepAwakeActivity"
export APPCORE_PERMISSIONS="$APP_PERMISSIONS"
export APPCORE_ORIENTATION="$APP_ORIENTATION"     # portrait or landscape (app_info.ORIENTATION)
export APPCORE_GRADLE_DEPS="${APPCORE_GRADLE_DEPS-$APP_GRADLE_DEPS}"
export APPCORE_EXPECTED_PERMISSIONS="$APP_LIBRARY_PERMISSIONS"
[ -f "$APP/icon.png" ] && export APPCORE_ICON="$APP/icon.png"
# Fix called by python-for-android right before Gradle: without it, the
# Google Play version closes at start-up (see android/p4a_hook.py)
cp "$CORE/android/p4a_hook.py" "$BUILD/p4a_hook.py"
export APPCORE_P4A_HOOK="$BUILD/p4a_hook.py"
# Removes unused Qt libraries and PySide6 modules (3D, Charts, QML…):
# about 300 MB less once installed (see android/slim_bundle.py).
# APPCORE_SLIM= (empty) to keep everything.
cp "$CORE/android/slim_bundle.py" "$BUILD/slim_bundle.py"
export APPCORE_SLIM=${APPCORE_SLIM-$BUILD/slim_bundle.py}

# ---------------------------------------------------------------------------
step "8/8 Building the APK (20 to 40 min the first time)"
# ---------------------------------------------------------------------------
cd "$APP"

# Gradle downloads its libraries from Maven Central / Google. A passing network
# failure gives "Could not find …" on files that exist: give downloads
# more time and retry the build (what is already
# downloaded is reused, so later attempts are faster).
mkdir -p "$HOME/.gradle"
for prop in 'systemProp.org.gradle.internal.http.connectionTimeout=60000' \
            'systemProp.org.gradle.internal.http.socketTimeout=60000' \
            'systemProp.org.gradle.internal.repository.max.retries=6'; do
    grep -qF "$prop" "$HOME/.gradle/gradle.properties" 2>/dev/null \
        || echo "$prop" >> "$HOME/.gradle/gradle.properties"
done

built=0
for attempt in 1 2 3; do
    if PATH="$VENV/bin:$PATH" "$VENV/bin/pyside6-android-deploy" \
        --wheel-pyside "$WHEEL_PYSIDE" \
        --wheel-shiboken "$WHEEL_SHIBOKEN" \
        --ndk-path "$NDK_DIR" \
        --name "$APP_NAME" \
        --keep-deployment-files \
        -f -v; then
        built=1
        break
    fi
    [ "$attempt" -lt 3 ] || break
    printf '\n\033[1;33mBuild failed (attempt %s/3). Retrying in 30 s…\033[0m\n' "$attempt" >&2
    sleep 30
done
[ $built -eq 1 ] || fail "the build failed 3 times (see the messages above)"

mkdir -p "$DIST"
BUILT=()
for apk in "$APP"/*.apk "$APP"/bin/*.apk; do
    [ -f "$apk" ] || continue
    cp "$apk" "$DIST/"
    BUILT+=("$DIST/$(basename "$apk")")
done
[ ${#BUILT[@]} -gt 0 ] || fail "no APK produced (see the messages above)"
step "APK ready:"
ls -lh "${BUILT[@]}"
# Declared permissions (only those of ANDROID_PERMISSIONS expected)
"$PY" "$CORE/android/apk_permissions.py" "${BUILT[@]}" || true
# 16 KB pages (Android 15+, Google Play): all libraries must be
# aligned on 16 KB
"$PY" "$CORE/android/check_16k.py" "${BUILT[@]}" \
    || printf '\n\033[1;33mWarning: APK not fully 16 KB compatible (see above).\033[0m\n' >&2
# All the libraries Qt loads at start-up must be in the APK:
# otherwise the app closes right at start-up (seen with the first PySide6 6.12 version)
"$PY" "$CORE/android/check_qt_libs.py" "${BUILT[@]}" \
    || fail "the APK would close at start-up: Qt libraries missing (see above)"
