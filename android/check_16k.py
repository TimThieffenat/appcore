"""Checks that the native libraries of an APK / AAB are compatible with
16 KB memory pages (Android 15+, required by Google Play).

A library is compatible when all its loaded segments (PT_LOAD) are
aligned on at least 16 KB (p_align >= 0x4000). NDK r28 and later do it
by default; libraries built with an older NDK are aligned
on 4 KB and Android 15+ in 16 KB mode refuses to load them.

Only 64-bit architectures are concerned (arm64-v8a, x86_64). The
native Python modules stored in libpybundle.so (archive of the
site-packages folder, unpacked at first start: Shiboken.abi3.so,
QtCore.abi3.so…) are checked too.

Usage: python android/check_16k.py <file.apk|.aab> [...]
Exit code 1 if a library is not compatible.
Only needs Python.
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
    """Alignments of the PT_LOAD segments of a 64-bit ELF, None if it is not one."""
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
    """Returns (compatible libraries, 4 KB libraries with their alignment)."""
    good, bad = [], []
    with zipfile.ZipFile(package) as zf:
        for name in sorted(zf.namelist()):
            parts = name.split("/")
            # APK: lib/<abi>/x.so; AAB: <module>/lib/<abi>/x.so
            if len(parts) < 3 or parts[-3] != "lib" or parts[-2] not in ABIS_64 \
                    or not name.endswith(".so"):
                continue
            data = zf.read(name)
            if data[:2] == b"\x1f\x8b":   # libpybundle.so: tar.gz archive
                for member, content in _bundle_libraries(data):
                    _sort(f"{parts[-2]}/{parts[-1]}:{member}", content, good, bad)
            else:
                _sort(f"{parts[-2]}/{parts[-1]}", data, good, bad)
    return good, bad


def _bundle_libraries(data: bytes):
    """.so files of a tar.gz archive (libpybundle.so)."""
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
        return   # not code (or 32-bit)
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
        print(f"16 KB pages: {Path(arg).name}")
        if bad:
            status = 1
            print(f"  ✗ {len(bad)} librar(y/ies) aligned on 4 KB "
                  f"(Android 15+ in 16 KB mode will refuse to load them):")
            bad.sort(key=lambda line: (":" in line, line))   # libs/ first
            shown = bad if len(bad) <= 25 else bad[:20]
            for line in shown:
                print(f"    - {line}")
            if len(shown) < len(bad):
                print(f"    … and {len(bad) - len(shown)} more")
        print(f"  ✓ {len(good)} compatible librar(y/ies)")
    return status


if __name__ == "__main__":
    sys.exit(main())
