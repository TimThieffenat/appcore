#!/usr/bin/env bash
# Crée la clé de signature d'envoi (une seule fois). SAUVEGARDE-LA (2 copies).
# Avec Play App Signing, Google garde la vraie clé : si celle-ci est perdue,
# on peut demander une réinitialisation, mais c'est long. Ne la mets PAS sur GitHub.
# Nom du fichier et alias : KEYSTORE_NAME et KEY_ALIAS de app_info.py.
#
#   bash appcore/android/make_keystore.sh      (depuis le dossier de l'app)
set -euo pipefail
CORE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ROOT=${APP_ROOT:-$(cd "$CORE/.." && pwd)}
CONFIG=$(python3 "$CORE/android/app_config.py" "$ROOT") || exit 1
eval "$CONFIG"
KEYSTORE=${KEYSTORE:-$HOME/$APP_KEYSTORE_NAME}
[ -f "$KEYSTORE" ] && { echo "Existe déjà : $KEYSTORE"; exit 1; }
keytool -genkeypair -v -keystore "$KEYSTORE" -alias "$APP_KEY_ALIAS" \
    -keyalg RSA -keysize 2048 -validity 10000
echo "Clé créée : $KEYSTORE (alias $APP_KEY_ALIAS)"
