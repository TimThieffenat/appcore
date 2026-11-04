#!/usr/bin/env bash
#
# Compile l'application en APK Android (arm64) avec pyside6-android-deploy.
#
# À lancer sous Linux : Ubuntu 24.04 dans WSL2 sur Windows, ou GitHub Actions,
# depuis le dossier de l'app (celui de main.py et app_info.py) :
#
#   bash appcore/android/build_apk.sh
#
# Relançable sans risque : tout ce qui est déjà téléchargé est réutilisé.
# Tout ce qui est propre à l'app (nom, paquet, autorisations, dossiers à
# embarquer…) vient de son app_info.py (voir android/app_config.py).
#
# Versions figées (celles de l'outil de Qt, voir ANDROID.md) :
# PySide6 6.12.0 · buildozer 1.6.0 · cython 0.29.33 · NDK r28c · JDK 17
# Python 3.11 pour l'outil (sur le PC) ; Python 3.14 dans l'app (choisi par
# l'outil de Qt via python-for-android v2026.05.09).
# NDK r28c : tout ce que python-for-android compile (Python, ssl, crypto,
# sqlite, libffi, le lanceur) est aligné sur les pages de 16 Ko (Android 15+,
# exigé par Google Play) ; les bibliothèques Qt de PySide6 6.12 le sont aussi.
# android/check_16k.py le vérifie à la fin.
# PYSIDE_VERSION=6.11.2 reprend l'ancienne combinaison (buildozer 1.5.0, NDK
# r27c, Python 3.11 dans l'app), sans les pages de 16 Ko.
# Android visé : API 36 (variable APPCORE_ANDROID_API pour en changer).
# Android minimum : API 28 = Android 9, le minimum de Qt 6.8+ (APPCORE_ANDROID_MINAPI).
#
# --keep-deployment-files garde buildozer.spec et le dossier deployment/ :
# android/release_aab.sh en a besoin pour fabriquer l'AAB de Google Play.
#
set -euo pipefail

