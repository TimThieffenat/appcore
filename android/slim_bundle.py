"""Allège l'APK / AAB : retire les bibliothèques Qt et les modules PySide6 dont
l'app ne se sert pas.

La recette PySide6 de l'outil de Qt copie TOUTE la roue PySide6 dans l'app :

- dans le dossier des bibliothèques natives (libs/<abi>/) : toutes les
  bibliothèques Qt (3D, Charts, Pdf, Quick, Designer…), alors que Qt n'en
  charge que quelques-unes (liste « qt_libs » de libs.xml) ;
- dans le paquet Python (site-packages, compressé dans libpybundle.so puis
  décompressé au premier lancement) : une deuxième copie de toutes ces
  bibliothèques (PySide6/Qt/lib), les plugins, le QML, les traductions de Qt
  et tous les modules Python (Qt3D, QtCharts…).

Ce script garde :

- dans libs/ : les bibliothèques que Qt charge (modules, bibliothèques locales,
  plugins) et tout ce dont elles ont besoin, trouvé en lisant leurs dépendances
  ELF (DT_NEEDED) ; les bibliothèques qui ne viennent pas de Qt (Python, ssl…)
  ne sont pas touchées ;
- dans site-packages/PySide6 : __init__, les modules Python de la liste et
  libpyside6. Le dossier Qt/ (copies des bibliothèques, plugins, QML,
  traductions) part entièrement : sur Android, Qt charge ses bibliothèques
  et ses plugins depuis libs/, jamais depuis là.

Appelé par la recette PySide6 (correctif « slim » de patch_deploy_tools.py),
juste après la copie de la roue. Utilisable seul pour essayer :

    python android/slim_bundle.py <site-packages> <libs/arm64-v8a> Core,Gui,Widgets,...

N'a besoin que de Python.
"""

from __future__ import annotations

import shutil
import struct
import sys
from pathlib import Path

# Toujours gardés dans site-packages/PySide6 (petits, ou lus par PySide6 lui-même)
KEEP_FILES = {"__init__.py", "__init__.pyc", "_config.py", "_config.pyc",
              "_git_pyside_version.py", "_git_pyside_version.pyc", "py.typed",
              "libpyside6.abi3.so"}
KEEP_DIRS = {"support", "lib"}   # petits : code Python de PySide6


def needed(path: Path) -> list[str]:
    """Bibliothèques demandées par un fichier ELF 64 bits (DT_NEEDED)."""
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if data[:4] != b"\x7fELF" or data[4] != 2:   # ELF 64 bits seulement (arm64)
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
    """Noms des bibliothèques atteintes depuis `roots` (en suivant DT_NEEDED)."""
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
                seen.add(name)   # bibliothèque du système (libc, liblog…)
    return seen


def slim(site_packages: Path, libs_dir: Path, modules: list[str],
         local_libs: list[str] = (), plugins: list[str] = (), arch: str = "arm64-v8a",
         log=print) -> tuple[int, int]:
    """Allège ; renvoie (octets retirés de libs, octets retirés de site-packages)."""
    pyside = site_packages / "PySide6"
    qt_lib = pyside / "Qt" / "lib"
    from_qt = {p.name for p in qt_lib.glob("*.so")} if qt_lib.is_dir() else set()
    modules = sorted(set(modules))
    # Ce que Qt charge au démarrage (libs.xml), plus les modules Python gardés
    roots = []
    for module in modules:
        roots += [libs_dir / f"libQt6{module}_{arch}.so", pyside / f"Qt{module}.abi3.so"]
    roots += [libs_dir / f"lib{name}_{arch}.so" for name in local_libs]
    roots += [libs_dir / f"lib{name}" if name.endswith(".so") else libs_dir / f"lib{name}_{arch}.so"
              for name in plugins]
    roots += list(libs_dir.glob("libplugins_*.so"))   # tous les plugins copiés par l'outil
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
                    drop(path)   # Qt/ (bibliothèques, plugins, QML, traductions), include, jar…
            elif path.name not in KEEP_FILES and path.name not in wanted:
                drop(path)       # modules inutilisés, fichiers .pyi
    for extra in ("include", "lib"):   # shiboken6 : en-têtes C++, outils de compilation
        if (site_packages / "shiboken6" / extra).is_dir() and extra == "include":
            drop(site_packages / "shiboken6" / extra)
    for stub in site_packages.glob("shiboken6/*.pyi"):
        drop(stub)
    log(f"  libs : {removed_libs / 1e6:.1f} Mo retirés, site-packages : "
        f"{removed_site / 1e6:.1f} Mo retirés")
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
