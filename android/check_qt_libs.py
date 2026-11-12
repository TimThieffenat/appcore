"""Checks that an APK / AAB holds all the libraries Qt loads at
start-up.

Qt reads its lists (res/values/libs.xml: qt_libs, load_local_libs,
bundled_libs) and loads each library, in order; at the first one
not found ("QtLoader: Can't find …"), the app closes at once. This script
reads those lists again in the built file (resources.arsc in an APK,
resources.pb in an AAB) and looks for each file in lib/<abi>/.

Usage: python android/check_qt_libs.py <file.apk|.aab> [...]
Exit code 1 if one is missing. Only needs Python.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ABIS = ("arm64-v8a", "armeabi-v7a", "x86_64", "x86")
# An entry of the lists: "arm64-v8a;Qt6Core_arm64-v8a" or "arm64-v8a;libx.so:liby.so"
ENTRY = re.compile(r"(arm64-v8a|armeabi-v7a|x86_64|x86);([A-Za-z0-9_.+:-]+)")


def library_file(name: str) -> str:
    """Like QtLoader.java: a name without .so becomes lib<name>.so."""
    return name if name.endswith(".so") else f"lib{name}.so"


def _strings(data: bytes) -> set[str]:
    """"abi;libraries" entries found in the compiled resources
    (UTF-8 and UTF-16 strings)."""
    found = set()
    for text in (data.decode("latin-1"), data.decode("utf-16-le", errors="ignore")):
        for abi, names in ENTRY.findall(text):
            found.add(f"{abi};{names}")
    return found


def check(package: Path) -> tuple[list[str], list[str]]:
    """Returns (libraries found, libraries missing)."""
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
            continue   # another architecture, absent from the package
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
        print(f"Libraries loaded by Qt at start-up: {Path(arg).name}")
        if not found and not missing:
            print("  ? Qt's lists not found in the resources (nothing checked)")
            continue
        if missing:
            status = 1
            print(f"  ✗ {len(missing)} not found in the package: the app will close "
                  "at start-up (\"QtLoader: Can't find …\"):")
            for line in missing:
                print(f"    - {line}")
        print(f"  ✓ {len(found)} present")
    return status


if __name__ == "__main__":
    sys.exit(main())
