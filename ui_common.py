"""Petits outils d'interface partagés par les pages (format téléphone).

Une app peut compléter ce module dans son propre ui_common.py
(`from appcore.ui_common import *` puis ses outils à elle : capo, accordage…).
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QScroller,
    QSizePolicy,
    QWidget,
)

from appcore import i18n
from appcore import music_theory as mt
from appcore.i18n import tr
from appcore.touch_combo import TouchComboBox
from appcore.touch_input import TouchLineEdit, TouchSpinBox


def is_android() -> bool:
    return QGuiApplication.platformName() == "android"


def enable_touch_scroll(area: QAbstractScrollArea) -> None:
    """Défilement au doigt (avec inertie) sur Android."""
    if is_android():
        QScroller.grabGesture(area.viewport(),
                              QScroller.ScrollerGestureType.LeftMouseButtonGesture)


def notation(settings: QSettings) -> str:
    """Noms des notes : le réglage, sinon Do Ré Mi dans les langues où c'est
    l'usage (français, espagnol, italien, portugais), C D E ailleurs."""
    value = settings.value("notation")
    if value is None or value == "":
        return "solfege" if i18n.language() in i18n.SOLFEGE_LANGUAGES else "letters"
    return mt.normalize_notation(value)


def fill_keys(box: QComboBox, keys, selected=None) -> None:
    """Liste dont chaque ligne montre un texte traduit et garde la clé anglaise
    en donnée : les réglages enregistrent la clé, quelle que soit la langue."""
    box.clear()
    for key in keys:
        box.addItem(tr(key), key)
    index = box.findData(selected) if selected is not None else -1
    box.setCurrentIndex(index if index >= 0 else 0)


def key_of(box: QComboBox) -> str:
    """Clé anglaise de la ligne choisie (voir fill_keys)."""
    data = box.currentData()
    return str(data) if data is not None else box.currentText()


def set_key(box: QComboBox, key) -> None:
    """Choisit la ligne de clé `key` (sinon la première)."""
    index = box.findData(key) if key is not None else -1
    box.setCurrentIndex(index if index >= 0 else 0)


def number_field(low: int, high: int, prefix: str = "", suffix: str = "") -> TouchSpinBox:
    """Champ de nombre : clavier numérique, valeur prise à la fin de la saisie,
    « Done » ferme le clavier pour de bon (voir touch_input)."""
    spin = TouchSpinBox()
    spin.setRange(low, high)
    if prefix:
        spin.setPrefix(prefix)
    if suffix:
        spin.setSuffix(suffix)
    return spin


def text_field(placeholder: str = "", max_length: int = 0) -> TouchLineEdit:
    """Champ de texte : « Done » ferme le clavier pour de bon (voir touch_input)."""
    edit = TouchLineEdit()
    if placeholder:
        edit.setPlaceholderText(placeholder)
    if max_length:
        edit.setMaxLength(max_length)
    return edit


def combo(items: list | None = None, chars: int = 8, min_width: int = 0) -> QComboBox:
    """Liste déroulante de largeur fixe (`chars` caractères) : les barres du haut
    tiennent sur un petit écran ; la liste ouverte montre les textes en entier."""
    box = TouchComboBox()   # le même menu partout (voir touch_combo)
    box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    box.setMinimumContentsLength(chars)
    if items:
        box.addItems(items)
    if min_width:
        box.setMinimumWidth(min_width)
    return box


def fill_roots(box: QComboBox, selected: str, note_notation: str) -> None:
    box.blockSignals(True)
    box.clear()
    for root in mt.ROOTS:
        box.addItem(mt.format_root(root, note_notation), root)
    index = box.findData(selected)
    box.setCurrentIndex(index if index >= 0 else mt.ROOTS.index("A"))
    box.blockSignals(False)


def set_text_or_first(box: QComboBox, text) -> None:
    """Sélectionne `text` s'il existe, sinon le premier élément."""
    index = box.findText(str(text)) if text is not None else -1
    box.setCurrentIndex(index if index >= 0 else 0)