PYSIDE_VERSION=${PYSIDE_VERSION:-6.12.0}
CORE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)    # le socle (appcore/)
ROOT=${APP_ROOT:-$(cd "$CORE/.." && pwd)}                # le dossier de l'app
[ -f "$ROOT/app_info.py" ] || { echo "app_info.py introuvable dans $ROOT" >&2; exit 1; }
# Nom, paquet, autorisations… de l'app (app_info.py) ; le nom doit être un
# identifiant Java valide (c'est le nom de l'APK)
CONFIG=$(python3 "$CORE/android/app_config.py" "$ROOT") || exit 1
eval "$CONFIG"
ANDROID_ARCH=${ANDROID_ARCH:-aarch64}    # aarch64 = téléphones récents (arm64-v8a)
case "$PYSIDE_VERSION" in
    6.11.*) DEFAULT_NDK=r27c; BUILDOZER_VERSION=1.5.0 ;;
    *)      DEFAULT_NDK=r28c; BUILDOZER_VERSION=1.6.0 ;;   # versions de l'outil de Qt 6.12
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
fail() { printf '\n\033[1;31mERREUR : %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
step "1/8 Vérification des outils système"
# ---------------------------------------------------------------------------
[ "$(uname -s)" = "Linux" ] || fail "à lancer sous Linux (Ubuntu dans WSL2 sur Windows)."
PACKAGES=(autoconf automake libtool libltdl-dev pkg-config openjdk-17-jdk zip unzip ccache curl git)
# libltdl-dev fournit la macro LT_SYS_SYMBOL_USCORE, dont libffi a besoin
# (sans elle : « possibly undefined macro: LT_SYS_SYMBOL_USCORE »).
missing=()
for pkg in "${PACKAGES[@]}"; do
    dpkg -s "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
done
if [ ${#missing[@]} -gt 0 ] && [ -n "${CI:-}" ]; then
    # Sur GitHub Actions : on installe nous-mêmes ce qui manque.
    sudo apt-get update -qq
    sudo apt-get install -y "${missing[@]}"
    missing=()
fi
[ ${#missing[@]} -eq 0 ] || fail "paquets manquants. Installe-les avec :
    sudo apt-get update && sudo apt-get install -y ${missing[*]}"

export JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}
[ -x "$JAVA_HOME/bin/javac" ] || fail "JDK 17 introuvable dans $JAVA_HOME"
export PATH="$JAVA_HOME/bin:$PATH"

# Proxy éventuel : Java ne lit pas http(s)_proxy, on le donne à Gradle.
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
step "2/8 Environnement Python 3.11 (pour l'outil de compilation)"
# ---------------------------------------------------------------------------
mkdir -p "$BUILD"
# Un venv corrigé par les anciens scripts de l'app (avant le socle : étiquettes
# THECORDS-PATCH, PERFECTPITCH-PATCH…) ne peut pas recevoir les correctifs du
# socle : on le refait (rien d'autre n'est retéléchargé que les paquets Python).
if [ -d "$VENV" ] && grep -rqsE "(THECORDS|PERFECTPITCH|[A-Z]+)-PATCH" \
        "$VENV"/lib/python3.11/site-packages/PySide6/scripts/deploy_lib/android/buildozer.py \
        && ! grep -qs "APPCORE-PATCH" \
        "$VENV"/lib/python3.11/site-packages/PySide6/scripts/deploy_lib/android/buildozer.py; then
    echo "Ancien environnement de compilation (d'avant appcore) : il est refait."
    rm -rf "$VENV"
fi
if [ ! -x "$PY" ]; then
    if command -v uv >/dev/null; then
        uv venv --python 3.11 "$VENV"
    elif command -v python3.11 >/dev/null; then
        python3.11 -m venv "$VENV"
    else
        fail "Python 3.11 introuvable. Le plus simple : installer uv
    curl -LsSf https://astral.sh/uv/install.sh | sh   (puis rouvrir le terminal)"
    fi
fi
"$PY" -c 'import sys; assert sys.version_info[:2] == (3, 11)' || fail "le venv n'est pas en Python 3.11"
# buildozer fait « pip install --user » : il faut voir les paquets utilisateur.
sed -i 's/^include-system-site-packages *=.*/include-system-site-packages = true/' "$VENV/pyvenv.cfg"

install() {
    if command -v uv >/dev/null; then uv pip install --python "$PY" -q "$@"
    else "$PY" -m pip install -q "$@"; fi
}
# Versions EXACTES : sinon l'outil réinstalle buildozer et annule les correctifs.
install pip "pyside6==$PYSIDE_VERSION" "buildozer==$BUILDOZER_VERSION" "cython==$CYTHON_VERSION"
REQS=$("$PY" -c "import PySide6, pathlib; print(pathlib.Path(PySide6.__file__).parent / 'scripts' / 'requirements-android.txt')")
[ -f "$REQS" ] && install -r "$REQS"

# ---------------------------------------------------------------------------
step "3/8 Correctifs de l'outil de déploiement"
# ---------------------------------------------------------------------------
SITE=$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
"$PY" "$CORE/android/patch_deploy_tools.py" "$SITE"

# ---------------------------------------------------------------------------
step "4/8 Wheels Android de PySide6 ($ANDROID_ARCH)"
# ---------------------------------------------------------------------------
# Nom des wheels : « cp310-abi3 » depuis 6.12 (valables pour tout Python
# >= 3.10), « cp311-cp311 » avant.
wheel() {   # wheel pyside6|shiboken6 : télécharge si besoin, affiche le chemin
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
WHEEL_PYSIDE=$(wheel pyside6) || fail "wheel Android pyside6 $PYSIDE_VERSION introuvable sur $QT_DOWNLOADS"
WHEEL_SHIBOKEN=$(wheel shiboken6) || fail "wheel Android shiboken6 $PYSIDE_VERSION introuvable sur $QT_DOWNLOADS"
echo "$(basename "$WHEEL_PYSIDE")"; echo "$(basename "$WHEEL_SHIBOKEN")"

# ---------------------------------------------------------------------------
step "5/8 Android NDK $NDK_VERSION"
# ---------------------------------------------------------------------------
# L'outil ne sait pas télécharger le NDK lui-même (bug connu) : on le fait ici.
if [ ! -d "$NDK_DIR" ]; then
    mkdir -p "$CACHE/android-ndk"
    curl -sSL --fail -o "$CACHE/android-ndk/ndk.zip" \
        "https://dl.google.com/android/repository/android-ndk-$NDK_VERSION-linux.zip"
    unzip -q "$CACHE/android-ndk/ndk.zip" -d "$CACHE/android-ndk"
    rm -f "$CACHE/android-ndk/ndk.zip"
fi

# ---------------------------------------------------------------------------
step "6/8 Apache Ant et Android SDK"
# ---------------------------------------------------------------------------
if [ ! -d "$ANT_DIR" ]; then
    mkdir -p "$PLATFORM"
    curl -sSL --fail -o "$PLATFORM/ant.tar.gz" \
        "https://archive.apache.org/dist/ant/binaries/apache-ant-$ANT_VERSION-bin.tar.gz"
    tar xzf "$PLATFORM/ant.tar.gz" -C "$PLATFORM"
    rm -f "$PLATFORM/ant.tar.gz"
fi
if [ ! -x "$SDK_DIR/tools/bin/sdkmanager" ]; then
    # décompression dans un dossier temporaire : un téléchargement raté ne
    # doit pas laisser un SDK à moitié installé
    rm -rf "$SDK_DIR" "$SDK_DIR.tmp"
    mkdir -p "$SDK_DIR.tmp"
    curl -sSL --fail -o "$SDK_DIR.tmp/tools.zip" "https://dl.google.com/android/repository/$CMDLINE_TOOLS"
    unzip -q "$SDK_DIR.tmp/tools.zip" -d "$SDK_DIR.tmp"
    rm -f "$SDK_DIR.tmp/tools.zip"
    mv "$SDK_DIR.tmp" "$SDK_DIR"
fi
if [ ! -d "$SDK_DIR/platform-tools" ]; then
    # « yes | commande » + pipefail : yes reçoit « Broken pipe » dès que
    # sdkmanager a fini de lire, et le pipeline est alors compté en échec même
    # si l'installation a réussi. On coupe pipefail ici : le statut du
    # pipeline devient celui de sdkmanager, ce qui est bien ce qu'on veut.
    set +o pipefail
    yes | "$SDK_DIR/tools/bin/sdkmanager" --sdk_root="$SDK_DIR" "${SDK_PROXY[@]}" --licenses >/dev/null || true
    yes | "$SDK_DIR/tools/bin/sdkmanager" --sdk_root="$SDK_DIR" "${SDK_PROXY[@]}" platform-tools >/dev/null || true
    set -o pipefail
fi
[ -d "$SDK_DIR/platform-tools" ] || fail "sdkmanager n'a pas installé platform-tools (voir les messages ci-dessus)"

# ---------------------------------------------------------------------------
step "7/8 Copie de l'application"
# ---------------------------------------------------------------------------
rm -rf "$APP"
mkdir -p "$APP/appcore"
cp "$ROOT"/*.py "$APP"/
# Le socle : son code, ses traductions et les guitares enregistrées (pas ses
# outils, tests, modèles ni scripts de compilation)
cp "$CORE"/*.py "$APP/appcore/"
cp -r "$CORE/locales" "$CORE/sounds" "$APP/appcore/"
# Les dossiers de l'app : traductions, sons, et ceux de EXTRA_DIRS (app_info.py)
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
rm -f "$APP/pysidedeploy.spec"   # un ancien fichier empêche de trouver le NDK
echo "$APP_NAME $APP_VERSION · paquet $APP_PACKAGE · autorisations : $APP_PERMISSIONS"
# Partie Java (écran toujours allumé, causes des arrêts pour le rapport
# d'erreur, résultat du sélecteur de fichiers transmis à Qt) : modèles du
# socle, au nom du paquet Java de l'app, plus le Java de l'app elle-même
# (son android/java/ : achat dans l'app, notifications… et ses crochets
# AppHooks.java). Hors du dossier de l'app, pour ne pas la copier dans les
# fichiers Python de l'APK. Les bibliothèques Java de l'app (GRADLE_DEPENDENCIES)
# sont ajoutées par Gradle : voir le correctif « gradle-deps » de patch_deploy_tools.py
rm -rf "$BUILD/java"
JAVA_DIR="$BUILD/java/$(echo "$JAVA_PACKAGE" | tr . /)"
mkdir -p "$JAVA_DIR"
if [ -d "$ROOT/android/java" ]; then
    cp -r "$ROOT/android/java/." "$BUILD/java/"
fi
for template in "$CORE"/android/java/*.java.in; do
    target="$JAVA_DIR/$(basename "$template" .in)"
    if [ -f "$target" ]; then
        echo "Java : $(basename "$target") de l'app (à la place du modèle du socle)"
        continue
    fi
    sed -e "s/@JAVA_PACKAGE@/$JAVA_PACKAGE/g" -e "s/@APP_NAME@/$APP_NAME/g" \
        -e "s/@APP_SLUG@/$APP_SLUG/g" "$template" > "$target"
done
export APPCORE_JAVA_SRC="$BUILD/java"
export APPCORE_ENTRYPOINT="$JAVA_PACKAGE.KeepAwakeActivity"
export APPCORE_PERMISSIONS="$APP_PERMISSIONS"
export APPCORE_GRADLE_DEPS="${APPCORE_GRADLE_DEPS-$APP_GRADLE_DEPS}"
export APPCORE_EXPECTED_PERMISSIONS="$APP_LIBRARY_PERMISSIONS"
[ -f "$APP/icon.png" ] && export APPCORE_ICON="$APP/icon.png"
# Correctif appelé par python-for-android juste avant Gradle : sans lui, la
# version Google Play se ferme au démarrage (voir android/p4a_hook.py)
cp "$CORE/android/p4a_hook.py" "$BUILD/p4a_hook.py"
export APPCORE_P4A_HOOK="$BUILD/p4a_hook.py"
# Retire les bibliothèques Qt et modules PySide6 inutilisés (3D, Charts, QML…) :
# environ 300 Mo de moins une fois installée (voir android/slim_bundle.py).
# APPCORE_SLIM= (vide) pour tout garder.
cp "$CORE/android/slim_bundle.py" "$BUILD/slim_bundle.py"
export APPCORE_SLIM=${APPCORE_SLIM-$BUILD/slim_bundle.py}

# ---------------------------------------------------------------------------
step "8/8 Compilation de l'APK (20 à 40 min la première fois)"
# ---------------------------------------------------------------------------
cd "$APP"

# Gradle télécharge ses bibliothèques sur Maven Central / Google. Un raté réseau
# passager donne « Could not find … » sur des fichiers qui existent : on laisse
# plus de temps aux téléchargements et on retente la compilation (ce qui est
# déjà téléchargé est réutilisé, donc les essais suivants sont plus rapides).
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
    printf '\n\033[1;33mCompilation échouée (essai %s/3). Nouvel essai dans 30 s…\033[0m\n' "$attempt" >&2
    sleep 30
done
[ $built -eq 1 ] || fail "la compilation a échoué 3 fois (voir les messages ci-dessus)"

mkdir -p "$DIST"
BUILT=()
for apk in "$APP"/*.apk "$APP"/bin/*.apk; do
    [ -f "$apk" ] || continue
    cp "$apk" "$DIST/"
    BUILT+=("$DIST/$(basename "$apk")")
done
[ ${#BUILT[@]} -gt 0 ] || fail "aucun APK produit (voir les messages ci-dessus)"
step "APK prêt :"
ls -lh "${BUILT[@]}"
# Autorisations déclarées (seulement celles de ANDROID_PERMISSIONS attendues)
"$PY" "$CORE/android/apk_permissions.py" "${BUILT[@]}" || true
# Pages de 16 Ko (Android 15+, Google Play) : toutes les bibliothèques doivent
# être alignées sur 16 Ko
"$PY" "$CORE/android/check_16k.py" "${BUILT[@]}" \
    || printf '\n\033[1;33mAttention : APK pas entièrement compatible 16 Ko (voir ci-dessus).\033[0m\n' >&2
# Toutes les bibliothèques que Qt charge au démarrage doivent être dans l'APK :
# sinon l'app se ferme dès son lancement (vu avec la 1re version PySide6 6.12)
"$PY" "$CORE/android/check_qt_libs.py" "${BUILT[@]}" \
    || fail "l'APK se fermerait au démarrage : bibliothèques de Qt manquantes (voir ci-dessus)"
