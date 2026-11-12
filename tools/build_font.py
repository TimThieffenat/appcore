"""Builds the symbols font built into the app (symbol_font_data.py file).

Development tool (needs fontTools: pip install fonttools), not
used by the app. From the app's folder:

    python appcore/tools/build_font.py [DejaVuSans.ttf DejaVuSans-Bold.ttf]

writes symbol_font_data.py ("<NAME> Symbols" font, with the symbols of the
app's code) and thirdparty/fonts/LICENSE-DejaVu.txt. With --core (from
anywhere): the base's font, appcore/symbol_font_data.py ("AppCore
Symbols", the base's symbols + EXTRA), which every app loads as a fallback.

Without paths: those of Debian / Ubuntu (fonts-dejavu-core package). Otherwise, the
two files from https://dejavu-fonts.github.io (ttf/ folder of the archive).

Why: the arrows, ♭ ♯, ▶ ◀, ♬, ✓, ✕… the app shows are not in
every phone's font, and Qt does not always find a fallback font
on Android: they showed as empty boxes. The app therefore ships
its symbols, taken from DejaVu Sans (regular and bold):

- only the useful characters: all the symbols written in the app's
  code (found automatically, see used_symbols) and a few other
  common ones (EXTRA), for a few dozen KB instead of 1.4 MB;
- renamed "<App> Symbols", as its licence requires for a modified
  font; the copyright notices and the licence stay in the font
  and are copied into symbol_font_data.py and thirdparty/fonts/.

Run again when the app shows a new symbol (the coverage test
reports it), then ship symbol_font_data.py with the rest.
"""

from __future__ import annotations

import ast
import base64
import io
import sys
import textwrap
import unicodedata
import zlib
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

CORE = Path(__file__).resolve().parent.parent      # the appcore/ folder
CORE_MODE = "--core" in sys.argv
ROOT = CORE if CORE_MODE else Path.cwd()           # the app's folder (or the base's)
DEFAULT_FONTS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
OUTPUT = ROOT / "symbol_font_data.py"
LICENSE_FILE = (ROOT / "LICENSE-DejaVu.txt") if CORE_MODE else \
    (ROOT / "thirdparty" / "fonts" / "LICENSE-DejaVu.txt")
# Files not to scan: generated data, third-party libraries
SKIP = {"symbol_font_data.py"}


def _app_name() -> str:
    if CORE_MODE:
        return "AppCore"
    sys.path.insert(0, str(ROOT))
    try:
        import app_info
    except ImportError:
        raise SystemExit("app_info.py not found: run from the app's folder "
                         "(or --core for the base's font)") from None
    return app_info.NAME


APP = _app_name()
FAMILY = f"{APP} Symbols"

# Common symbols on top of those in the code: for a song name, a
# future feature… without having to rebuild the font.
EXTRA = (" ¡¢£¥§©®±²³¹¼½¾¿÷øØ°·×«»"
         "‐‑‒–—―‘’‚“”„†‡•…‰‹›⁄′″   "
         "−≈≠≤≥∞√∆"
         "←↑→↓↔↕↖↗↘↙↶↷↺↻⇐⇒⇄⇅"
         "■□▪▫▬▲△▶▷▸▼▽◀◁◂◆◇○◎●◐◑★☆"
         "♩♪♫♬♭♮♯"
         "✓✔✕✖✗✘✚✎✏✂⌫⏎⌘")


def _docstrings(tree: ast.AST) -> set[int]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                found.add(id(body[0].value))
    return found


def is_symbol(char: str) -> bool:
    """Character the phone's font may not have: anything that is
    neither ASCII nor a letter (accented letters, it has)."""
    return ord(char) > 127 and not unicodedata.category(char).startswith(("L", "M", "C"))


