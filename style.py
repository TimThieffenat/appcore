"""Thèmes des apps.

- light : blanc, rose et turquoise pastel, sobre.
- dark : noir et gris, accents néon.
- system (par défaut) : celui du téléphone ou de l'ordinateur, clair ou
  sombre, et l'app suit quand il change.

Chaque thème définit les couleurs de l'interface, celles du manche, de l'or
(étoiles, XP), de la flamme et de la glace, et celles des degrés (fill =
remplissage de la pastille, ink = couleur du texte coloré). Les dessins faits à
la main lisent current_palette(). Les tailles sont pensées pour un téléphone en
paysage (~850 × 390 dp) et restent confortables sur ordinateur.

Une app ajoute sa propre feuille de style (ses objets nommés : puces, gros
compteurs…) avec add_qss(), ou boot.run(pages, qss=...) : mêmes champs
{couleur} que ci-dessous, accolades doublées ({{ }}).
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

_BASE = """
QWidget {{ font-size: 14px; color: {text}; }}
QMainWindow, QStackedWidget, QWidget#page {{ background: {bg}; }}

/* Rail de navigation (icônes à gauche) */
QFrame#rail {{ background: {surface}; border: none; border-right: 1px solid {border}; }}
QToolButton#navButton {{
    background: transparent; color: {muted}; border: none; border-radius: 12px;
    padding: 1px 2px; font-size: 11px;
}}
QToolButton#navButton:hover {{ background: {hover}; color: {text}; }}
QToolButton#navButton:checked {{ background: {accent_soft}; color: {accent_text}; font-weight: 600; }}

/* Titres et textes */
QLabel#title {{ font-size: 18px; font-weight: 600; }}
QLabel#subtitle, QLabel#muted {{ color: {muted}; }}
QLabel#panelTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#accentLine {{ font-size: 15px; font-weight: 600; color: {accent_text}; }}

/* Boutons */
QPushButton {{
    background: {accent_soft}; color: {accent_text}; border: none;
    border-radius: 8px; padding: 7px 12px; font-weight: 600;
}}
QPushButton:hover {{ background: {accent_soft_hover}; }}

QFrame#segmentBar {{
    background: {surface}; border: 1px solid {border}; border-radius: 10px;
}}
QPushButton#segment {{
    background: transparent; color: {muted}; border: 1px solid transparent;
    border-radius: 7px; padding: 6px 12px;
}}
QPushButton#segment:hover {{ color: {text}; background: {hover}; }}
QPushButton#segment:checked {{
    background: {accent_soft}; color: {accent_text}; border-color: {seg_border};
}}

QPushButton#toggle {{
    background: {surface}; color: {muted}; border: 1px solid {border};
}}
QPushButton#toggle:hover {{ color: {text}; background: {hover}; }}
QPushButton#toggle:checked {{
    background: {pink_soft}; color: {pink_text}; border-color: {pink_border};
}}

QPushButton#flat {{ background: transparent; color: {pink_text}; padding: 4px 6px; }}

QPushButton#flat:hover {{ background: {pink_soft}; }}
QPushButton:disabled {{ background: {surface}; color: {border_strong}; border-color: {border}; }}

/* Panneaux (notes, règles, réglages) */
QFrame#sidePanel, QFrame#overlay {{
    background: {surface}; border: 1px solid {border}; border-radius: 12px;
}}
QFrame#sidePanel QLabel, QFrame#sidePanel QCheckBox,
QFrame#overlay QLabel, QFrame#overlay QCheckBox {{ background: transparent; }}

/* Champs */
QComboBox, QSpinBox, QLineEdit {{
    background: {input_bg}; border: 1px solid {border};
    border-radius: 8px; padding: 5px 8px; min-height: 22px;
}}
QSpinBox:hover, QSpinBox:focus,
QLineEdit:hover, QLineEdit:focus {{ border-color: {accent}; }}

/* Menus déroulants (touch_combo) : toute la case est le bouton, pas de flèche,
   pas de surbrillance qui reste ; la liste s'ouvre au centre, sur un voile. */
