"""Fixes PySide6's Android deployment tool and buildozer (in the venv).

pyside6-android-deploy is still a "technical preview". These fixes
add the app's settings (landscape, full screen, icon, permissions,
Android versions, slimmed app) and work around defects of the tool.
Made for PySide6 6.12 (buildozer 1.6.0, NDK r28c, Python 3.14 on the
phone); still works with 6.11.2 (buildozer 1.5.0, NDK r27c,
Python 3.11), hence a few "optional" fixes specific to one or
the other version.

Usage: python patch_deploy_tools.py <venv site-packages>
No effect if already applied. Only modifies the build venv.

The app's own settings (permissions, Java activity, icon…) are
not written into the tool: it reads them at build time from the
APPCORE_* variables that build_apk.sh prepares from app_info.py. The same venv
therefore serves every app.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

TAG = "APPCORE-PATCH"

# PySide6 6.11 only: last python-for-android commit (develop
# branch) whose python3 recipe is still 3.11, as PySide6 6.11's Android
# wheels are cp311. PySide6 6.12 pins its own commit
# (v2026.05.09, Python 3.14) and its "abi3" wheels work with that Python.
P4A_COMMIT = "3762c88c56e3443efb8eba2a02a2604b680240fd"


def _write(path: Path, text: str) -> None:
    """Rewrites through a temporary file + rename: a new file is
    created, which avoids modifying a cache shared by hard link (uv)."""
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False,
                                     prefix=path.name, suffix=".tmp") as tmp:
        tmp.write(text)
    shutil.copymode(path, tmp.name)
    os.replace(tmp.name, path)


def patch(path: Path, anchor: str, replacement: str, name: str,
          required: bool = True) -> None:
    text = path.read_text()
    if f"{TAG}: {name}" in text:
        print(f"  = {name} (already applied)")
        return
    if text.count(anchor) != 1:
        message = f"  ! {name}: reference text not found in {path}"
        if required:
            raise SystemExit(message + "\n    The tool's version changed: check this fix.")
        print(message + " (optional, skipped)")
        return
    _write(path, text.replace(anchor, replacement))
    print(f"  + {name}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    site = Path(sys.argv[1]).resolve()
    buildozer_cfg = site / "PySide6/scripts/deploy_lib/android/buildozer.py"
    if not buildozer_cfg.exists():
        raise SystemExit(f"Not found: {buildozer_cfg} (is PySide6 installed in this venv?)")
    print(f"Fixes in {site}")

    # 1) Python 3.11: otherwise the APK builds but crashes at start-up
    #    (libpython3.11.so not found by shiboken6).
    patch(buildozer_cfg,
          '        self.set_value("app", "p4a.branch", "develop")',
          '        self.set_value("app", "p4a.branch", "develop")\n'
          f'        # {TAG}: p4a-python311\n'
          f'        self.set_value("app", "p4a.commit", "{P4A_COMMIT}")',
          "p4a-python311", required=False)   # 6.11 only

    # 2) Landscape (both ways on a phone) and full screen.
    patch(buildozer_cfg,
          '        self.set_value("app", "p4a.bootstrap", "qt")',
          '        self.set_value("app", "p4a.bootstrap", "qt")\n'
          f'        # {TAG}: landscape\n'
          '        self.set_value("app", "orientation", "landscape")\n'
          '        self.set_value("app", "android.manifest.orientation", "sensorLandscape")\n'
          '        self.set_value("app", "fullscreen", "1")',
          "landscape")

    # 2b bis) Only the permissions the app uses. The tool copies
    #     those declared by every bundled Qt module, even unused ones:
    #     CAMERA and BLUETOOTH (FFmpeg multimedia plugin), INTERNET and
    #     ACCESS_NETWORK_STATE (Qt Network), WRITE_EXTERNAL_STORAGE (Qt Core).
    #     The apps have no camera, Bluetooth or network (the error report
    #     goes through the phone's email app), and their files go through
    #     Android's picker, which asks for no permission. What remains are those
    #     of ANDROID_PERMISSIONS (app_info.py), which build_apk.sh puts in
    #     APPCORE_PERMISSIONS: MODIFY_AUDIO_SETTINGS (Qt Multimedia uses it
    #     to set up sound output and the microphone; a "normal" permission,
    #     granted by Android without asking), RECORD_AUDIO for a microphone…
    #     build_apk.sh shows the permissions of the APK produced at the end.
    patch(buildozer_cfg,
          '        self.set_value("app", "android.permissions", permissions)',
          f'        # {TAG}: permissions\n'
          '        import os as _os5\n'
          '        permissions = _os5.environ.get("APPCORE_PERMISSIONS",\n'
          '                                       "android.permission.MODIFY_AUDIO_SETTINGS")\n'
          '        self.set_value("app", "android.permissions", permissions)',
          "permissions")

    # 2c) Target Android version (targetSdk). Without this setting, buildozer targets
    #     Android 12 (API 31): the phone warns that the app is "built for
    #     an older version of Android", and Google Play requires API 36 since
    #     late August 2026. APPCORE_ANDROID_API variable to choose another one.
    #     Placed after the tool's settings: PySide6 6.12 itself sets
    #     api = 35 and minapi = ndk_api = 28, which must be replaced.
    patch(buildozer_cfg,
          '        self.set_value("app", "p4a.bootstrap", "qt")',
          '        self.set_value("app", "p4a.bootstrap", "qt")\n'
          f'        # {TAG}: target-api\n'
          '        import os as _os\n'
          '        self.set_value("app", "android.api", _os.environ.get("APPCORE_ANDROID_API", "36"))\n'
          '        self.set_value("app", "android.accept_sdk_license", "True")',
          "target-api")

    # 2c bis) Minimum Android version (minSdk). buildozer uses 21 by default,
    #     which Google Play refuses ("Play automatic protection requires
    #     SDK 24 or later"). And Qt 6.8+ (so PySide6 6.11) only
    #     works from Android 9 (API 28): with 21, the app
    #     installed on Android 5 to 8 then crashed at start-up. The
    #     native libraries are built for that same version (buildozer
    #     aligns android.ndk_api with android.minapi). APPCORE_ANDROID_MINAPI variable.
    patch(buildozer_cfg,
          '        self.set_value("app", "p4a.bootstrap", "qt")',
          '        self.set_value("app", "p4a.bootstrap", "qt")\n'
          f'        # {TAG}: min-api\n'
          '        import os as _os3\n'
          '        _minapi = _os3.environ.get("APPCORE_ANDROID_MINAPI", "28")\n'
          '        self.set_value("app", "android.minapi", _minapi, raise_warning=False)\n'
          '        self.set_value("app", "android.ndk_api", _minapi, raise_warning=False)',
          "min-api")

    # 2d) Recorded sounds (sounds/ folder, .snd files): buildozer only copies
    #     the listed extensions into the APK.
    patch(buildozer_cfg,
          '        include_exts = f"{include_exts},qml,js"',
          f'        # {TAG}: sound-files\n'
          '        include_exts = f"{include_exts},qml,js,snd"',
          "sound-files")

    # 2e) Screen always on while the app is shown: the main
    #     activity becomes KeepAwakeActivity (appcore/android/java/, the
    #     python-for-android one + FLAG_KEEP_SCREEN_ON), in the app's Java package.
    #     build_apk.sh supplies the Java sources folder in APPCORE_JAVA_SRC
    #     and the activity's full name in APPCORE_ENTRYPOINT.
    patch(buildozer_cfg,
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)',
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)\n'
          f'        # {TAG}: keep-screen-on\n'
          '        import os as _os2\n'
          '        if _os2.environ.get("APPCORE_JAVA_SRC"):\n'
          '            self.set_value("app", "android.add_src", _os2.environ["APPCORE_JAVA_SRC"])\n'
          '            self.set_value("app", "android.entrypoint", _os2.environ["APPCORE_ENTRYPOINT"])',
          "keep-screen-on")

    # 2e bis) Java libraries of the app's Java (in-app purchase with Google
    #     Play Billing, reminders with WorkManager…): GRADLE_DEPENDENCIES of
    #     app_info.py, which build_apk.sh puts in APPCORE_GRADLE_DEPS (separated by
    #     commas). They require AndroidX. The permissions these
    #     libraries add (BILLING, WAKE_LOCK…) are expected by
    #     apk_permissions.py (LIBRARY_PERMISSIONS of app_info.py).
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

    # 2f) PySide6 modules not found in the Google Play version: the file
    #     android/p4a_hook.py adds the "lib" prefix to them right before the
    #     Gradle build (explained in that file). build_apk.sh
    #     supplies its path in APPCORE_P4A_HOOK.
    patch(buildozer_cfg,
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)',
          '        self.set_value("app", "android.archs", pysidedeploy_config.arch)\n'
          f'        # {TAG}: lib-prefix-hook\n'
          '        import os as _os4\n'
          '        if _os4.environ.get("APPCORE_P4A_HOOK"):\n'
          '            self.set_value("app", "p4a.hook", _os4.environ["APPCORE_P4A_HOOK"])',
          "lib-prefix-hook")

    # 3) Application icon (APPCORE_ICON variable supplied by build_apk.sh).
    patch(buildozer_cfg,
          '        self.set_value("app", "icon.filename", pysidedeploy_config.icon)',
          f'        # {TAG}: icon\n'
          '        import os as _os\n'
          '        self.set_value("app", "icon.filename",\n'
          '                       _os.environ.get("APPCORE_ICON") or pysidedeploy_config.icon)',
          "icon", required=False)

    # 3b) Lighter app: the PySide6 recipe copies the whole wheel (Qt 3D,
    #     Charts, QML, WebView… and a 2nd copy of each Qt library in
    #     the Python package, unpacked at first start). Right after these
    #     copies, android/slim_bundle.py removes what the app does not load.
    #     build_apk.sh supplies its path in APPCORE_SLIM; without this
    #     variable, nothing changes.
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

    # 4) buildozer downloads Ant and the SDK tools with urllib, which fails
    #    ("read of closed file"): use curl instead.
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
          "curl-download", required=False)   # buildozer 1.5.0 only

    # 5) Java ignores http(s)_proxy: pass the proxy to sdkmanager if there is one.
    #    (buildozer 1.6.0 does it itself: nothing to do in that case.)
    android_target = site / "buildozer/targets/android.py"
    if "--proxy_host=" in android_target.read_text() and \
            f"{TAG}: sdkmanager-proxy" not in android_target.read_text():
        print("  = sdkmanager-proxy (already done by buildozer)")
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
    print("Done.")


if __name__ == "__main__":
    main()
