"""Slims the APK / AAB down: removes the Qt libraries and PySide6 modules the
app does not use.

The PySide6 recipe of Qt's tool copies the WHOLE PySide6 wheel into the app:

- in the native library folder (libs/<abi>/): all Qt
  libraries (3D, Charts, Pdf, Quick, Designer…), while Qt only
  loads a few of them ("qt_libs" list of libs.xml);
- in the Python package (site-packages, compressed into libpybundle.so then
  unpacked at first start): a second copy of all these
  libraries (PySide6/Qt/lib), the plugins, QML, Qt's translations
  and all Python modules (Qt3D, QtCharts…).

This script keeps:

- in libs/: the libraries Qt loads (modules, local libraries,
  plugins) and everything they need, found by reading their ELF
  dependencies (DT_NEEDED); libraries that do not come from Qt (Python, ssl…)
  are not touched;
- in site-packages/PySide6: __init__, the Python modules of the list and
  libpyside6. The Qt/ folder (copies of the libraries, plugins, QML,
  translations) goes entirely: on Android, Qt loads its libraries
  and plugins from libs/, never from there.

Called by the PySide6 recipe ("slim" fix of patch_deploy_tools.py),
right after the wheel is copied. Can be used alone to try it:

    python android/slim_bundle.py <site-packages> <libs/arm64-v8a> Core,Gui,Widgets,...

Only needs Python.
"""

from __future__ import annotations

import shutil
import struct
import sys
from pathlib import Path

# Always kept in site-packages/PySide6 (small, or read by PySide6 itself)
KEEP_FILES = {"__init__.py", "__init__.pyc", "_config.py", "_config.pyc",
              "_git_pyside_version.py", "_git_pyside_version.pyc", "py.typed",
              "libpyside6.abi3.so"}
KEEP_DIRS = {"support", "lib"}   # small: PySide6's Python code


def needed(path: Path) -> list[str]:
    """Libraries required by a 64-bit ELF file (DT_NEEDED)."""
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if data[:4] != b"\x7fELF" or data[4] != 2:   # 64-bit ELF only (arm64)
        return []
    little = data[5] == 1
    e = "<" if little else ">"
    phoff, = struct.unpack_from(e + "Q", data, 0x20)
    phentsize, phnum = struct.unpack_from(e + "HH", data, 0x36)
    dynamic = None
    loads = []
    for i in range(phnum):
        p_type, _, p_offset, p_vaddr, _, p_filesz, _, _ = \
            struct.unpack_from(e + "IIQQQQQQ", data, phoff + i * phentsize)
        if p_type == 2:
            dynamic = (p_offset, p_filesz)
        elif p_type == 1:
            loads.append((p_vaddr, p_offset, p_filesz))
    if dynamic is None:
        return []

    def offset_of(vaddr: int) -> int:
        for start, off, size in loads:
            if start <= vaddr < start + size:
                return vaddr - start + off
        return vaddr

    strtab = None
    names = []
    off, size = dynamic
    for k in range(0, size, 16):
        tag, value = struct.unpack_from(e + "qQ", data, off + k)
        if tag == 0:
            break
        if tag == 5:          # DT_STRTAB
            strtab = offset_of(value)
        elif tag == 1:        # DT_NEEDED
            names.append(value)
    if strtab is None:
        return []
    out = []
    for value in names:
        end = data.index(b"\0", strtab + value)
        out.append(data[strtab + value:end].decode("ascii", errors="replace"))
    return out


def closure(roots: list[Path], search: list[Path]) -> set[str]:
    """Names of the libraries reached from `roots` (following DT_NEEDED)."""
    seen: set[str] = set()
    todo = list(roots)
    while todo:
        path = todo.pop()
        if path.name in seen:
            continue
        seen.add(path.name)
        for name in needed(path):
            if name in seen:
                continue
            found = next((d / name for d in search if (d / name).is_file()), None)
            if found is not None:
                todo.append(found)
            else:
                seen.add(name)   # system library (libc, liblog…)
    return seen


def slim(site_packages: Path, libs_dir: Path, modules: list[str],
         local_libs: list[str] = (), plugins: list[str] = (), arch: str = "arm64-v8a",
         log=print) -> tuple[int, int]:
    """Slims down; returns (bytes removed from libs, bytes removed from site-packages)."""
    pyside = site_packages / "PySide6"
    qt_lib = pyside / "Qt" / "lib"
    from_qt = {p.name for p in qt_lib.glob("*.so")} if qt_lib.is_dir() else set()
    modules = sorted(set(modules))
    # What Qt loads at start-up (libs.xml), plus the Python modules kept
    roots = []
    for module in modules:
        roots += [libs_dir / f"libQt6{module}_{arch}.so", pyside / f"Qt{module}.abi3.so"]
    roots += [libs_dir / f"lib{name}_{arch}.so" for name in local_libs]
    roots += [libs_dir / f"lib{name}" if name.endswith(".so") else libs_dir / f"lib{name}_{arch}.so"
              for name in plugins]
    roots += list(libs_dir.glob("libplugins_*.so"))   # all plugins copied by the tool
    roots += [pyside / "libpyside6.abi3.so"]
    if "Qml" in modules:
        roots.append(pyside / "libpyside6qml.abi3.so")
    roots = [r for r in roots if r.is_file()]
    keep = closure(roots, [libs_dir, qt_lib, pyside])

    removed_libs = 0
    for path in sorted(libs_dir.glob("*.so")):
        if path.name in from_qt and path.name not in keep:
            removed_libs += path.stat().st_size
            path.unlink()
            log(f"  - libs/{path.name}")

    removed_site = 0

    def drop(path: Path) -> None:
        nonlocal removed_site
        if path.is_dir():
            removed_site += sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            shutil.rmtree(path)
        elif path.exists():
            removed_site += path.stat().st_size
            path.unlink()

    if pyside.is_dir():
        wanted = {f"Qt{m}.abi3.so" for m in modules}
        if "Qml" in modules:
            wanted.add("libpyside6qml.abi3.so")
        for path in sorted(pyside.iterdir()):
            if path.is_dir():
                if path.name not in KEEP_DIRS:
                    drop(path)   # Qt/ (libraries, plugins, QML, translations), include, jar…
            elif path.name not in KEEP_FILES and path.name not in wanted:
                drop(path)       # unused modules, .pyi files
    for extra in ("include", "lib"):   # shiboken6: C++ headers, build tools
        if (site_packages / "shiboken6" / extra).is_dir() and extra == "include":
            drop(site_packages / "shiboken6" / extra)
    for stub in site_packages.glob("shiboken6/*.pyi"):
        drop(stub)
    log(f"  libs: {removed_libs / 1e6:.1f} MB removed, site-packages: "
        f"{removed_site / 1e6:.1f} MB removed")
    return removed_libs, removed_site


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    modules = [m for m in sys.argv[3].split(",") if m]
    slim(Path(sys.argv[1]), Path(sys.argv[2]), modules)
    return 0


if __name__ == "__main__":
    sys.exit(main())