QComboBox {{ padding: 5px 10px; }}
QComboBox::drop-down {{ width: 0px; border: none; }}
QComboBox::down-arrow {{ image: none; width: 0px; height: 0px; }}
QComboBox:disabled {{ color: {muted}; }}
QFrame#choiceCard {{
    background: {surface}; border: 1px solid {border}; border-radius: 14px;
}}
QLabel#choiceRow {{
    background: transparent; border-radius: 9px; padding: 0 14px; font-size: 15px;
}}
QLabel#choiceRow[current="true"] {{
    background: {accent_soft}; color: {accent_text}; font-weight: 600;
}}
QLabel#choiceRow[pressed="true"] {{ background: {border}; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {border_strong}; background: {input_bg};
}}
QCheckBox::indicator:hover {{ border-color: {accent}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QCheckBox::indicator:disabled {{ background: {surface}; border-color: {border}; }}

QSlider::groove:horizontal {{ height: 6px; background: {border}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: {input_bg}; border: 2px solid {accent};
    width: 18px; height: 18px; margin: -8px 0; border-radius: 11px;
}}

/* Zones de défilement : le fond de la page passe au travers (sinon Android
   peint la zone visible en blanc, même en thème sombre) */
QScrollArea#strip, QScrollArea#plain {{ background: transparent; border: none; }}
QScrollArea#strip > QWidget#qt_scrollarea_viewport,
QScrollArea#plain > QWidget#qt_scrollarea_viewport {{ background: transparent; }}
QWidget#stripContent {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0; }}
QScrollBar::handle {{ background: {border_strong}; border-radius: 4px; }}
QScrollBar::handle:vertical {{ min-height: 30px; }}
QScrollBar::handle:horizontal {{ min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* Gros bouton Lecture / Stop */
QPushButton#primary, QPushButton#primaryStop {{
    font-size: 16px; padding: 10px 28px; border-radius: 10px;
}}
QPushButton#primary {{ background: {accent_soft}; color: {accent_text}; border: 1px solid {seg_border}; }}
QPushButton#primary:hover {{ background: {accent_soft_hover}; }}
QPushButton#primaryStop {{ background: {pink_soft}; color: {pink_text}; border: 1px solid {pink_border}; }}

QToolTip {{
    background: {surface}; color: {text}; border: 1px solid {border};
    padding: 5px 8px;
}}
"""

THEMES = {
    "light": dict(
        # Interface
        bg="#ffffff", surface="#fbf8f9", hover="#f5eef1",
        text="#2a2c33", muted="#737782",
        border="#ece4e8", border_strong="#d4cbd0", input_bg="#ffffff",
        accent="#4cbfb3", accent_soft="#dcf4f1", accent_soft_hover="#c8ede8",
        accent_text="#1c766d", seg_border="transparent",
        pink_soft="#fdecf2", pink_text="#b4446b", pink_border="#f5c6d5",
        own_soft="#f1edfd", own_text="#6550c2", own_border="#d8cff7",
        gold="#d99a1e", gold_soft="#fdf3dc", flame="#f0743c", ice="#5aa9e6",
        # Manche
        board="#fbf8f9", board_border="#ece4e8", fret="#ddd5d9",
        nut="#c9c0c5", string="#b9b2b7", inlay="#f6d9e3",
        # Pastilles : remplissage pastel, texte foncé
        dots="pastel", dot_text="#2a2c33",
        degrees={
            1: ("#f5a8bf", "#b8436a"),  # tonique : rose
            3: ("#8fdcd1", "#1a7a70"),  # tierce : turquoise
            5: ("#c8bbf3", "#6550c2"),  # quinte : lavande
            7: ("#f8cba2", "#a85a14"),  # septième : pêche
            2: ("#acd2f6", "#2c6db3"),  # seconde / 9 : bleu ciel
            4: ("#c3e7b5", "#3d7f2f"),  # quarte / 11 : menthe
            6: ("#f3e29a", "#86690a"),  # sixte / 13 : vanille
        },
    ),
    "dark": dict(
        # Interface
        bg="#0a0a0c", surface="#131317", hover="#1c1c22",
        text="#e9e9ef", muted="#8a8a96",
        border="#25252c", border_strong="#3a3a44", input_bg="#16161b",
        accent="#14f1d9", accent_soft="#10292a", accent_soft_hover="#153637",
        accent_text="#14f1d9", seg_border="#14f1d9",
        pink_soft="#2a1220", pink_text="#ff5cb3", pink_border="#ff3ea5",
        own_soft="#1d1530", own_text="#b585ff", own_border="#a970ff",
        gold="#ffd23f", gold_soft="#2a2410", flame="#ff7a1a", ice="#5ac8ff",
        # Manche
        board="#121216", board_border="#24242b", fret="#30303a",
        nut="#4a4a55", string="#5c5c68", inlay="#24242c",
        # Pastilles : contour et texte néon sur fond noir, avec halo
        dots="neon", dot_text="#0a0a0c",
        degrees={
            1: ("#ff3ea5", "#ff3ea5"),  # tonique : rose néon
            3: ("#14f1d9", "#14f1d9"),  # tierce : turquoise néon
            5: ("#a970ff", "#b585ff"),  # quinte : violet
            7: ("#ff9f1a", "#ff9f1a"),  # septième : orange
            2: ("#3d9bff", "#5aabff"),  # seconde / 9 : bleu
            4: ("#a6ff3d", "#a6ff3d"),  # quarte / 11 : vert acide
            6: ("#ffe347", "#ffe347"),  # sixte / 13 : jaune
        },
    ),
}

# Anciens noms de thèmes (version française) -> nouveaux noms
_ALIASES = {"clair": "light", "sombre": "dark"}

SYSTEM = "system"          # réglage par défaut : le thème du téléphone
_current = "light"         # thème affiché (jamais « system »)
_choice = SYSTEM           # réglage choisi
_style_applied = False
_following = False
_extra_qss: list[str] = []   # feuilles de style ajoutées par l'app (add_qss)
_app = None                  # l'application, une fois le thème appliqué


def add_qss(text: str) -> None:
    """Ajoute une feuille de style de l'app (champs {couleur} du thème,
    accolades doublées). Si le thème est déjà affiché, elle s'applique aussitôt."""
    if text and text not in _extra_qss:
        _extra_qss.append(text)
        if _app is not None:
            apply_theme(_app, _choice)


def stylesheet(palette: dict) -> str:
    """La feuille de style complète (socle + app) aux couleurs de `palette`."""
    return "".join(part.format(**palette) for part in [_BASE, *_extra_qss])


def theme_choice(name) -> str:
    """Le réglage : « system », « light » ou « dark » (inconnu : « system »)."""
    name = _ALIASES.get(name, name)
    return name if name in THEMES or name == SYSTEM else SYSTEM


def system_is_dark() -> bool:
    """Le téléphone (ou l'ordinateur) est-il en mode sombre ? Qt 6.5 et plus ;
    si on ne peut pas le savoir : clair."""
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except (AttributeError, RuntimeError):
        return False


def theme_name(name) -> str:
    """Le thème à afficher pour ce réglage : « light » ou « dark »."""
    choice = theme_choice(name)
    if choice == SYSTEM:
        return "dark" if system_is_dark() else "light"
    return choice


def current_palette() -> dict:
    return THEMES[_current]


def degree_colors(family: int) -> tuple[str, str]:
    """(remplissage, encre) pour une famille de degré (1 à 7)."""
    return THEMES[_current]["degrees"][family]


def _qt_palette(c: dict) -> QPalette:
    """Palette Qt aux couleurs du thème.

    La feuille de style ne couvre pas tout : sur Android, les zones qu'elle
    oublie (intérieur des zones de défilement, listes déroulantes…) prennent
    la palette du système, claire. Avec cette palette, tout suit le thème.
    """
    role = QPalette.ColorRole
    colors = {
        role.Window: c["bg"], role.WindowText: c["text"],
        role.Base: c["input_bg"], role.AlternateBase: c["surface"],
        role.Text: c["text"], role.PlaceholderText: c["muted"],
        role.Button: c["surface"], role.ButtonText: c["text"],
        role.ToolTipBase: c["surface"], role.ToolTipText: c["text"],
        role.Highlight: c["accent_soft"], role.HighlightedText: c["accent_text"],
        role.BrightText: c["pink_text"], role.Link: c["accent_text"],
        role.Light: c["hover"], role.Midlight: c["surface"], role.Mid: c["border"],
        role.Dark: c["border_strong"], role.Shadow: c["border_strong"],
    }
    palette = QPalette()
    for color_role, color in colors.items():
        palette.setColor(QPalette.ColorGroup.All, color_role, QColor(color))
    for color_role in (role.WindowText, role.Text, role.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, color_role, QColor(c["border_strong"]))
    return palette


def apply_theme(app: QApplication, name: object) -> None:
    """Applique le réglage `name` (« system », « light » ou « dark »)."""
    global _current, _choice, _app
    _app = app
    _choice = theme_choice(name)
    _current = theme_name(_choice)
    palette = {k: v for k, v in THEMES[_current].items() if isinstance(v, str)}
    # « Fusion » : le même dessin des contrôles sur Android, Windows et Linux
    # (le style natif d'Android ignore une partie des couleurs du thème).
    global _style_applied
    if not _style_applied:
        app.setStyle("Fusion")
        _style_applied = True
    app.setPalette(_qt_palette(palette))
    app.setStyleSheet(stylesheet(palette))


def follow_system(app: QApplication, on_change=None) -> None:
    """Quand le téléphone passe en sombre ou en clair pendant que l'app est
    ouverte, l'app suit (si le réglage est « system »). `on_change` est appelé
    après coup, pour redessiner ce qui est peint à la main (manche…)."""
    global _following
    if _following:
        return
    try:
        signal = QGuiApplication.styleHints().colorSchemeChanged
    except AttributeError:   # Qt trop ancien : le thème suit au prochain lancement
        return
    _following = True

    def refresh(*_) -> None:
        if _choice != SYSTEM or theme_name(SYSTEM) == _current:
            return
        apply_theme(app, SYSTEM)
        if on_change is not None:
            on_change()

    # après Qt, qui met aussi à jour ses propres couleurs à ce moment-là
    signal.connect(lambda *_: QTimer.singleShot(0, refresh))
