"""Texts to translate (base and app), and what is missing in each language.

Development tool, not used by the app. From the app's folder:

    python appcore/tools/i18n_check.py            # summary of each of the app's languages
    python appcore/tools/i18n_check.py --list     # all the app's texts, by file
    python appcore/tools/i18n_check.py --core     # summary of the base alone (appcore/locales)

The texts to translate are:
- those written in tr(...), ntr(...) and N_(...) in the code;
- the names in data tables (scales, chords, tunings, instruments…
  for the base; the app's are given by the app's tools/i18n_data.py,
  a texts(add) function), read directly from the modules, without having to
  mark them one by one.

The base's texts are translated in appcore/locales/<code>.py, the
app's in locales/<code>.py. For each language, the summary gives the missing
texts (shown in English in the app), those no longer used, and the
translations whose {name} fields do not match the English.
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
ROOT = CORE.parent if CORE_ONLY else Path.cwd()        # the app's folder
sys.path.insert(0, str(ROOT))
SKIP = {"symbol_font_data.py"}
CALLS = ("tr", "N_", "ntr")

Texts = dict[str, tuple[str, str | None]]   # text -> (source, plural or None)


def code_texts(folder: Path, prefix: str = "") -> Texts:
    """tr / ntr / N_ in the .py files of a folder (without subfolders)."""
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
    """Names in the base's tables."""
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
    """Names in the app's tables: the app's tools/i18n_data.py, texts(add) function."""
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
                    wrong.append((text, f"fields {sorted(_fields(form))} ≠ {sorted(expected)}"))
        elif isinstance(value, tuple):
            wrong.append((text, "not a plural"))
        elif _fields(value) != _fields(text):
            wrong.append((text, f"fields {sorted(_fields(value))} ≠ {sorted(_fields(text))}"))
    return missing, unused, wrong


def _report(label: str, total: int, missing, unused, wrong) -> bool:
    print(f"{label}: {total - len(missing)}/{total} translated"
          + (f", {len(unused)} unused" if unused else "")
          + (f", {len(wrong)} to fix" if wrong else ""))
    for text in missing[:15]:
        print(f"   missing: {text!r}")
    if len(missing) > 15:
        print(f"   … and {len(missing) - 15} more")
    for text in unused[:5]:
        print(f"   unused: {text!r}")
    if len(unused) > 5:
        print(f"   … and {len(unused) - 5} more unused")
    for text, why in wrong:
        print(f"   ! {text!r}: {why}")
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
    print(f"Base: {len(core)} texts")
    for code in codes:
        catalog = _catalog(f"appcore.locales.{code}")
        if catalog is None:
            print(f"  {code}: no appcore/locales/{code}.py file")
            status = 1
            continue
        status |= _report(f"  {code}", len(core), *check(catalog, core))
    if CORE_ONLY:
        sys.exit(status)

    import app_info
    own = {t: v for t, v in app_texts().items() if t not in core}
    print(f"{app_info.NAME}: {len(own)} texts (on top of the base's)")
    for code in codes:
        catalog = _catalog(f"locales.{code}")
        if catalog is None:
            print(f"  {code}: no locales/{code}.py file")
            status = 1
            continue
        # an app entry may replace the base's one (different translation): useful
        status |= _report(f"  {code}", len(own), *check(catalog, own, extra_used=core))
    sys.exit(status)


if __name__ == "__main__":
    main()
