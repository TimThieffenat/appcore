"""python-for-android fix, called while the APK / AAB is being made.

buildozer passes it to python-for-android (p4a.hook setting, see
patch_deploy_tools.py). python-for-android calls `after_apk_build` once
the Android project is prepared (libraries in libs/, resources in
src/main/res), right before Gradle builds it.

The problem: at start-up, Qt loads the PySide6 modules (QtCore.abi3.so,
QtGui.abi3.so…) from the app's library folder. But Android only
installs files whose name starts with "lib" there when the app
is not in debug mode, which is the case of the Google Play version. Qt did not
find them ("QtLoader: Can't find …/lib/arm64/QtCore.abi3.so") and
the app closed right after its logo. The test APK (debug mode) was
not affected: Android installs all libraries there.

The fix: these modules take the "lib" prefix (libQtCore.abi3.so…),
in the libs/ folder and in the list Qt reads (res/values/libs.xml).
Python is not concerned: it loads its own copies, in the app's
folder (site-packages/PySide6).

Second fix: each library of Qt's list must exist in
libs/<abi>/. At start-up, Qt loads them one by one and stops at the first one
not found ("QtLoader: Can't find …"): the app closes at once. With
PySide6 6.12, Qt's tool adds Qt Multimedia's FFmpeg libraries to the list
under the name "libavcodec_arm64-v8a.so", while they are
shipped as "libavcodec.so": the first 6.12 version of the app
closed at start-up. An entry not found takes the name of the file present
without the architecture suffix (libavcodec.so); if there is none either,
it is removed from the list (and noted in the build log).

Third fix: the loading order. Qt loads its lists in
order, and each library runs its initialisation code (JNI_OnLoad)
when loaded: libQt6Multimedia then calls Java through Qt Core, which
must therefore be loaded (and initialised) BEFORE it. Qt's tool writes the
modules in a random order (it goes through a Python set, whose order
changes from one build to the next): about one build in two,
Multimedia came before Core, and the app closed on a black screen right at
start-up (SIGSEGV in QJniEnvironment::getJniEnv). Each list is therefore
put back in dependency order (ELF DT_NEEDED): a library always comes
after those it needs, otherwise the original order is kept.
"""

from __future__ import annotations

import os
import re
import struct
from pathlib import Path

# Name of a PySide6 module copied into libs/<abi>/ without the "lib" prefix
MODULE = re.compile(r"Qt\w+\.abi3\.so")
# The same name in Qt's list: <item>arm64-v8a;QtCore.abi3.so</item>
LIST_ITEM = re.compile(r"(<item>[\w-]+;)(Qt\w+\.abi3\.so)(</item>)")


# An entry of Qt's lists: <item>arm64-v8a;libavutil_arm64-v8a.so</item>
# (several libraries possible, separated by ":")
ANY_ITEM = re.compile(r"<item>([\w-]+);([^<]*)</item>")


def library_file(name: str) -> str:
    """The file Qt looks for for a name of the list (QtLoader.java:
    "Qt6Core_arm64-v8a" -> libQt6Core_arm64-v8a.so, a name ending in .so as is)."""
    return name if name.endswith(".so") else f"lib{name}.so"


def fix_missing_libs(dist_dir: Path) -> list[str]:
    """Each library of Qt's lists (libs.xml) must exist in
    libs/<abi>/: otherwise take the same name without the architecture suffix, or
    remove it from the list. Returns what changed."""
    libs_xml = dist_dir / "src" / "main" / "res" / "values" / "libs.xml"
    libs = dist_dir / "libs"
    if not libs_xml.is_file() or not libs.is_dir():
        return []
    changed: list[str] = []

    def fix(match: re.Match) -> str:
        abi, names = match.group(1), match.group(2)
        abi_dir = libs / abi
        if not abi_dir.is_dir() or not names.strip():
            return match.group(0)
        kept = []
        for name in names.split(":"):
            if (abi_dir / library_file(name)).is_file():
                kept.append(name)
                continue
            plain = re.sub(rf"_{re.escape(abi)}\.so$", ".so", library_file(name))
            if plain != library_file(name) and (abi_dir / plain).is_file():
                kept.append(plain)
                changed.append(f"{abi}/{library_file(name)} -> {plain}")
            else:
                changed.append(f"{abi}/{library_file(name)}: not found, removed from the list")
        if not kept:
            return ""
        return f"<item>{abi};{':'.join(kept)}</item>"

    text = libs_xml.read_text(encoding="utf-8")
    new_text = ANY_ITEM.sub(fix, text)
    if new_text != text:
        libs_xml.write_text(new_text, encoding="utf-8")
    return changed


