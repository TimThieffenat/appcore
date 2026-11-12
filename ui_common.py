"""Small interface tools shared by the pages (phone format).

An app can extend this module in its own ui_common.py
(`from appcore.ui_common import *` then its own tools: capo, tuning…).
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
    """Finger scrolling (with inertia) on Android."""
    if is_android():
        QScroller.grabGesture(area.viewport(),
                              QScroller.ScrollerGestureType.LeftMouseButtonGesture)


def notation(settings: QSettings) -> str:
    """Note names: the setting, else Do Ré Mi in the languages where it is
    customary (French, Spanish, Italian, Portuguese), C D E elsewhere."""
    value = settings.value("notation")
    if value is None or value == "":
        return "solfege" if i18n.language() in i18n.SOLFEGE_LANGUAGES else "letters"
    return mt.normalize_notation(value)


def fill_keys(box: QComboBox, keys, selected=None) -> None:
    """List whose rows show a translated text and keep the English key
    as data: settings save the key, whatever the language."""
    box.clear()
    for key in keys:
        box.addItem(tr(key), key)
    index = box.findData(selected) if selected is not None else -1
    box.setCurrentIndex(index if index >= 0 else 0)


def key_of(box: QComboBox) -> str:
    """English key of the chosen row (see fill_keys)."""
    data = box.currentData()
    return str(data) if data is not None else box.currentText()


def set_key(box: QComboBox, key) -> None:
    """Selects the row with key `key` (else the first one)."""
    index = box.findData(key) if key is not None else -1
    box.setCurrentIndex(index if index >= 0 else 0)


def number_field(low: int, high: int, prefix: str = "", suffix: str = "") -> TouchSpinBox:
    """Number field: numeric keyboard, value taken at the end of input,
    "Done" closes the keyboard for good (see touch_input)."""
    spin = TouchSpinBox()
    spin.setRange(low, high)
    if prefix:
        spin.setPrefix(prefix)
    if suffix:
        spin.setSuffix(suffix)
    return spin


def text_field(placeholder: str = "", max_length: int = 0) -> TouchLineEdit:
    """Text field: "Done" closes the keyboard for good (see touch_input)."""
    edit = TouchLineEdit()
    if placeholder:
        edit.setPlaceholderText(placeholder)
    if max_length:
        edit.setMaxLength(max_length)
    return edit


def combo(items: list | None = None, chars: int = 8, min_width: int = 0) -> QComboBox:
    """Fixed-width drop-down list (`chars` characters): top bars fit
    on a small screen; the open list shows the full texts."""
    box = TouchComboBox()   # the same menu everywhere (see touch_combo)
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
    """Selects `text` if it exists, else the first item."""
    index = box.findText(str(text)) if text is not None else -1
    box.setCurrentIndex(index if index >= 0 else 0)


def scroll_area(content: QWidget) -> QScrollArea:
    """Area scrolled with the finger, transparent background (dark theme on Android)."""
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
    """Label (with an object name for the style sheet: "title", "muted"…)."""
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
    """A row of controls that never overflows: if the screen is too
    narrow, it scrolls with the finger (or the wheel) instead of being cut.
    Otherwise it fills the width like a normal row."""

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
    """One-line label that cuts text that is too long with "…"."""

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
    """Panel opening over the page, stuck to the right edge."""

    def __init__(self, page: QWidget, width: int) -> None:
        super().__init__(page)
        self.setObjectName("overlay")
        self.page = page
        self.panel_width = width
        self.top = 56
        self.button = None   # toggle button opening this panel (see bind_button)
        self.hide()

    def bind_button(self, button) -> None:
        """The toggle button opening the panel stays pressed exactly as long
        as the panel is open, however it is closed (the panel's Close
        button, another panel, edit mode…). Without this, the button
        stayed highlighted with the panel closed, and tapping it closed it again."""
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
            button.blockSignals(True)   # without reopening / closing the panel
            button.setChecked(opened)
            button.blockSignals(False)


class SegmentBar(QFrame):
    """Frame grouping "segment" buttons (segmented control)."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("segmentBar")
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(3, 3, 3, 3)
        self.row.setSpacing(2)
