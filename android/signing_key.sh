#!/usr/bin/env bash
#
# Signing key of the test APK: ALWAYS THE SAME, so that Android agrees
# to install a new version over the old one (otherwise: "app
# not installed" and you must uninstall, which erases the user's data).
#
# Gradle signs the test APK with ~/.android/debug.keystore. On GitHub, each
# build started from a fresh machine, hence a new key. This script:
#   1. if the KEYSTORE_B64 and KEYSTORE_PASSWORD secrets exist (those of the
#      Google Play upload key), copies that key under the name Gradle expects;
#   2. otherwise, keeps the test key already there (restored from the GitHub cache) or
#      creates one, which the workflow caches.
# Writes "kind=upload" or "kind=debug" to $GITHUB_OUTPUT (if set).
#
set -euo pipefail

CORE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)    # the base (appcore/)
ROOT=${APP_ROOT:-$(cd "$CORE/.." && pwd)}                # the app's folder
DEST_DIR=${ANDROID_USER_HOME:-$HOME/.android}
DEST=$DEST_DIR/debug.keystore
# key alias: KEY_ALIAS of app_info.py (by default the app's name in lower case)
ALIAS=${KEY_ALIAS:-$(python3 "$CORE/android/app_config.py" "$ROOT" --get APP_KEY_ALIAS)}
mkdir -p "$DEST_DIR"

output() { [ -n "${GITHUB_OUTPUT:-}" ] && echo "kind=$1" >> "$GITHUB_OUTPUT"; return 0; }

if [ -n "${KEYSTORE_B64:-}" ] && [ -n "${KEYSTORE_PASSWORD:-}" ]; then
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    printf '%s' "$KEYSTORE_B64" | base64 -d > "$TMP/upload.jks"
    rm -f "$TMP/debug.keystore"
    if keytool -importkeystore -noprompt \
            -srckeystore "$TMP/upload.jks" -srcstorepass "$KEYSTORE_PASSWORD" \
            -srcalias "$ALIAS" -srckeypass "$KEYSTORE_PASSWORD" \
            -destkeystore "$TMP/debug.keystore" -deststoretype PKCS12 \
            -deststorepass android -destkeypass android -destalias androiddebugkey \
            >/dev/null 2>&1; then
        cp "$TMP/debug.keystore" "$DEST"
        echo "Signing: upload key (KEYSTORE_B64 secret), the same for every build."
        keytool -list -keystore "$DEST" -storepass android 2>/dev/null | grep -i "SHA-256\|SHA256" || true
        output upload
        exit 0
    fi
    echo "::warning::KEYSTORE_B64 / KEYSTORE_PASSWORD do not open (password? alias '$ALIAS'?): test key instead."
fi

if [ -f "$DEST" ]; then
    echo "Signing: existing test key ($DEST)."
else
    keytool -genkeypair -noprompt -keystore "$DEST" -storetype PKCS12 \
        -storepass android -keypass android -alias androiddebugkey \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -dname "CN=Android Debug, O=Android, C=US" >/dev/null
    echo "Signing: new test key created ($DEST)."
fi
keytool -list -keystore "$DEST" -storepass android 2>/dev/null | grep -i "SHA-256\|SHA256" || true
output debug
