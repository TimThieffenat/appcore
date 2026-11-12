"""The app's Android settings, read from its app_info.py, for shell scripts.

    eval "$(python3 appcore/android/app_config.py <app folder>)"
    python3 appcore/android/app_config.py . --get APP_KEY_ALIAS
    python3 appcore/android/app_config.py . --github-env >> "$GITHUB_ENV"

writes "export APP_NAME=..." lines: name, version, Google Play package,
Java package, permissions, signing key, extra folders, orientation, Pro
product (which adds Google Play Billing and its permissions). app_info.py
is read without being imported (runpy): its constants must not import anything.
Anything missing takes the base's default value (appcore/app.py).
"""

from __future__ import annotations

import re
import runpy
import shlex
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE.parent))
from appcore.app import DEFAULTS  # noqa: E402

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _permission(name: str) -> str:
    """"RECORD_AUDIO" -> "android.permission.RECORD_AUDIO" (a full name stays as is)."""
    return name if "." in name else f"android.permission.{name}"


# What a Pro version (PRO_PRODUCT) needs: Google Play Billing (PlayBilling.java.in,
# version 8 required by Google Play since 31 August 2026). androidx.fragment: a
# Google library brought by Billing pulls 1.1.0, flagged as outdated by the Play
# Console; asking for it here makes Gradle take this newer one (it keeps the
# highest).
BILLING_DEPENDENCIES = ("com.android.billingclient:billing:8.3.0",
                        "androidx.fragment:fragment:1.6.2")
BILLING_PERMISSIONS = ("com.android.vending.BILLING", "ACCESS_NETWORK_STATE")


def _merged(base, extra) -> list[str]:
    """`base` then the items of `extra` it lacks (a Gradle dependency counts once,
    whatever its version)."""
    out = [str(x) for x in base]
    keys = {x.rsplit(":", 1)[0] if x.count(":") == 2 else x for x in out}
    for item in extra:
        key = item.rsplit(":", 1)[0] if item.count(":") == 2 else item
        if key not in keys:
            out.append(item)
            keys.add(key)
    return out


def config(root: Path) -> dict[str, str]:
    path = root / "app_info.py"
    if not path.is_file():
        raise SystemExit(f"app_info.py not found in {root}")
    info = dict(DEFAULTS)
    info.update({k: v for k, v in runpy.run_path(str(path)).items() if k.isupper()})
    name = str(info["NAME"])
    if not IDENTIFIER.fullmatch(name):
        raise SystemExit(f"NAME = {name!r}: must be a valid Java identifier "
                         "(letters, digits, _), it is the APK's name")
    slug = "".join(c for c in name.lower() if c.isalnum())
    package = str(info["ANDROID_PACKAGE"] or f"com.{slug}.app")
    if package.count(".") < 1:
        raise SystemExit(f"ANDROID_PACKAGE = {package!r}: needs at least two parts (com.name.app)")
    domain, _, short = package.rpartition(".")
    permissions = ", ".join(_permission(p) for p in info["ANDROID_PERMISSIONS"])
    pro = str(info.get("PRO_PRODUCT") or "").strip()
    if pro and not re.fullmatch(r"[a-z0-9][a-z0-9._]*", pro):
        raise SystemExit(f"PRO_PRODUCT = {pro!r}: a Play product ID (lower case, digits, . _)")
    gradle = list(info["GRADLE_DEPENDENCIES"])
    library = [_permission(p) for p in info["LIBRARY_PERMISSIONS"]]
    if pro:
        gradle = _merged(gradle, BILLING_DEPENDENCIES)
        library = _merged(library, [_permission(p) for p in BILLING_PERMISSIONS])
    return {
        "APP_NAME": name,
        "APP_SLUG": slug,
        "APP_VERSION": str(info["VERSION"]),
        "APP_PACKAGE": package,
        "PACKAGE_DOMAIN": domain,
        "PACKAGE_NAME": short,
        "JAVA_PACKAGE": str(info["JAVA_PACKAGE"] or f"org.{slug}"),
        "APP_PERMISSIONS": permissions,
        "APP_KEY_ALIAS": str(info["KEY_ALIAS"] or slug),
        "APP_KEYSTORE_NAME": str(info["KEYSTORE_NAME"] or f"{slug}-upload.jks"),
        "APP_EXTRA_DIRS": " ".join(str(d) for d in info["EXTRA_DIRS"]),
        "APP_GRADLE_DEPS": ",".join(gradle),
        "APP_LIBRARY_PERMISSIONS": ", ".join(library),
        "APP_PRO_PRODUCT": pro,
        "APP_ORIENTATION": ("portrait" if str(info["ORIENTATION"]).lower() == "portrait"
                            else "landscape"),
    }


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    values = config(root)
    if "--get" in sys.argv:          # a single value: app_config.py <folder> --get APP_NAME
        print(values[sys.argv[sys.argv.index("--get") + 1]])
        return
    if "--github-env" in sys.argv:   # $GITHUB_ENV format (GitHub Actions): KEY=value
        for key, value in values.items():
            print(f"{key}={value}")
        return
    for key, value in values.items():
        print(f"export {key}={shlex.quote(value)}")


if __name__ == "__main__":
    main()
