"""The apps' themes.

- light: white, pastel pink and turquoise, understated.
- dark: black and grey, neon accents.
- system (default): the phone's or computer's, light or
  dark, and the app follows when it changes.

Each theme defines the interface colours, those of the neck, gold
(stars, XP), flame and ice, and those of the degrees (fill =
the dot's fill, ink = colour of coloured text). Hand-drawn widgets
read current_palette(). Sizes are designed for a phone in
landscape (~850 × 390 dp) and stay comfortable on desktop.

An app adds its own style sheet (its named objects: chips, big
counters…) with add_qss(), or boot.run(pages, qss=...): same
{colour} fields as below, doubled braces ({{ }}).
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

_BASE = """
QWidget {{ font-size: 14px; color: {text}; }}
QMainWindow, QStackedWidget, QWidget#page {{ background: {bg}; }}

/* Navigation rail (icons on the left) */
QFrame#rail {{ background: {surface}; border: none; border-right: 1px solid {border}; }}
QToolButton#navButton {{
    background: transparent; color: {muted}; border: none; border-radius: 12px;
    padding: 1px 2px; font-size: 11px;
}}
QToolButton#navButton:hover {{ background: {hover}; color: {text}; }}
QToolButton#navButton:checked {{ background: {accent_soft}; color: {accent_text}; font-weight: 600; }}

/* Titles and texts */
QLabel#title {{ font-size: 18px; font-weight: 600; }}
QLabel#subtitle, QLabel#muted {{ color: {muted}; }}
QLabel#panelTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#accentLine {{ font-size: 15px; font-weight: 600; color: {accent_text}; }}

/* Buttons */
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

/* Panels (notes, rules, settings) */
QFrame#sidePanel, QFrame#overlay {{
    background: {surface}; border: 1px solid {border}; border-radius: 12px;
}}
QFrame#sidePanel QLabel, QFrame#sidePanel QCheckBox,
QFrame#overlay QLabel, QFrame#overlay QCheckBox {{ background: transparent; }}

/* Fields */
QComboBox, QSpinBox, QLineEdit {{
    background: {input_bg}; border: 1px solid {border};
    border-radius: 8px; padding: 5px 8px; min-height: 22px;
}}
QSpinBox:hover, QSpinBox:focus,
QLineEdit:hover, QLineEdit:focus {{ border-color: {accent}; }}

/* Drop-down menus (touch_combo): the whole box is the button, no arrow,
   no lingering highlight; the list opens in the centre, over a veil. */
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

/* Scroll areas: the page background shows through (otherwise Android
   paints the visible area white, even in the dark theme) */
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

/* Big Play / Stop button */
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
        # Neck
        board="#fbf8f9", board_border="#ece4e8", fret="#ddd5d9",
        nut="#c9c0c5", string="#b9b2b7", inlay="#f6d9e3",
        # Dots: pastel fill, dark text
        dots="pastel", dot_text="#2a2c33",
        degrees={
            1: ("#f5a8bf", "#b8436a"),  # root: pink
            3: ("#8fdcd1", "#1a7a70"),  # third: turquoise
            5: ("#c8bbf3", "#6550c2"),  # fifth: lavender
            7: ("#f8cba2", "#a85a14"),  # seventh: peach
            2: ("#acd2f6", "#2c6db3"),  # second / 9: sky blue
            4: ("#c3e7b5", "#3d7f2f"),  # fourth / 11: mint
            6: ("#f3e29a", "#86690a"),  # sixth / 13: vanilla
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
        # Neck
        board="#121216", board_border="#24242b", fret="#30303a",
        nut="#4a4a55", string="#5c5c68", inlay="#24242c",
        # Dots: neon outline and text on black, with a glow
        dots="neon", dot_text="#0a0a0c",
        degrees={
            1: ("#ff3ea5", "#ff3ea5"),  # root: neon pink
            3: ("#14f1d9", "#14f1d9"),  # third: neon turquoise
            5: ("#a970ff", "#b585ff"),  # fifth: violet
            7: ("#ff9f1a", "#ff9f1a"),  # seventh: orange
            2: ("#3d9bff", "#5aabff"),  # second / 9: blue
            4: ("#a6ff3d", "#a6ff3d"),  # fourth / 11: acid green
            6: ("#ffe347", "#ffe347"),  # sixth / 13: yellow
        },
    ),
}

# Former theme names (French version) -> new names
_ALIASES = {"clair": "light", "sombre": "dark"}

SYSTEM = "system"          # default setting: the phone's theme
_current = "light"         # theme shown (never "system")
_choice = SYSTEM           # chosen setting
_style_applied = False
_following = False
_extra_qss: list[str] = []   # style sheets added by the app (add_qss)
_app = None                  # the application, once the theme is applied


def add_qss(text: str) -> None:
    """Adds a style sheet of the app ({colour} fields of the theme,
    doubled braces). If the theme is already shown, it applies at once."""
    if text and text not in _extra_qss:
        _extra_qss.append(text)
        if _app is not None:
            apply_theme(_app, _choice)


def stylesheet(palette: dict) -> str:
    """The full style sheet (base + app) in the colours of `palette`."""
    return "".join(part.format(**palette) for part in [_BASE, *_extra_qss])


def theme_choice(name) -> str:
    """The setting: "system", "light" or "dark" (unknown: "system")."""
    name = _ALIASES.get(name, name)
    return name if name in THEMES or name == SYSTEM else SYSTEM


def system_is_dark() -> bool:
    """Is the phone (or computer) in dark mode? Qt 6.5 and later;
    if it cannot be known: light."""
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except (AttributeError, RuntimeError):
        return False


def theme_name(name) -> str:
    """The theme shown for this setting: "light" or "dark"."""
    choice = theme_choice(name)
    if choice == SYSTEM:
        return "dark" if system_is_dark() else "light"
    return choice


def current_palette() -> dict:
    return THEMES[_current]


def degree_colors(family: int) -> tuple[str, str]:
    """(fill, ink) for a degree family (1 to 7)."""
    return THEMES[_current]["degrees"][family]


def _qt_palette(c: dict) -> QPalette:
    """Qt palette in the theme's colours.

    The style sheet does not cover everything: on Android, the areas it
    misses (inside scroll areas, drop-down lists…) take the system
    palette, which is light. With this palette, everything follows the theme.
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
    """Applies the setting `name` ("system", "light" or "dark")."""
    global _current, _choice, _app
    _app = app
    _choice = theme_choice(name)
    _current = theme_name(_choice)
    palette = {k: v for k, v in THEMES[_current].items() if isinstance(v, str)}
    # "Fusion": the same drawing of controls on Android, Windows and Linux
    # (Android's native style ignores some of the theme's colours).
    global _style_applied
    if not _style_applied:
        app.setStyle("Fusion")
        _style_applied = True
    app.setPalette(_qt_palette(palette))
    app.setStyleSheet(stylesheet(palette))


def follow_system(app: QApplication, on_change=None) -> None:
    """When the phone switches to dark or light while the app is
    open, the app follows (if the setting is "system"). `on_change` is called
    afterwards, to redraw what is painted by hand (neck…)."""
    global _following
    if _following:
        return
    try:
        signal = QGuiApplication.styleHints().colorSchemeChanged
    except AttributeError:   # Qt too old: the theme follows at the next start
        return
    _following = True

    def refresh(*_) -> None:
        if _choice != SYSTEM or theme_name(SYSTEM) == _current:
            return
        apply_theme(app, SYSTEM)
        if on_change is not None:
            on_change()

    # after Qt, which also updates its own colours at that moment
    signal.connect(lambda *_: QTimer.singleShot(0, refresh))