def used_symbols(root: Path = ROOT) -> dict[str, set[str]]:
    """Symbols written in the app's texts (not in comments or
    docstrings) -> files where they appear."""
    found: dict[str, set[str]] = {}
    # the code and its translations (locales/); for an app, without the base
    # (its symbols are in the base's font, loaded as a fallback)
    for path in sorted(root.glob("*.py")) + sorted(root.glob("locales/*.py")):
        if path.name in SKIP:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docs = _docstrings(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                for char in node.value:
                    if is_symbol(char):
                        found.setdefault(char, set()).add(path.name)
    return found


def _rename(font: TTFont, style: str) -> None:
    """New name (required by the licence); copyright, trademark and licence kept."""
    name = font["name"]
    version = name.getDebugName(5) or ""
    full = FAMILY if style == "Regular" else f"{FAMILY} {style}"
    postscript = FAMILY.replace(" ", "") + "-" + style
    for name_id in (1, 2, 3, 4, 6, 16, 17):
        name.removeNames(nameID=name_id)
    values = {1: FAMILY, 2: style, 3: f"{full}; {version}", 4: full, 6: postscript,
              16: FAMILY, 17: style,
              10: "Symbols of DejaVu Sans (https://dejavu-fonts.github.io), "
                  f"subset and renamed for {APP} as its license requires."}
    for name_id, value in values.items():
        name.setName(value, name_id, 3, 1, 0x409)   # Windows, Unicode, English
        name.setName(value, name_id, 1, 0, 0)       # Mac, Roman
    if style == "Regular":
        font["OS/2"].fsSelection = (font["OS/2"].fsSelection | 0x40) & ~0x21   # REGULAR


def build_face(source: str, chars: str, style: str) -> bytes:
    font = TTFont(source, recalcTimestamp=False)   # the same result every time
    missing = [c for c in chars if ord(c) not in font.getBestCmap()]
    if missing:
        raise SystemExit(f"{Path(source).name} lacks: {' '.join(missing)} "
                         "— choose another character in the app or remove it from EXTRA.")
    options = subset.Options()
    options.name_IDs = ["*"]           # keeps copyright (0), trademark (7), licence (13, 14)
    options.name_languages = ["*"]
    options.layout_features = []       # no ligatures or kerning for symbols
    options.drop_tables += ["FFTM", "MATH", "kern"]
    options.notdef_outline = True
    options.recalc_bounds = True
    sub = subset.Subsetter(options)
    sub.populate(unicodes=sorted({ord(c) for c in chars}))
    sub.subset(font)
    _rename(font, style)
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def _literal(data: bytes, width: int = 88) -> str:
    text = base64.b64encode(zlib.compress(data, 9)).decode("ascii")
    lines = textwrap.wrap(text, width)
    return "(\n" + "".join(f'    "{line}"\n' for line in lines) + ")"


def main() -> None:
    sources = [a for a in sys.argv[1:] if a != "--core"] or list(DEFAULT_FONTS)
    if len(sources) != 2:
        raise SystemExit(__doc__)
    used = used_symbols()
    chars = "".join(sorted(set(used) | set(EXTRA)))
    regular = build_face(sources[0], chars, "Regular")
    bold = build_face(sources[1], chars, "Bold")
    license_text = TTFont(sources[0])["name"].getDebugName(13).strip() + "\n"
    license_text = "\n".join(line.rstrip() for line in license_text.split("\n"))
    assert '"""' not in license_text and "\\" not in license_text
    version = TTFont(sources[0])["name"].getDebugName(5)

    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(
        f"{FAMILY} (symbol_font_data.py) is a subset of DejaVu Sans {version}\n"
        f"(https://dejavu-fonts.github.io), renamed as required below.\n\n"
        + license_text, encoding="utf-8")
    body = (
        f'"""The "{FAMILY}" font built into the app (see appcore/symbol_font.py).\n\n'
        "GENERATED by appcore/tools/build_font.py: do not edit by hand.\n\n"
        f"The symbols of DejaVu Sans {version.removeprefix('Version ')} (regular and bold), "
        f"{len(chars)} characters,\n"
        "renamed as their licence requires (full text in LICENSE below\n"
        f'and in {LICENSE_FILE.relative_to(ROOT).as_posix()}). Compressed TTF files (zlib, base64).\n"""\n'
        "# Generated file (data, original licence as is): no style check\n"
        "# ruff: noqa: E501\n# flake8: noqa\n\n"
        f"FAMILY = {FAMILY!r}\n"
        f"CHARS = {chars!r}\n\n"
        f"REGULAR = {_literal(regular)}\n\n"
        f"BOLD = {_literal(bold)}\n\n"
        f'LICENSE = """\\\n{license_text}"""\n')
    OUTPUT.write_text(body, encoding="utf-8")
    print(f"{OUTPUT.name}: {len(chars)} characters, regular {len(regular) // 1024} KB, "
          f"bold {len(bold) // 1024} KB (file {OUTPUT.stat().st_size // 1024} KB)")
    print("Symbols in the code:", " ".join(sorted(used)))


if __name__ == "__main__":
    main()
