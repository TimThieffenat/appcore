"""Police de symboles intégrée : flèches, ♭ ♯, ▶ ◀, ♬, ✓, ✕, ★… sur tous les téléphones.

Sur certains téléphones, la police d'Android n'a pas tous ces symboles, et Qt
ne trouve pas toujours une autre police qui les a : ils s'affichaient en
carrés vides (constaté dans RiffFinder : clavier ↶ ♬ ✕ ↗, accords « ♭VII → I »,
rythmes ↓ ↑…).

Deux polices, les symboles de DejaVu Sans renommés (voir tools/build_font.py) :
- celle de l'app, « <App> Symbols » (symbol_font_data.py à la racine de l'app),
  avec les symboles écrits dans son code ;
- celle du socle, « AppCore Symbols » (appcore/symbol_font_data.py), avec ceux
  du socle et les plus courants. Une app sans police à elle marche donc aussi.

install() les charge et les place en secours de la police du texte : le texte
garde la police du téléphone, et chaque caractère qu'elle n'a pas est pris dans
la police de l'app, puis dans celle du socle, avant toute police du système.

Comment : QFont.insertSubstitution(police du texte, la nôtre). Qt essaie les
« substituts » d'une police, dans l'ordre, pour chaque caractère manquant ;
cela vaut pour toutes les polices de l'app qui partent de celle du texte
(étiquettes, boutons, dessins des pages, listes déroulantes…).
"""

from __future__ import annotations

import base64
import importlib
import zlib


def _sources() -> list:
    """Les modules de données : celui de l'app (s'il existe), puis celui du socle."""
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
    """Tous les symboles couverts (app + socle)."""
    return "".join(sorted({c for m in _sources() for c in getattr(m, "CHARS", "")}))


def font_files(module) -> list[bytes]:
    """Les deux fichiers TTF (normale, grasse) d'un module de données."""
    return [zlib.decompress(base64.b64decode(face)) for face in (module.REGULAR, module.BOLD)]


def install(app) -> bool:
    """À appeler juste après avoir créé la QApplication, avant toute fenêtre.
    Renvoie False si aucune police n'a pu être chargée (l'app marche quand
    même, avec les polices du système)."""
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
    # La police réellement utilisée pour le texte (« Roboto » sur Android), et
    # non le nom demandé, qui peut être un alias (« Sans Serif ») : un alias
    # inconnu de Qt ferait de nos symboles la police principale.
    text_family = QFontInfo(base).family()
    if not text_family or text_family in loaded:
        return False
    # + le nom demandé s'il existe vraiment : sur Android, les polices de Qt
    # pour les listes, menus, bulles d'aide… s'appellent « Roboto »
    names = [text_family] + [name for name in base.families()
                             if name != text_family and name not in loaded
                             and QFontDatabase.hasFamily(name)]
    for name in names:
        for family in loaded:            # l'app d'abord, puis le socle
            QFont.insertSubstitution(name, family)
    font = QFont(base)              # même taille ; nouvelle police, sans cache d'avant
    font.setFamilies([text_family])
    app.setFont(font)
    return True
