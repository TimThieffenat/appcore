#!/usr/bin/env bash
#
# Fabrique l'AAB signé pour Google Play (paquet ANDROID_PACKAGE de app_info.py,
# par exemple com.rifffinder.app).
#
# Pré-requis : avoir lancé  bash appcore/android/build_apk.sh  au moins une fois
# (il prépare le venv, le SDK, le NDK et le fichier buildozer.spec).
#
#   bash appcore/android/release_aab.sh                # construit l'AAB
#   VERSION_CODE=2 bash appcore/android/release_aab.sh # à chaque nouvel envoi sur Play
#
# Signature : crée la clé UNE fois avec  bash appcore/android/make_keystore.sh
# puis garde ~/<KEYSTORE_NAME> + son mot de passe en lieu sûr (2 copies).
#
set -euo pipefail

CORE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)    # le socle (appcore/)
ROOT=${APP_ROOT:-$(cd "$CORE/.." && pwd)}                # le dossier de l'app
CONFIG=$(python3 "$CORE/android/app_config.py" "$ROOT") || exit 1
eval "$CONFIG"
BUILD=${BUILD_DIR:-$ROOT/build/android}
APP=$BUILD/app
VENV=$BUILD/venv
DIST=$ROOT/dist

# PACKAGE_DOMAIN + PACKAGE_NAME = ANDROID_PACKAGE (définitif après publication)
VERSION_CODE=${VERSION_CODE:-1}       # entier, à augmenter à CHAQUE envoi sur Play
VERSION_NAME=$APP_VERSION
APP_LABEL=$APP_NAME
KEYSTORE=${KEYSTORE:-$HOME/$APP_KEYSTORE_NAME}
KEY_ALIAS=${KEY_ALIAS:-$APP_KEY_ALIAS}

fail() { printf '\n\033[1;31mERREUR : %s\033[0m\n' "$*" >&2; exit 1; }

[ -d "$APP" ] || fail "lance d'abord : bash appcore/android/build_apk.sh"
[ -f "$KEYSTORE" ] || fail "clé introuvable ($KEYSTORE). Crée-la avec : bash appcore/android/make_keystore.sh"
export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}
export PATH="$JAVA_HOME/bin:$VENV/bin:$PATH"

# Mot de passe : variable KEYSTORE_PASSWORD (GitHub Actions), sinon demandé
PW=${KEYSTORE_PASSWORD:-}
if [ -z "$PW" ]; then
    read -r -s -p "Mot de passe de la clé : " PW; echo
fi
export P4A_RELEASE_KEYSTORE=$KEYSTORE
export P4A_RELEASE_KEYALIAS=$KEY_ALIAS
export P4A_RELEASE_KEYSTORE_PASSWD=$PW
export P4A_RELEASE_KEYALIAS_PASSWD=$PW

cd "$APP"
SPEC=$(find . -maxdepth 2 -name buildozer.spec | head -1)
[ -n "$SPEC" ] || fail "buildozer.spec introuvable dans $APP (lance appcore/android/build_apk.sh jusqu'au bout une fois)"
echo "Spec : $SPEC"
cp "$SPEC" "$SPEC.bak"

set_spec() {   # set_spec clé valeur : remplace la ligne ou l'ajoute dans [app]
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
set_spec android.api "${APPCORE_ANDROID_API:-36}"   # Google Play : API 36 exigée depuis fin août 2026
# minSdk : Google Play exige au moins 24 (protection automatique Play) et Qt 6.8+
# ne fonctionne qu'à partir d'Android 9 (API 28). Même valeur que build_apk.sh
# (patch min-api), pour réutiliser ce qui est déjà compilé.
set_spec android.minapi "${APPCORE_ANDROID_MINAPI:-28}"
set_spec android.accept_sdk_license True
# Indispensable pour la version Google Play : sans ce correctif, Qt ne trouve
# pas les modules PySide6 et l'app se ferme après son logo (android/p4a_hook.py)
cp "$CORE/android/p4a_hook.py" "$BUILD/p4a_hook.py"
set_spec p4a.hook "$BUILD/p4a_hook.py"
# App allégée (bibliothèques Qt inutilisées retirées) : la recette PySide6,
# rejouée pour l'AAB, appelle android/slim_bundle.py comme dans build_apk.sh
cp "$CORE/android/slim_bundle.py" "$BUILD/slim_bundle.py"
export APPCORE_SLIM=${APPCORE_SLIM-$BUILD/slim_bundle.py}
grep -E "^(package\.|version|p4a\.hook|android\.(numeric_version|release_artifact|archs|api|minapi|ndk_api|permissions))" "$SPEC" || true

# Le dossier de travail de buildozer est celui du spec
cd "$(dirname "$SPEC")"
# build_apk.sh a rangé le dossier de compilation dans deployment/ : on le
# remet en place pour réutiliser ce qui est déjà compilé
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
[ $found -eq 1 ] || fail "aucun .aab produit (voir les messages ci-dessus)"
ls -lh "$DIST"/*.aab
# Pages de 16 Ko : Google Play refuse les bibliothèques alignées sur 4 Ko
"$VENV/bin/python" "$CORE/android/check_16k.py" "$DIST/$APP_LABEL-$VERSION_NAME-$VERSION_CODE.aab" \
    || printf '\n\033[1;33mAttention : AAB pas entièrement compatible 16 Ko (voir ci-dessus).\033[0m\n' >&2
# Bibliothèques chargées par Qt au démarrage : toutes présentes, sinon l'app se ferme
"$VENV/bin/python" "$CORE/android/check_qt_libs.py" "$DIST/$APP_LABEL-$VERSION_NAME-$VERSION_CODE.aab" \
    || fail "l'AAB se fermerait au démarrage : bibliothèques de Qt manquantes (voir ci-dessus)"
echo "Envoie ce fichier dans la Play Console (Test fermé > Créer une release)."