def needed(path: Path) -> list[str]:
    """Libraries required by a 64-bit ELF file (DT_NEEDED)."""
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2:
        return []
    e = "<" if data[5] == 1 else ">"
    phoff, = struct.unpack_from(e + "Q", data, 0x20)
    phentsize, phnum = struct.unpack_from(e + "HH", data, 0x36)
    dynamic, loads = None, []
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

    strtab, names = None, []
    off, size = dynamic
    for k in range(0, size, 16):
        tag, value = struct.unpack_from(e + "qQ", data, off + k)
        if tag == 0:
            break
        if tag == 5:
            strtab = offset_of(value)
        elif tag == 1:
            names.append(value)
    if strtab is None:
        return []
    return [data[strtab + v:data.index(b"\0", strtab + v)].decode("ascii", "replace")
            for v in names]


ARRAY = re.compile(r'(<array name="(\w+)">)(.*?)(</array>)', re.S)


def order_libs(dist_dir: Path) -> list[str]:
    """Puts each list of libs.xml back in dependency order: each
    library after those it needs (in this list or in the
    previous lists, which Qt loads first). Returns what changed."""
    libs_xml = dist_dir / "src" / "main" / "res" / "values" / "libs.xml"
    libs = dist_dir / "libs"
    if not libs_xml.is_file() or not libs.is_dir():
        return []
    changed: list[str] = []

    def sort_array(match: re.Match) -> str:
        head, name, body, tail = match.groups()
        items = list(ANY_ITEM.finditer(body))
        if len(items) < 2:
            return match.group(0)
        files = []
        for item in items:
            abi_dir = libs / item.group(1)
            files.append([abi_dir / library_file(n) for n in item.group(2).split(":") if n])
        provides = [{f.name for f in group} for group in files]
        wants = [{n for f in group for n in needed(f)} for group in files]
        order: list[int] = []
        placed: set[str] = set()
        todo = list(range(len(items)))
        while todo:
            listed = set().union(*(provides[i] for i in todo))
            # the first item (in the original order) whose dependencies in
            # the list are already loaded; if there is none (cycle): the first
            pick = next((i for i in todo if not (wants[i] & listed) - placed - provides[i]),
                        todo[0])
            todo.remove(pick)
            order.append(pick)
            placed |= provides[pick]
        if order == list(range(len(items))):
            return match.group(0)
        before = [items[i].group(2) for i in range(len(items))]
        after = [items[i].group(2) for i in order]
        changed.append(f"{name} : " + " < ".join(after))
        new_items = "\n        ".join(items[i].group(0) for i in order)
        start, end = items[0].start(), items[-1].end()
        return head + body[:start] + new_items + body[end:] + tail if before != after \
            else match.group(0)

    text = libs_xml.read_text(encoding="utf-8")
    new_text = ARRAY.sub(sort_array, text)
    if new_text != text:
        libs_xml.write_text(new_text, encoding="utf-8")
    return changed


def add_lib_prefix(dist_dir: Path) -> list[str]:
    """Renames the modules and updates Qt's list. Returns what changed.
    No effect if already done (the project folder is reused)."""
    changed = []
    libs = dist_dir / "libs"
    if libs.is_dir():
        for abi_dir in sorted(p for p in libs.iterdir() if p.is_dir()):
            for module in sorted(abi_dir.iterdir()):
                if MODULE.fullmatch(module.name):
                    os.replace(module, abi_dir / f"lib{module.name}")
                    changed.append(f"{abi_dir.name}/{module.name} -> lib{module.name}")
    libs_xml = dist_dir / "src" / "main" / "res" / "values" / "libs.xml"
    if libs_xml.is_file():
        text = libs_xml.read_text(encoding="utf-8")
        new_text, count = LIST_ITEM.subn(r"\1lib\2\3", text)
        if count:
            libs_xml.write_text(new_text, encoding="utf-8")
            changed.append(f"libs.xml : {count} module(s) -> lib…")
    return changed


def after_apk_build(toolchain) -> None:
    """Called by python-for-android, in the Android project folder."""
    try:
        dist_dir = Path(toolchain._dist.dist_dir)
    except Exception:  # noqa: BLE001 — otherwise: the current folder (the same one)
        dist_dir = Path.cwd()
    changed = add_lib_prefix(dist_dir)
    print("[APPCORE-PATCH] PySide6 modules prefixed with \"lib\":",
          ", ".join(changed) if changed else "nothing to do", flush=True)
    fixed = fix_missing_libs(dist_dir)
    print("[APPCORE-PATCH] Qt's library list:",
          ", ".join(fixed) if fixed else "all present", flush=True)
    ordered = order_libs(dist_dir)
    print("[APPCORE-PATCH] Qt's loading order:",
          " | ".join(ordered) if ordered else "already in dependency order", flush=True)
