"""Built-in symbols font: arrows, ♭ ♯, ▶ ◀, ♬, ✓, ✕, ★… on every phone.

On some phones, Android's font does not have all these symbols, and Qt
does not always find another font that has them: they showed as empty
boxes (seen in RiffFinder: keyboard ↶ ♬ ✕ ↗, chords "♭VII → I",
rhythms ↓ ↑…).

Two fonts, the DejaVu Sans symbols renamed (see tools/build_font.py):
- the app's, "<App> Symbols" (symbol_font_data.py at the app's root),
  with the symbols written in its code;
- the base's, "AppCore Symbols" (appcore/symbol_font_data.py), with the
  base's ones and the most common. An app without its own font works too.

install() loads them and sets them as fallbacks of the text font: text
keeps the phone's font, and each character it lacks is taken from the
app's font, then from the base's, before any system font.

How: QFont.insertSubstitution(text font, ours). Qt tries a font's
"substitutes", in order, for each missing character; this applies to
every font of the app derived from the text font
(labels, buttons, page drawings, drop-down lists…).
"""

from __future__ import annotations

import base64
import importlib
import zlib


def _sources() -> list:
    """The data modules: the app's (if it exists), then the base's."""
    found = []
    for name in ("symbol_font_data", "appcore.symbol_font_data"):
        try:
            module = importlib.import_module(name)
        except ImportError:
            continue
        if all(hasattr(module, attr) for attr in ("FAMILY", "REGULAR", "BOLD")) \
                and module.FAMILY not in [m.FAMILY for m in found]:
            found.append(module)
    return found


def families() -> list[str]:
    return [m.FAMILY for m in _sources()]


def chars() -> str:
    """All covered symbols (app + base)."""
    return "".join(sorted({c for m in _sources() for c in getattr(m, "CHARS", "")}))


def font_files(module) -> list[bytes]:
    """The two TTF files (regular, bold) of a data module."""
    return [zlib.decompress(base64.b64decode(face)) for face in (module.REGULAR, module.BOLD)]


def install(app) -> bool:
    """Call right after creating the QApplication, before any window.
    Returns False if no font could be loaded (the app works anyway,
    with the system fonts)."""
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QFont, QFontDatabase, QFontInfo

    loaded: list[str] = []
    for module in _sources():
        for ttf in font_files(module):
            font_id = QFontDatabase.addApplicationFontFromData(QByteArray(ttf))
            if font_id >= 0 and module.FAMILY in QFontDatabase.applicationFontFamilies(font_id) \
                    and module.FAMILY not in loaded:
                loaded.append(module.FAMILY)
    if not loaded:
        return False
    base = app.font()
    # The font really used for text ("Roboto" on Android), and not the
    # requested name, which can be an alias ("Sans Serif"): an alias
    # unknown to Qt would make our symbols the main font.
    text_family = QFontInfo(base).family()
    if not text_family or text_family in loaded:
        return False
    # + the requested name if it really exists: on Android, Qt's fonts
    # for lists, menus, tooltips… are called "Roboto"
    names = [text_family] + [name for name in base.families()
                             if name != text_family and name not in loaded
                             and QFontDatabase.hasFamily(name)]
    for name in names:
        for family in loaded:            # the app first, then the base
            QFont.insertSubstitution(name, family)
    font = QFont(base)              # same size; new font, without the previous cache
    font.setFamilies([text_family])
    app.setFont(font)
    return True
