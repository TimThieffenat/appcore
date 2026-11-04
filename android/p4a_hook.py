"""Correctif de python-for-android, appelé pendant la fabrication de l'APK / AAB.

buildozer le transmet à python-for-android (réglage p4a.hook, voir
patch_deploy_tools.py). python-for-android appelle `after_apk_build` une fois
le projet Android préparé (bibliothèques dans libs/, ressources dans
src/main/res), juste avant la compilation par Gradle.

Le problème : au démarrage, Qt charge les modules de PySide6 (QtCore.abi3.so,
QtGui.abi3.so…) depuis le dossier des bibliothèques de l'app. Mais Android
n'y installe que les fichiers dont le nom commence par « lib » quand l'app
n'est pas en mode débogage, ce qui est le cas de la version Google Play. Qt ne
les trouvait pas (« QtLoader: Can't find …/lib/arm64/QtCore.abi3.so ») et
l'app se fermait juste après son logo. L'APK de test (mode débogage) n'était
pas touché : Android y installe toutes les bibliothèques.

Le correctif : ces modules prennent le préfixe « lib » (libQtCore.abi3.so…),
dans le dossier libs/ et dans la liste que lit Qt (res/values/libs.xml).
Python n'est pas concerné : il charge ses propres copies, dans le dossier de
l'app (site-packages/PySide6).

Second correctif : chaque bibliothèque de la liste de Qt doit exister dans
libs/<abi>/. Au démarrage, Qt les charge une à une et s'arrête à la première
introuvable (« QtLoader: Can't find … ») : l'app se ferme aussitôt. Avec
PySide6 6.12, l'outil de Qt ajoute à la liste les bibliothèques FFmpeg de Qt
Multimedia sous le nom « libavcodec_arm64-v8a.so », alors qu'elles sont
livrées sous le nom « libavcodec.so » : la 1re version 6.12 de l'app se
fermait au démarrage. Une entrée introuvable prend le nom du fichier présent
sans le suffixe d'architecture (libavcodec.so) ; s'il n'y en a pas non plus,
elle est retirée de la liste (et notée dans le journal de compilation).

Troisième correctif : l'ordre de chargement. Qt charge ses listes dans
l'ordre, et chaque bibliothèque exécute son code d'initialisation (JNI_OnLoad)
au chargement : libQt6Multimedia appelle alors Java à travers Qt Core, qui
doit donc être chargée (et initialisée) AVANT elle. L'outil de Qt écrit les
modules dans un ordre au hasard (il passe par un ensemble Python, dont l'ordre
change d'une compilation à l'autre) : une compilation sur deux environ,
Multimedia passait avant Core, et l'app se fermait sur un écran noir dès son
lancement (SIGSEGV dans QJniEnvironment::getJniEnv). Chaque liste est donc
remise dans l'ordre des dépendances (ELF DT_NEEDED) : une bibliothèque vient
toujours après celles dont elle a besoin, sinon l'ordre d'origine est gardé.
"""

from __future__ import annotations

import os
import re
import struct
from pathlib import Path

# Nom d'un module PySide6 copié dans libs/<abi>/ sans le préfixe « lib »
MODULE = re.compile(r"Qt\w+\.abi3\.so")
# Le même nom dans la liste de Qt : <item>arm64-v8a;QtCore.abi3.so</item>
LIST_ITEM = re.compile(r"(<item>[\w-]+;)(Qt\w+\.abi3\.so)(</item>)")


# Une entrée des listes de Qt : <item>arm64-v8a;libavutil_arm64-v8a.so</item>
# (plusieurs bibliothèques possibles, séparées par « : »)
ANY_ITEM = re.compile(r"<item>([\w-]+);([^<]*)</item>")


def library_file(name: str) -> str:
    """Le fichier que Qt cherche pour un nom de la liste (QtLoader.java :
    « Qt6Core_arm64-v8a » -> libQt6Core_arm64-v8a.so, un nom en .so tel quel)."""
    return name if name.endswith(".so") else f"lib{name}.so"


def fix_missing_libs(dist_dir: Path) -> list[str]:
    """Chaque bibliothèque des listes de Qt (libs.xml) doit exister dans
    libs/<abi>/ : sinon on prend le même nom sans suffixe d'architecture, ou on
    la retire de la liste. Renvoie ce qui a changé."""
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
                changed.append(f"{abi}/{library_file(name)} : introuvable, retirée de la liste")
        if not kept:
            return ""
        return f"<item>{abi};{':'.join(kept)}</item>"

    text = libs_xml.read_text(encoding="utf-8")
    new_text = ANY_ITEM.sub(fix, text)
    if new_text != text:
        libs_xml.write_text(new_text, encoding="utf-8")
    return changed


def needed(path: Path) -> list[str]:
    """Bibliothèques demandées par un fichier ELF 64 bits (DT_NEEDED)."""
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
    """Remet chaque liste de libs.xml dans l'ordre des dépendances : chaque
    bibliothèque après celles dont elle a besoin (dans cette liste ou dans les
    listes précédentes, que Qt charge avant). Renvoie ce qui a changé."""
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
            # le premier élément (dans l'ordre d'origine) dont les dépendances de
            # la liste sont déjà chargées ; s'il n'y en a pas (cycle) : le premier
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
    """Renomme les modules et met la liste de Qt à jour. Renvoie ce qui a changé.
    Sans effet si c'est déjà fait (le dossier du projet est réutilisé)."""
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
    """Appelé par python-for-android, dans le dossier du projet Android."""
    try:
        dist_dir = Path(toolchain._dist.dist_dir)
    except Exception:  # noqa: BLE001 — sinon : le dossier courant (c'est le même)
        dist_dir = Path.cwd()
    changed = add_lib_prefix(dist_dir)
    print("[APPCORE-PATCH] modules PySide6 préfixés « lib » :",
          ", ".join(changed) if changed else "rien à faire", flush=True)
    fixed = fix_missing_libs(dist_dir)
    print("[APPCORE-PATCH] liste des bibliothèques de Qt :",
          ", ".join(fixed) if fixed else "toutes présentes", flush=True)
    ordered = order_libs(dist_dir)
    print("[APPCORE-PATCH] ordre de chargement de Qt :",
          " | ".join(ordered) if ordered else "déjà dans l'ordre des dépendances", flush=True)