def scroll_area(content: QWidget) -> QScrollArea:
    """Zone qui défile au doigt, au fond transparent (thème sombre sur Android)."""
    scroll = QScrollArea()
    scroll.setObjectName("plain")
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    content.setObjectName("stripContent")
    scroll.setWidget(content)
    scroll.viewport().setAutoFillBackground(False)
    enable_touch_scroll(scroll)
    return scroll


def label(text: str = "", name: str = "", wrap: bool = False,
          align: Qt.AlignmentFlag | None = None) -> QLabel:
    """Étiquette (avec un nom d'objet pour la feuille de style : "title", "muted"…)."""
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    if align is not None:
        widget.setAlignment(align)
    return widget


def top_bar() -> QHBoxLayout:
    bar = QHBoxLayout()
    bar.setSpacing(6)
    return bar


class ToolStrip(QScrollArea):
    """Une rangée de contrôles qui ne déborde jamais : si l'écran est trop
    étroit, elle défile au doigt (ou à la molette) au lieu d'être coupée.
    Sinon elle remplit la largeur comme une rangée normale."""

    def __init__(self, row: QHBoxLayout | None = None) -> None:
        super().__init__()
        self.setObjectName("plain")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content = QWidget()
        content.setObjectName("stripContent")
        self.row = row if row is not None else QHBoxLayout()
        self.row.setContentsMargins(0, 0, 0, 0)
        content.setLayout(self.row)
        self.setWidget(content)
        self.viewport().setAutoFillBackground(False)
        enable_touch_scroll(self)

    def sizeHint(self) -> QSize:
        hint = self.widget().sizeHint()
        return QSize(hint.width(), hint.height())

    def minimumSizeHint(self) -> QSize:
        return QSize(40, self.widget().sizeHint().height())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setFixedHeight(max(1, self.widget().sizeHint().height()))

    def wheelEvent(self, event) -> None:
        bar = self.horizontalScrollBar()
        delta = event.angleDelta().y() or event.angleDelta().x()
        bar.setValue(bar.value() - delta)


def tool_strip(row: QHBoxLayout) -> ToolStrip:
    return ToolStrip(row)


def page_margins(layout) -> None:
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(6)


class ElidedLabel(QLabel):
    """Étiquette sur une ligne qui coupe le texte trop long avec « … »."""

    def __init__(self, text: str = "") -> None:
        super().__init__()
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def setText(self, text: str) -> None:
        self._full = text
        super().setText(text)
        self.setToolTip(text)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setPen(self.palette().windowText().color())
        elided = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight,
                                               self.width())
        p.drawText(self.rect(), self.alignment(), elided)
        p.end()


class OverlayPanel(QFrame):
    """Panneau qui s'ouvre par-dessus la page, collé au bord droit."""

    def __init__(self, page: QWidget, width: int) -> None:
        super().__init__(page)
        self.setObjectName("overlay")
        self.page = page
        self.panel_width = width
        self.top = 56
        self.button = None   # bouton à bascule qui ouvre ce panneau (voir bind_button)
        self.hide()

    def bind_button(self, button) -> None:
        """Le bouton à bascule qui ouvre le panneau reste enfoncé exactement tant
        que le panneau est ouvert, quelle que soit la façon de le fermer (bouton
        Fermer du panneau, autre panneau, mode écriture…). Sans ça, le bouton
        restait en surbrillance panneau fermé, et le toucher le refermait."""
        self.button = button

    def place(self, top: int | None = None) -> None:
        if top is not None:
            self.top = top
        margin = 8
        width = min(self.panel_width, self.page.width() - 2 * margin)
        height = max(120, self.page.height() - self.top - margin)
        self.setGeometry(self.page.width() - width - margin, self.top, width, height)
        self.raise_()

    def set_open(self, opened: bool) -> None:
        self.place()
        self.setVisible(opened)
        button = self.button
        if button is not None and button.isChecked() != opened:
            button.blockSignals(True)   # sans rouvrir / refermer le panneau
            button.setChecked(opened)
            button.blockSignals(False)


class SegmentBar(QFrame):
    """Cadre qui regroupe des boutons « segment » (contrôle segmenté)."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("segmentBar")
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(3, 3, 3, 3)
        self.row.setSpacing(2)
