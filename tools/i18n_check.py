"""Textes à traduire (socle et app), et ce qu'il manque dans chaque langue.

Outil de développement, pas utilisé par l'app. Depuis le dossier de l'app :

    python appcore/tools/i18n_check.py            # bilan de chaque langue de l'app
    python appcore/tools/i18n_check.py --list     # tous les textes de l'app, par fichier
    python appcore/tools/i18n_check.py --core     # bilan du socle seul (appcore/locales)

Les textes à traduire sont :
- ceux écrits dans tr(...), ntr(...) et N_(...) dans le code ;
- les noms des tableaux de données (gammes, accords, accordages, instruments…
  pour le socle ; ceux de l'app sont donnés par tools/i18n_data.py de l'app,
  une fonction texts(add)), lus directement dans les modules, sans avoir à les
  marquer un par un.

Les textes du socle se traduisent dans appcore/locales/<code>.py, ceux de
l'app dans locales/<code>.py. Pour chaque langue, le bilan donne les textes
manquants (affichés en anglais dans l'app), ceux qui ne servent plus, et les
traductions dont les champs {nom} ne correspondent pas à l'anglais.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import string
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent          # appcore/
CORE_ONLY = "--core" in sys.argv
ROOT = CORE.parent if CORE_ONLY else Path.cwd()        # le dossier de l'app
sys.path.insert(0, str(ROOT))
SKIP = {"symbol_font_data.py"}
CALLS = ("tr", "N_", "ntr")

Texts = dict[str, tuple[str, str | None]]   # texte -> (source, pluriel ou None)


def code_texts(folder: Path, prefix: str = "") -> Texts:
    """tr / ntr / N_ dans les fichiers .py d'un dossier (sans les sous-dossiers)."""
    found: Texts = {}
    for path in sorted(folder.glob("*.py")):
        if path.name in SKIP:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        source = prefix + path.name
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):   # i18n.tr(...)
                name = node.func.attr
            else:
                continue
            args = node.args
            if name in ("tr", "N_") and args and isinstance(args[0], ast.Constant) \
                    and isinstance(args[0].value, str):
                found.setdefault(args[0].value, (source, None))
            elif name == "ntr" and len(args) >= 2 and all(
                    isinstance(a, ast.Constant) and isinstance(a.value, str) for a in args[:2]):
                found[args[0].value] = (source, args[1].value)
    return found


def _adder(out: Texts):
    def add(source: str, *texts) -> None:
        for text in texts:
            if text:
                out.setdefault(text, (source, None))
    return add


def core_data_texts() -> Texts:
    """Noms des tableaux du socle."""
    from appcore import guitar_synth
    from appcore import music_theory as mt

    out: Texts = {}
    add = _adder(out)
    add("music_theory: scales", *mt.SCALES)
    add("music_theory: chords", *mt.CHORDS)
    add("music_theory: tunings", *mt.TUNINGS)
    add("music_theory: modes", *mt.MODES)
    add("instruments", *(label for label, _ in guitar_synth.VOICES.values()))
    return out


def app_data_texts() -> Texts:
    """Noms des tableaux de l'app : tools/i18n_data.py de l'app, fonction texts(add)."""
    path = ROOT / "tools" / "i18n_data.py"
    out: Texts = {}
    if not path.is_file():
        return out
    spec = importlib.util.spec_from_file_location("app_i18n_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.texts(_adder(out))
    return out


def core_texts() -> Texts:
    texts = core_data_texts()
    texts.update(code_texts(CORE, "appcore/"))
    return texts


def app_texts() -> Texts:
    texts = app_data_texts()
    texts.update(code_texts(ROOT))
    return texts


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def _catalog(module: str) -> dict | None:
    try:
        return importlib.import_module(module).T
    except ModuleNotFoundError:
        return None


def check(catalog: dict, texts: Texts, extra_used=()) -> tuple[list, list, list]:
    missing = [t for t in texts if t not in catalog]
    used = set(texts) | set(extra_used)
    unused = [t for t in catalog if t not in used]
    wrong = []
    for text, (_, plural) in texts.items():
        value = catalog.get(text)
        if value is None:
            continue
        if plural is not None:
            if not (isinstance(value, tuple) and len(value) == 2):
                wrong.append((text, "pluriel attendu : (singulier, pluriel)"))
                continue
            expected = _fields(text) | _fields(plural)
            for form in value:
                if _fields(form) - expected or not _fields(form) >= (_fields(text) - {"n"}):
                    wrong.append((text, f"champs {sorted(_fields(form))} ≠ {sorted(expected)}"))
        elif isinstance(value, tuple):
            wrong.append((text, "pas un pluriel"))
        elif _fields(value) != _fields(text):
            wrong.append((text, f"champs {sorted(_fields(value))} ≠ {sorted(_fields(text))}"))
    return missing, unused, wrong


def _report(label: str, total: int, missing, unused, wrong) -> bool:
    print(f"{label} : {total - len(missing)}/{total} traduits"
          + (f", {len(unused)} inutiles" if unused else "")
          + (f", {len(wrong)} à corriger" if wrong else ""))
    for text in missing[:15]:
        print(f"   manque : {text!r}")
    if len(missing) > 15:
        print(f"   … et {len(missing) - 15} autres")
    for text in unused[:5]:
        print(f"   inutile : {text!r}")
    if len(unused) > 5:
        print(f"   … et {len(unused) - 5} autres inutiles")
    for text, why in wrong:
        print(f"   ! {text!r} : {why}")
    return bool(missing or wrong)


def main() -> None:
    from appcore import i18n

    core = core_texts()
    if "--list" in sys.argv:
        texts = core if CORE_ONLY else {t: v for t, v in app_texts().items() if t not in core}
        by_source: dict[str, list[str]] = {}
        for text, (source, _) in texts.items():
            by_source.setdefault(source, []).append(text)
        for source in sorted(by_source):
            print(f"    # --- {source}")
            for text in by_source[source]:
                print(f"    {text!r}: '',")
        return
    status = 0
    codes = [c for c in i18n.ALL_LANGUAGES if c != "en"] if CORE_ONLY else \
        [c for c in i18n.LANGUAGES if c != "en"]
    print(f"Socle : {len(core)} textes")
    for code in codes:
        catalog = _catalog(f"appcore.locales.{code}")
        if catalog is None:
            print(f"  {code} : pas de fichier appcore/locales/{code}.py")
            status = 1
            continue
        status |= _report(f"  {code}", len(core), *check(catalog, core))
    if CORE_ONLY:
        sys.exit(status)

    import app_info
    own = {t: v for t, v in app_texts().items() if t not in core}
    print(f"{app_info.NAME} : {len(own)} textes (en plus de ceux du socle)")
    for code in codes:
        catalog = _catalog(f"locales.{code}")
        if catalog is None:
            print(f"  {code} : pas de fichier locales/{code}.py")
            status = 1
            continue
        # une entrée de l'app peut remplacer celle du socle (autre traduction) : utile
        status |= _report(f"  {code}", len(own), *check(catalog, own, extra_used=core))
    sys.exit(status)


if __name__ == "__main__":
    main()
