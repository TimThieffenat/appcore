"""Réglages Android de l'app, lus dans son app_info.py, pour les scripts shell.

    eval "$(python3 appcore/android/app_config.py <dossier de l'app>)"
    python3 appcore/android/app_config.py . --get APP_KEY_ALIAS
    python3 appcore/android/app_config.py . --github-env >> "$GITHUB_ENV"

écrit des lignes « export APP_NAME=... » : nom, version, paquet Google Play,
paquet Java, autorisations, clé de signature, dossiers en plus. app_info.py
est lu sans être importé (runpy) : ses constantes ne doivent rien importer.
Tout ce qui manque prend la valeur par défaut du socle (appcore/app.py).
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
    """« RECORD_AUDIO » -> « android.permission.RECORD_AUDIO » (un nom complet reste tel quel)."""
    return name if "." in name else f"android.permission.{name}"


def config(root: Path) -> dict[str, str]:
    path = root / "app_info.py"
    if not path.is_file():
        raise SystemExit(f"app_info.py introuvable dans {root}")
    info = dict(DEFAULTS)
    info.update({k: v for k, v in runpy.run_path(str(path)).items() if k.isupper()})
    name = str(info["NAME"])
    if not IDENTIFIER.fullmatch(name):
        raise SystemExit(f"NAME = {name!r} : doit être un identifiant Java valide "
                         "(lettres, chiffres, _), c'est le nom de l'APK")
    slug = "".join(c for c in name.lower() if c.isalnum())
    package = str(info["ANDROID_PACKAGE"] or f"com.{slug}.app")
    if package.count(".") < 1:
        raise SystemExit(f"ANDROID_PACKAGE = {package!r} : il faut au moins deux parties (com.nom.app)")
    domain, _, short = package.rpartition(".")
    permissions = ", ".join(_permission(p) for p in info["ANDROID_PERMISSIONS"])
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
        "APP_GRADLE_DEPS": ",".join(str(d) for d in info["GRADLE_DEPENDENCIES"]),
        "APP_LIBRARY_PERMISSIONS": ", ".join(_permission(p) for p in info["LIBRARY_PERMISSIONS"]),
    }


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    values = config(root)
    if "--get" in sys.argv:          # une seule valeur : app_config.py <dossier> --get APP_NAME
        print(values[sys.argv[sys.argv.index("--get") + 1]])
        return
    if "--github-env" in sys.argv:   # format de $GITHUB_ENV (GitHub Actions) : CLÉ=valeur
        for key, value in values.items():
            print(f"{key}={value}")
        return
    for key, value in values.items():
        print(f"export {key}={shlex.quote(value)}")


if __name__ == "__main__":
    main()
