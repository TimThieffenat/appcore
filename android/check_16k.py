"""Vérifie que les bibliothèques natives d'un APK / AAB sont compatibles avec
les pages mémoire de 16 Ko (Android 15+, exigé par Google Play).

Une bibliothèque est compatible quand tous ses segments chargés (PT_LOAD) sont
alignés sur 16 Ko au moins (p_align >= 0x4000). Le NDK r28 et suivants le font
par défaut ; les bibliothèques compilées avec un NDK plus ancien sont alignées
sur 4 Ko et Android 15+ en mode 16 Ko refuse de les charger.

Seules les architectures 64 bits sont concernées (arm64-v8a, x86_64). Les
modules Python natifs rangés dans libpybundle.so (archive du dossier
site-packages, décompressée au premier lancement : Shiboken.abi3.so,
QtCore.abi3.so…) sont vérifiés aussi.

Usage : python android/check_16k.py <fichier.apk|.aab> [...]
Code de sortie 1 si une bibliothèque n'est pas compatible.
N'a besoin que de Python.
"""

from __future__ import annotations

import io
import struct
import sys
import tarfile
import zipfile
from pathlib import Path

PAGE_16K = 0x4000
ABIS_64 = ("arm64-v8a", "x86_64")


def load_alignments(data: bytes) -> list[int] | None:
    """Alignements des segments PT_LOAD d'un ELF 64 bits, None si ce n'en est pas un."""
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2:
        return None
    e = "<" if data[5] == 1 else ">"
    phoff, = struct.unpack_from(e + "Q", data, 0x20)
    phentsize, phnum = struct.unpack_from(e + "HH", data, 0x36)
    aligns = []
    for i in range(phnum):
        base = phoff + i * phentsize
        if base + 56 > len(data):
            break
        p_type, = struct.unpack_from(e + "I", data, base)
        if p_type == 1:   # PT_LOAD
            p_align, = struct.unpack_from(e + "Q", data, base + 48)
            aligns.append(p_align)
    return aligns


def check(package: Path) -> tuple[list[str], list[str]]:
    """Renvoie (bibliothèques compatibles, bibliothèques à 4 Ko avec leur alignement)."""
    good, bad = [], []
    with zipfile.ZipFile(package) as zf:
        for name in sorted(zf.namelist()):
            parts = name.split("/")
            # APK : lib/<abi>/x.so ; AAB : <module>/lib/<abi>/x.so
            if len(parts) < 3 or parts[-3] != "lib" or parts[-2] not in ABIS_64 \
                    or not name.endswith(".so"):
                continue
            data = zf.read(name)
            if data[:2] == b"\x1f\x8b":   # libpybundle.so : archive tar.gz
                for member, content in _bundle_libraries(data):
                    _sort(f"{parts[-2]}/{parts[-1]}:{member}", content, good, bad)
            else:
                _sort(f"{parts[-2]}/{parts[-1]}", data, good, bad)
    return good, bad


def _bundle_libraries(data: bytes):
    """Fichiers .so d'une archive tar.gz (libpybundle.so)."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r|gz") as tar:
            for member in tar:
                if member.isfile() and member.name.endswith(".so"):
                    handle = tar.extractfile(member)
                    if handle is not None:
                        yield member.name.removeprefix("./"), handle.read()
    except (tarfile.TarError, OSError, EOFError):
        return


def _sort(label: str, data: bytes, good: list[str], bad: list[str]) -> None:
    aligns = load_alignments(data)
    if aligns is None:
        return   # pas du code (ou 32 bits)
    smallest = min(aligns) if aligns else 0
    if smallest >= PAGE_16K:
        good.append(label)
    else:
        bad.append(f"{label} (alignement {smallest // 1024} Ko)")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    status = 0
    for arg in sys.argv[1:]:
        good, bad = check(Path(arg))
        print(f"Pages de 16 Ko : {Path(arg).name}")
        if bad:
            status = 1
            print(f"  ✗ {len(bad)} bibliothèque(s) alignée(s) sur 4 Ko "
                  f"(Android 15+ en 16 Ko refusera de les charger) :")
            bad.sort(key=lambda line: (":" in line, line))   # libs/ d'abord
            shown = bad if len(bad) <= 25 else bad[:20]
            for line in shown:
                print(f"    - {line}")
            if len(shown) < len(bad):
                print(f"    … et {len(bad) - len(shown)} autre(s)")
        print(f"  ✓ {len(good)} bibliothèque(s) compatible(s)")
    return status


if __name__ == "__main__":
    sys.exit(main())
