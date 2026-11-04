"""Corrige l'outil de déploiement Android de PySide6 et buildozer (dans le venv).

pyside6-android-deploy est encore un « aperçu technique ». Ces correctifs
ajoutent les réglages de l'app (paysage, plein écran, icône, autorisations,
versions d'Android, app allégée) et contournent des défauts de l'outil.
Prévu pour PySide6 6.12 (buildozer 1.6.0, NDK r28c, Python 3.14 sur le
téléphone) ; fonctionne encore avec 6.11.2 (buildozer 1.5.0, NDK r27c,
Python 3.11), d'où quelques correctifs « optionnels » propres à l'une ou
l'autre version.

Usage : python patch_deploy_tools.py <site-packages du venv>
Sans effet si déjà appliqués. Ne modifie que le venv de compilation.

Les réglages propres à l'app (autorisations, activité Java, icône…) ne sont
pas écrits dans l'outil : il les lit au moment de compiler dans les variables
APPCORE_* que build_apk.sh prépare d'après app_info.py. Un même venv sert donc
à toutes les apps.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

TAG = "APPCORE-PATCH"

# PySide6 6.11 seulement : dernier commit de python-for-android (branche
# develop) dont la recette python3 est encore en 3.11, car les wheels Android
# de PySide6 6.11 sont cp311. PySide6 6.12 fixe lui-même son commit
# (v2026.05.09, Python 3.14) et ses wheels « abi3 » marchent avec ce Python.
P4A_COMMIT = "3762c88c56e3443efb8eba2a02a2604b680240fd"


def _write(path: Path, text: str) -> None:
    """Réécrit via un fichier temporaire + renommage : un nouveau fichier est
    créé, ce qui évite de modifier un cache partagé par lien physique (uv)."""
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False,
                                     prefix=path.name, suffix=".tmp") as tmp:
        tmp.write(text)
    shutil.copymode(path, tmp.name)
    os.replace(tmp.name, path)


def patch(path: Path, anchor: str, replacement: str, name: str,
          required: bool = True) -> None:
    text = path.read_text()
    if f"{TAG}: {name}" in text:
        print(f"  = {name} (déjà appliqué)")
        return
    if text.count(anchor) != 1:
        message = f"  ! {name} : texte de référence introuvable dans {path}"
        if required:
            raise SystemExit(message + "\n    La version de l'outil a changé : vérifier ce correctif.")
        print(message + " (optionnel, ignoré)")
        return
    _write(path, text.replace(anchor, replacement))
    print(f"  + {name}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    site = Path(sys.argv[1]).resolve()
    buildozer_cfg = site / "PySide6/scripts/deploy_lib/android/buildozer.py"
    if not buildozer_cfg.exists():
        raise SystemExit(f"Introuvable : {buildozer_cfg} (PySide6 est-il installé dans ce venv ?)")
    print(f"Correctifs dans {site}")

    # 1) Python 3.11 : sinon l'APK se compile mais plante au démarrage
    #    (libpython3.11.so introuvable pour shiboken6).
    patch(buildozer_cfg,
          '        self.set_value("app", "p4a.branch", "develop")',
          '        self.set_value("app", "p4a.branch", "develop")\n'
          f'        # {TAG}: p4a-python311\n'
          f'        self.set_value("app", "p4a.commit", "{P4A_COMMIT}")',
          "p4a-python311", required=False)   # 6.11 seulement

    # 2) Paysage (dans les deux sens sur téléphone) et plein écran.
    patch(buildozer_cfg,
          '        self.set_value("app", "p4a.bootstrap", "qt")',
          '        self.set_value("app", "p4a.bootstrap", "qt")\n'
          f'        # {TAG}: landscape\n'
          '        self.set_value("app", "orientation", "landscape")\n'
          '        self.set_value("app", "android.manifest.orientation", "sensorLandscape")\n'
          '        self.set_value("app", "fullscreen", "1")',
          "landscape")

    # 2b bis) Seulement les autorisations dont l'app se sert. L'outil recopie
    #     celles que déclarent tous les modules Qt embarqués, même inutilisés :
    #     CAMERA et BLUETOOTH (greffon multimédia FFmpeg), INTERNET et
    #     ACCESS_NETWORK_STATE (Qt Network), WRITE_EXTERNAL_STORAGE (Qt Core).
    #     Les apps n'ont ni caméra, ni Bluetooth, ni réseau (le rapport d'erreur
    #     part par l'app d'e-mail du téléphone), et leurs fichiers passent par le
    #     sélecteur d'Android, qui ne demande aucune autorisation. Restent celles
    #     de ANDROID_PERMISSIONS (app_info.py), que build_apk.sh met dans
    #     APPCORE_PERMISSIONS : MODIFY_AUDIO_SETTINGS (Qt Multimedia s'en sert
    #     pour régler la sortie du son et le micro ; autorisation « normale »,
    #     qu'Android accorde sans rien demander), RECORD_AUDIO pour un micro…
    #     build_apk.sh affiche à la fin les autorisations de l'APK produit.
    patch(buildozer_cfg,
          '        self.set_value("app", "android.permissions", permissions)',
          f'        # {TAG}: permissions\n'
          '        import os as _os5\n'
          '        permissions = _os5.environ.get("APPCORE_PERMISSIONS",\n'
          '                                       "android.permission.MODIFY_AUDIO_SETTINGS")\n'
          '        self.set_value("app", "android.permissions", permissions)',
          "permissions")

    # 2c) Version d'Android visée (targetSdk). Sans ce réglage, buildozer vise
    #     Android 12 (API 31) : le téléphone prévient que l'app est « conçue pour
    #     une ancienne version d'Android », et Google Play exige l'API 36 depuis
    #     fin août 2026. Variable APPCORE_ANDROID_API pour en choisir une autre.
    #     Placé après les réglages de l'outil : PySide6 6.12 fixe lui-même
    #     api = 35 et minapi = ndk_api = 28, qu'il faut remplacer.
    patch(buildozer_cfg,
          '        self.set_value("app", "p4a.bootstrap", "qt")',
          '        self.set_value("app", "p4a.bootstrap", "qt")\n'
          f'        # {TAG}: target-api\n'
          '        import os as _os\n'
          '        self.set_value("app", "android.api", _os.environ.get("APPCORE_ANDROID_API", "36"))\n'
          '        self.set_value("app", "android.accept_sdk_license", "True")',
          "target-api")

    # 2c bis) Version d'Android minimale (minSdk). buildozer met 21 par défaut,
    #     ce que Google Play refuse (« La protection automatique Play nécessite
    #     le SDK 24 ou version ultérieure »). Et Qt 6.8+ (donc PySide6 6.11) ne
    #     fonctionne qu'à partir d'Android 9 (API 28) : avec 21, l'app
    #     s'installait sur Android 5 à 8 puis plantait au démarrage. Les
    #     bibliothèques natives sont compilées pour cette même version (buildozer
    #     aligne android.ndk_api sur android.minapi). Variable APPCORE_ANDROID_MINAPI.
    patch(buildozer_cfg,
          '        self.set_value("app", "p4a.bootstrap", "qt")',
          '        self.set_value("app", "p4a.bootstrap", "qt")\n'
          f'        # {TAG}: min-api\n'
          '        import os as _os3\n'
          '        _minapi = _os3.environ.get("APPCORE_ANDROID_MINAPI", "28")\n'
          '        self.set_value("app", "android.minapi", _minapi, raise_warning=False)\n'
          '        self.set_value("app", "android.ndk_api", _minapi, raise_warning=False)',
          "min-api")

    # 2d) Sons enregistrés (dossier sounds/, fichiers .snd) : buildozer ne copie
    #     dans l'APK que les extensions listées.
    patch(buildozer_cfg,
          '        include_exts = f"{include_exts},qml,js"',
          f'        # {TAG}: sound-files\n'
          '        include_exts = f"{include_exts},qml,js,snd"',
          "sound-files")

    # 2e) Écran toujours allumé tant que l'app est affichée : l'activité
    #     principale devient KeepAwakeActivity (appcore/android/java/, celle de
    #     python-for-android + FLAG_KEEP_SCREEN_ON), dans le paquet Java de l'app.
    #     build_apk.sh fournit le dossier des sources Java dans APPCORE_JAVA_SRC
    #     et le nom complet de l'activité dans APPCORE_ENTRYPOINT.
    patch(buildozer_cfg,
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)',
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)\n'
          f'        # {TAG}: keep-screen-on\n'
          '        import os as _os2\n'
          '        if _os2.environ.get("APPCORE_JAVA_SRC"):\n'
          '            self.set_value("app", "android.add_src", _os2.environ["APPCORE_JAVA_SRC"])\n'
          '            self.set_value("app", "android.entrypoint", _os2.environ["APPCORE_ENTRYPOINT"])',
          "keep-screen-on")

    # 2e bis) Bibliothèques Java du Java de l'app (achat dans l'app avec Google
    #     Play Billing, rappels avec WorkManager…) : GRADLE_DEPENDENCIES de
    #     app_info.py, que build_apk.sh met dans APPCORE_GRADLE_DEPS (séparées par
    #     des virgules). Elles demandent AndroidX. Les autorisations que ces
    #     bibliothèques ajoutent (BILLING, WAKE_LOCK…) sont attendues par
    #     apk_permissions.py (LIBRARY_PERMISSIONS de app_info.py).
    patch(buildozer_cfg,
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)',
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)\n'
          f'        # {TAG}: gradle-deps\n'
          '        import os as _os6\n'
          '        _deps = _os6.environ.get("APPCORE_GRADLE_DEPS", "")\n'
          '        if _deps and _os6.environ.get("APPCORE_JAVA_SRC"):\n'
          '            self.set_value("app", "android.gradle_dependencies", _deps)\n'
          '            self.set_value("app", "android.enable_androidx", "True")',
          "gradle-deps")

    # 2f) Modules PySide6 introuvables dans la version Google Play : le fichier
    #     android/p4a_hook.py leur ajoute le préfixe « lib » juste avant la
    #     compilation Gradle (explications dans ce fichier). build_apk.sh
    #     fournit son chemin dans APPCORE_P4A_HOOK.
    patch(buildozer_cfg,
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)',
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)\n'
          f'        # {TAG}: lib-prefix-hook\n'
          '        import os as _os4\n'
          '        if _os4.environ.get("APPCORE_P4A_HOOK"):\n'
          '            self.set_value("app", "p4a.hook", _os4.environ["APPCORE_P4A_HOOK"])',
          "lib-prefix-hook")

    # 3) Icône de l'application (variable APPCORE_ICON fournie par build_apk.sh).
    patch(buildozer_cfg,
          '        self.set_value("app", "icon.filename", pysidedeploy_config.icon)',
          f'        # {TAG}: icon\n'
          '        import os as _os\n'
          '        self.set_value("app", "icon.filename",\n'
          '                       _os.environ.get("APPCORE_ICON") or pysidedeploy_config.icon)',
          "icon", required=False)

    # 3b) App plus légère : la recette PySide6 copie toute la roue (Qt 3D,
    #     Charts, QML, WebView… et une 2e copie de chaque bibliothèque Qt dans
    #     le paquet Python, décompressé au premier lancement). Juste après ces
    #     copies, android/slim_bundle.py retire ce que l'app ne charge pas.
    #     build_apk.sh fournit son chemin dans APPCORE_SLIM ; sans cette
    #     variable, rien ne change.
    patch(site / "PySide6/scripts/deploy_lib/android/recipes/PySide6/__init__.tmpl.py",
          "\n\nrecipe = PySideRecipe()",
          f"\n        # {TAG}: slim\n"
          "        import os as _os_slim\n"
          "        if _os_slim.environ.get(\"APPCORE_SLIM\"):\n"
          "            import runpy\n"
          "            info(\"Removing unused Qt libraries and modules\")\n"
          "            runpy.run_path(_os_slim.environ[\"APPCORE_SLIM\"])[\"slim\"](\n"
          "                Path(self.ctx.get_python_install_dir(arch.arch)),\n"
          "                Path(self.ctx.get_libs_dir(arch.arch)),\n"
          "                [{% for module in qt_modules %}\"{{ module }}\", {% endfor %}],\n"
          "                local_libs=[{% for lib in qt_local_libs %}\"{{ lib }}\", {% endfor %}],\n"
          "                plugins=[{% for c, n in qt_plugins %}\"plugins_{{ c }}_{{ n }}\", "
          "{% endfor %}],\n"
          "                arch=arch.arch, log=info)\n"
          "\n\nrecipe = PySideRecipe()",
          "slim")

    # 4) buildozer télécharge Ant et les outils SDK avec urllib, qui échoue
    #    (« read of closed file ») : on passe par curl.
    patch(site / "buildozer/__init__.py",
          "        self.debug('Downloading {0}'.format(url))\n"
          "        urlretrieve(url, filename, report_hook)\n"
          "        return filename",
          "        self.debug('Downloading {0}'.format(url))\n"
          f"        # {TAG}: curl-download\n"
          "        import subprocess\n"
          "        subprocess.check_call(['curl', '-sSL', '--retry', '3', '--fail',\n"
          "                               '-o', filename, url])\n"
          "        return filename",
          "curl-download", required=False)   # buildozer 1.5.0 seulement

    # 5) Java ignore http(s)_proxy : on transmet le proxy à sdkmanager s'il y en a un.
    #    (buildozer 1.6.0 le fait lui-même : rien à faire dans ce cas.)
    android_target = site / "buildozer/targets/android.py"
    if "--proxy_host=" in android_target.read_text() and \
            f"{TAG}: sdkmanager-proxy" not in android_target.read_text():
        print("  = sdkmanager-proxy (déjà fait par buildozer)")
    else:
        patch(android_target,
              '        command = [self.sdkmanager_path, f"--sdk_root={android_sdk_dir}", *args]',
              '        command = [self.sdkmanager_path, f"--sdk_root={android_sdk_dir}", *args]\n'
              f'        # {TAG}: sdkmanager-proxy\n'
              '        import os as _os\n'
              '        from urllib.parse import urlparse as _parse\n'
              '        _proxy = _os.environ.get("https_proxy") or _os.environ.get("http_proxy")\n'
              '        if _proxy:\n'
              '            _url = _parse(_proxy)\n'
              '            command += ["--proxy=http", f"--proxy_host={_url.hostname}",\n'
              '                        f"--proxy_port={_url.port or 80}"]',
              "sdkmanager-proxy", required=False)
    print("Terminé.")


if __name__ == "__main__":
    main()
