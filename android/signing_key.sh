#!/usr/bin/env bash
#
# Clé de signature de l'APK de test : TOUJOURS LA MÊME, pour qu'Android accepte
# d'installer une nouvelle version par-dessus l'ancienne (sinon : « application
# non installée » et il faut désinstaller, ce qui efface les morceaux).
#
# Gradle signe l'APK de test avec ~/.android/debug.keystore. Sur GitHub, chaque
# compilation partait d'une machine neuve, donc d'une nouvelle clé. Ce script :
#   1. si les secrets KEYSTORE_B64 et KEYSTORE_PASSWORD existent (ceux de la clé
#      d'envoi Google Play), copie cette clé sous le nom attendu par Gradle ;
#   2. sinon, garde la clé de test déjà présente (restaurée du cache GitHub) ou
#      en crée une, que le workflow met en cache.
# Écrit « kind=upload » ou « kind=debug » dans $GITHUB_OUTPUT (si défini).
#
set -euo pipefail

CORE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)    # le socle (appcore/)
ROOT=${APP_ROOT:-$(cd "$CORE/.." && pwd)}                # le dossier de l'app
DEST_DIR=${ANDROID_USER_HOME:-$HOME/.android}
DEST=$DEST_DIR/debug.keystore
# alias de la clé : KEY_ALIAS de app_info.py (par défaut le nom de l'app en minuscules)
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
        echo "Signature : clé d'envoi (secret KEYSTORE_B64), la même à chaque compilation."
        keytool -list -keystore "$DEST" -storepass android 2>/dev/null | grep -i "SHA-256\|SHA256" || true
        output upload
        exit 0
    fi
    echo "::warning::KEYSTORE_B64 / KEYSTORE_PASSWORD ne s'ouvrent pas (mot de passe ? alias '$ALIAS' ?) : clé de test à la place."
fi

if [ -f "$DEST" ]; then
    echo "Signature : clé de test existante ($DEST)."
else
    keytool -genkeypair -noprompt -keystore "$DEST" -storetype PKCS12 \
        -storepass android -keypass android -alias androiddebugkey \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -dname "CN=Android Debug, O=Android, C=US" >/dev/null
    echo "Signature : nouvelle clé de test créée ($DEST)."
fi
keytool -list -keystore "$DEST" -storepass android 2>/dev/null | grep -i "SHA-256\|SHA256" || true
output debug
