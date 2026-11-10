#!/usr/bin/env bash
# Creates the upload signing key (only once). BACK IT UP (2 copies).
# With Play App Signing, Google keeps the real key: if this one is lost,
# a reset can be requested, but it takes time. Do NOT put it on GitHub.
# File name and alias: KEYSTORE_NAME and KEY_ALIAS of app_info.py.
#
#   bash appcore/android/make_keystore.sh      (from the app's folder)
set -euo pipefail
CORE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ROOT=${APP_ROOT:-$(cd "$CORE/.." && pwd)}
CONFIG=$(python3 "$CORE/android/app_config.py" "$ROOT") || exit 1
eval "$CONFIG"
KEYSTORE=${KEYSTORE:-$HOME/$APP_KEYSTORE_NAME}
[ -f "$KEYSTORE" ] && { echo "Already exists: $KEYSTORE"; exit 1; }
keytool -genkeypair -v -keystore "$KEYSTORE" -alias "$APP_KEY_ALIAS" \
    -keyalg RSA -keysize 2048 -validity 10000
echo "Key created: $KEYSTORE (alias $APP_KEY_ALIAS)"
