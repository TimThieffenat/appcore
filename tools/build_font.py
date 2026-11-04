"""Fabrique la police de symboles intégrée à l'app (fichier symbol_font_data.py).

Outil de développement (fontTools nécessaire : pip install fonttools), pas
utilisé par l'app. Depuis le dossier de l'app :

    python appcore/tools/build_font.py [DejaVuSans.ttf DejaVuSans-Bold.ttf]

écrit symbol_font_data.py (police « <NAME> Symbols », avec les symboles du code
de l'app) et thirdparty/fonts/LICENSE-DejaVu.txt. Avec --core (depuis
n'importe où) : la police du socle, appcore/symbol_font_data.py (« AppCore
Symbols », symboles du socle + EXTRA), que toutes les apps chargent en secours.

Sans chemins : ceux de Debian / Ubuntu (paquet fonts-dejavu-core). Sinon, les
deux fichiers de https://dejavu-fonts.github.io (dossier ttf/ de l'archive).

Pourquoi : les flèches, ♭ ♯, ▶ ◀, ♬, ✓, ✕… que l'app affiche ne sont pas dans
la police de tous les téléphones, et Qt ne trouve pas toujours une police de
secours sur Android : ils s'affichaient en carrés vides. L'app embarque donc
ses symboles, pris dans DejaVu Sans (normale et grasse) :

- seulement les caractères utiles : tous les symboles écrits dans le code de
  l'app (relevés automatiquement, voir used_symbols) et quelques autres
  courants (EXTRA), pour quelques dizaines de Ko au lieu de 1,4 Mo ;
- renommée « <App> Symbols », comme l'exige sa licence pour une police
  modifiée ; les mentions de copyright et la licence restent dans la police
  et sont recopiées dans symbol_font_data.py et thirdparty/fonts/.

À relancer quand l'app affiche un nouveau symbole (le test de couverture le
signale), puis copier symbol_font_data.py avec le reste.
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

CORE = Path(__file__).resolve().parent.parent      # le dossier appcore/
CORE_MODE = "--core" in sys.argv
ROOT = CORE if CORE_MODE else Path.cwd()           # le dossier de l'app (ou du socle)
DEFAULT_FONTS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
OUTPUT = ROOT / "symbol_font_data.py"
LICENSE_FILE = (ROOT / "LICENSE-DejaVu.txt") if CORE_MODE else \
    (ROOT / "thirdparty" / "fonts" / "LICENSE-DejaVu.txt")
# Fichiers à ne pas relever : données générées, bibliothèques tierces
SKIP = {"symbol_font_data.py"}


def _app_name() -> str:
    if CORE_MODE:
        return "AppCore"
    sys.path.insert(0, str(ROOT))
    try:
        import app_info
    except ImportError:
        raise SystemExit("app_info.py introuvable : lancer depuis le dossier de l'app "
                         "(ou --core pour la police du socle)") from None
    return app_info.NAME


APP = _app_name()
FAMILY = f"{APP} Symbols"

# Symboles courants en plus de ceux du code : pour un nom de morceau, une
# future fonction… sans avoir à refaire la police.
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
    """Caractère que la police du téléphone n'a peut-être pas : tout ce qui
    n'est ni ASCII ni une lettre (les lettres accentuées, elle les a)."""
    return ord(char) > 127 and not unicodedata.category(char).startswith(("L", "M", "C"))


def used_symbols(root: Path = ROOT) -> dict[str, set[str]]:
    """Symboles écrits dans les textes de l'app (pas dans les commentaires ni
    les docstrings) -> fichiers où ils apparaissent."""
    found: dict[str, set[str]] = {}
    # le code et ses traductions (locales/) ; pour une app, sans le socle
    # (ses symboles sont dans la police du socle, chargée en secours)
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
    """Nouveau nom (exigé par la licence) ; copyright, marque et licence gardés."""
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
        name.setName(value, name_id, 3, 1, 0x409)   # Windows, Unicode, anglais
        name.setName(value, name_id, 1, 0, 0)       # Mac, Roman
    if style == "Regular":
        font["OS/2"].fsSelection = (font["OS/2"].fsSelection | 0x40) & ~0x21   # REGULAR


def build_face(source: str, chars: str, style: str) -> bytes:
    font = TTFont(source, recalcTimestamp=False)   # même résultat à chaque fois
    missing = [c for c in chars if ord(c) not in font.getBestCmap()]
    if missing:
        raise SystemExit(f"{Path(source).name} n'a pas : {' '.join(missing)} "
                         "— choisir un autre caractère dans l'app ou l'enlever de EXTRA.")
    options = subset.Options()
    options.name_IDs = ["*"]           # garde copyright (0), marque (7), licence (13, 14)
    options.name_languages = ["*"]
    options.layout_features = []       # pas de ligatures ni de crénage pour des symboles
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
        f'"""Police « {FAMILY} » intégrée à l\'app (voir appcore/symbol_font.py).\n\n'
        "GÉNÉRÉ par appcore/tools/build_font.py : ne pas modifier à la main.\n\n"
        f"Les symboles de DejaVu Sans {version.removeprefix('Version ')} (normale et grasse), "
        f"{len(chars)} caractères,\n"
        "renommés comme l'exige leur licence (texte complet dans LICENSE ci-dessous\n"
        f'et dans {LICENSE_FILE.relative_to(ROOT).as_posix()}). Fichiers TTF compressés (zlib, base64).\n"""\n'
        "# Fichier généré (données, licence d'origine telle quelle) : pas de vérification de style\n"
        "# ruff: noqa: E501\n# flake8: noqa\n\n"
        f"FAMILY = {FAMILY!r}\n"
        f"CHARS = {chars!r}\n\n"
        f"REGULAR = {_literal(regular)}\n\n"
        f"BOLD = {_literal(bold)}\n\n"
        f'LICENSE = """\\\n{license_text}"""\n')
    OUTPUT.write_text(body, encoding="utf-8")
    print(f"{OUTPUT.name} : {len(chars)} caractères, normale {len(regular) // 1024} Ko, "
          f"grasse {len(bold) // 1024} Ko (fichier {OUTPUT.stat().st_size // 1024} Ko)")
    print("Symboles du code :", " ".join(sorted(used)))


if __name__ == "__main__":
    main()
