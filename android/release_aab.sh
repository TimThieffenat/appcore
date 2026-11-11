#!/usr/bin/env bash
#
# Makes the signed AAB for Google Play (package ANDROID_PACKAGE of app_info.py,
# for example com.rifffinder.app).
#
# Prerequisite: having run  bash appcore/android/build_apk.sh  at least once
# (it prepares the venv, the SDK, the NDK and the buildozer.spec file).
#
#   bash appcore/android/release_aab.sh                # builds the AAB
#   VERSION_CODE=2 bash appcore/android/release_aab.sh # for each new upload to Play
#
# Signing: create the key ONCE with  bash appcore/android/make_keystore.sh
# then keep ~/<KEYSTORE_NAME> + its password somewhere safe (2 copies).
#
set -euo pipefail

CORE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)    # the base (appcore/)
ROOT=${APP_ROOT:-$(cd "$CORE/.." && pwd)}                # the app's folder
CONFIG=$(python3 "$CORE/android/app_config.py" "$ROOT") || exit 1
eval "$CONFIG"
BUILD=${BUILD_DIR:-$ROOT/build/android}
APP=$BUILD/app
VENV=$BUILD/venv
DIST=$ROOT/dist

# PACKAGE_DOMAIN + PACKAGE_NAME = ANDROID_PACKAGE (final once published)
VERSION_CODE=${VERSION_CODE:-1}       # integer, to increase for EACH upload to Play
VERSION_NAME=$APP_VERSION
APP_LABEL=$APP_NAME
KEYSTORE=${KEYSTORE:-$HOME/$APP_KEYSTORE_NAME}
KEY_ALIAS=${KEY_ALIAS:-$APP_KEY_ALIAS}

fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[ -d "$APP" ] || fail "run first: bash appcore/android/build_apk.sh"
[ -f "$KEYSTORE" ] || fail "key not found ($KEYSTORE). Create it with: bash appcore/android/make_keystore.sh"
export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}
export PATH="$JAVA_HOME/bin:$VENV/bin:$PATH"

# Password: KEYSTORE_PASSWORD variable (GitHub Actions), else asked
PW=${KEYSTORE_PASSWORD:-}
if [ -z "$PW" ]; then
    read -r -s -p "Key password: " PW; echo
fi
export P4A_RELEASE_KEYSTORE=$KEYSTORE
export P4A_RELEASE_KEYALIAS=$KEY_ALIAS
export P4A_RELEASE_KEYSTORE_PASSWD=$PW
export P4A_RELEASE_KEYALIAS_PASSWD=$PW

cd "$APP"
SPEC=$(find . -maxdepth 2 -name buildozer.spec | head -1)
[ -n "$SPEC" ] || fail "buildozer.spec not found in $APP (run appcore/android/build_apk.sh to the end once)"
echo "Spec: $SPEC"
cp "$SPEC" "$SPEC.bak"

set_spec() {   # set_spec key value: replaces the line or adds it in [app]
    if grep -qE "^[#[:space:]]*$1[[:space:]]*=" "$SPEC"; then
        sed -i -E "s|^[#[:space:]]*$1[[:space:]]*=.*|$1 = $2|" "$SPEC"
    else
        sed -i "0,/^\[app\]/s||[app]\n$1 = $2|" "$SPEC"
    fi
}
set_spec package.domain "$PACKAGE_DOMAIN"
set_spec package.name "$PACKAGE_NAME"
set_spec version "$VERSION_NAME"
set_spec android.numeric_version "$VERSION_CODE"
set_spec android.release_artifact aab
set_spec android.archs arm64-v8a
set_spec android.api "${APPCORE_ANDROID_API:-36}"   # Google Play: API 36 required since late August 2026
# minSdk: Google Play requires at least 24 (Play automatic protection) and Qt 6.8+
# only works from Android 9 (API 28). Same value as build_apk.sh
# (min-api patch), to reuse what is already built.
set_spec android.minapi "${APPCORE_ANDROID_MINAPI:-28}"
set_spec android.accept_sdk_license True
# Essential for the Google Play version: without this fix, Qt does not find
# the PySide6 modules and the app closes after its logo (android/p4a_hook.py)
cp "$CORE/android/p4a_hook.py" "$BUILD/p4a_hook.py"
set_spec p4a.hook "$BUILD/p4a_hook.py"
# Slimmed app (unused Qt libraries removed): the PySide6 recipe,
# run again for the AAB, calls android/slim_bundle.py as in build_apk.sh
cp "$CORE/android/slim_bundle.py" "$BUILD/slim_bundle.py"
export APPCORE_SLIM=${APPCORE_SLIM-$BUILD/slim_bundle.py}
grep -E "^(package\.|version|p4a\.hook|android\.(numeric_version|release_artifact|archs|api|minapi|ndk_api|permissions))" "$SPEC" || true

# buildozer's working folder is the spec's
cd "$(dirname "$SPEC")"
# build_apk.sh moved the build folder into deployment/: put it
# back in place to reuse what is already built
if [ ! -d .buildozer ] && [ -d deployment/.buildozer ]; then
    mv deployment/.buildozer .buildozer
fi
"$VENV/bin/buildozer" -v android release

mkdir -p "$DIST"
found=0
for f in bin/*.aab ./*.aab; do
    [ -f "$f" ] || continue
    cp "$f" "$DIST/$APP_LABEL-$VERSION_NAME-$VERSION_CODE.aab"; found=1
done
[ $found -eq 1 ] || fail "no .aab produced (see the messages above)"
ls -lh "$DIST"/*.aab
# 16 KB pages: Google Play refuses libraries aligned on 4 KB
"$VENV/bin/python" "$CORE/android/check_16k.py" "$DIST/$APP_LABEL-$VERSION_NAME-$VERSION_CODE.aab" \
    || printf '\n\033[1;33mWarning: AAB not fully 16 KB compatible (see above).\033[0m\n' >&2
# Libraries loaded by Qt at start-up: all present, otherwise the app closes
"$VENV/bin/python" "$CORE/android/check_qt_libs.py" "$DIST/$APP_LABEL-$VERSION_NAME-$VERSION_CODE.aab" \
    || fail "the AAB would close at start-up: Qt libraries missing (see above)"
echo "Upload this file to the Play Console (Closed testing > Create a release)."
