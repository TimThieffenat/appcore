"""Vérifie qu'un APK / AAB contient toutes les bibliothèques que Qt charge au
démarrage.

Qt lit ses listes (res/values/libs.xml : qt_libs, load_local_libs,
bundled_libs) et charge chaque bibliothèque, dans l'ordre ; à la première
introuvable (« QtLoader: Can't find … »), l'app se ferme aussitôt. Ce script
relit ces listes dans le fichier compilé (resources.arsc dans un APK,
resources.pb dans un AAB) et cherche chaque fichier dans lib/<abi>/.

Usage : python android/check_qt_libs.py <fichier.apk|.aab> [...]
Code de sortie 1 s'il en manque une. N'a besoin que de Python.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ABIS = ("arm64-v8a", "armeabi-v7a", "x86_64", "x86")
# Une entrée des listes : « arm64-v8a;Qt6Core_arm64-v8a » ou « arm64-v8a;libx.so:liby.so »
ENTRY = re.compile(r"(arm64-v8a|armeabi-v7a|x86_64|x86);([A-Za-z0-9_.+:-]+)")


def library_file(name: str) -> str:
    """Comme QtLoader.java : un nom sans .so devient lib<nom>.so."""
    return name if name.endswith(".so") else f"lib{name}.so"


def _strings(data: bytes) -> set[str]:
    """Entrées « abi;bibliothèques » trouvées dans les ressources compilées
    (chaînes UTF-8 et UTF-16)."""
    found = set()
    for text in (data.decode("latin-1"), data.decode("utf-16-le", errors="ignore")):
        for abi, names in ENTRY.findall(text):
            found.add(f"{abi};{names}")
    return found


def check(package: Path) -> tuple[list[str], list[str]]:
    """Renvoie (bibliothèques trouvées, bibliothèques manquantes)."""
    with zipfile.ZipFile(package) as zf:
        names = zf.namelist()
        resources = [n for n in names if n.endswith(("resources.arsc", "resources.pb"))]
        entries: set[str] = set()
        for name in resources:
            entries |= _strings(zf.read(name))
        present = {}
        for name in names:
            parts = name.split("/")
            if len(parts) >= 3 and parts[-3] == "lib" and parts[-2] in ABIS:
                present.setdefault(parts[-2], set()).add(parts[-1])
    found, missing = [], []
    for entry in sorted(entries):
        abi, libs = entry.split(";", 1)
        if abi not in present:
            continue   # autre architecture, absente du paquet
        for lib in libs.split(":"):
            if not lib:
                continue
            target = library_file(lib)
            (found if target in present[abi] else missing).append(f"{abi}/{target}")
    return found, missing


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    status = 0
    for arg in sys.argv[1:]:
        found, missing = check(Path(arg))
        print(f"Bibliothèques chargées par Qt au démarrage : {Path(arg).name}")
        if not found and not missing:
            print("  ? listes de Qt introuvables dans les ressources (rien vérifié)")
            continue
        if missing:
            status = 1
            print(f"  ✗ {len(missing)} introuvable(s) dans le paquet : l'app se fermera "
                  "au démarrage (« QtLoader: Can't find … ») :")
            for line in missing:
                print(f"    - {line}")
        print(f"  ✓ {len(found)} présente(s)")
    return status


if __name__ == "__main__":
    sys.exit(main())
