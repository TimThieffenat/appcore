"""Keyboard input fields made for the phone (numbers and text).

On Android, after "Done" the field kept the focus: the keyboard closed
then reopened at once (the page refreshed at each digit typed, and
Android reopens the keyboard of the focused field). Here:

- "Done" (or Enter) confirms, gives up the focus and closes the keyboard for good;
- when the keyboard closes another way (Back button…), the field gives up the
  focus too: nothing reopens it on its own;
- a number is only taken at the end of input (not at each
  digit), with a numeric keyboard without suggestions.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLineEdit, QSpinBox, QWidget

_watching = False


def _on_android() -> bool:
    return QGuiApplication.platformName() == "android"


def _release(widget: QWidget) -> None:
    try:
        if widget.hasFocus():
            widget.clearFocus()
    except RuntimeError:  # widget already destroyed
        pass
    QGuiApplication.inputMethod().hide()


def close_keyboard_later(widget: QWidget) -> None:
    """After the Enter / Done key: once the field has finished handling it,
    it gives up the focus and the keyboard closes; a second time a bit later,
    in case a page refresh reopened it."""
    QTimer.singleShot(0, lambda: _release(widget))
    QTimer.singleShot(200, lambda: _release(widget))


def _keyboard_visibility_changed() -> None:
    if not QGuiApplication.inputMethod().isVisible():
        QTimer.singleShot(250, _drop_focus_if_keyboard_hidden)


def _drop_focus_if_keyboard_hidden() -> None:
    if QGuiApplication.inputMethod().isVisible():
        return  # just moving from one field to another: the keyboard came back
    widget = QApplication.focusWidget()
    if isinstance(widget, (TouchSpinBox, TouchLineEdit)):
        widget.clearFocus()


def _watch_keyboard() -> None:
    global _watching
    if _watching or not _on_android():
        return
    _watching = True
    QGuiApplication.inputMethod().visibleChanged.connect(_keyboard_visibility_changed)


def _is_enter(event) -> bool:
    return event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)   # Android's "Done" = Enter


class TouchSpinBox(QSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setKeyboardTracking(False)   # value taken at the end of input
        self.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly
                                 | Qt.InputMethodHint.ImhNoPredictiveText)
        _watch_keyboard()

    def keyPressEvent(self, event) -> None:
        super().keyPressEvent(event)
        if _is_enter(event):
            close_keyboard_later(self)


class TouchLineEdit(QLineEdit):
    def __init__(self) -> None:
        super().__init__()
        _watch_keyboard()

    def keyPressEvent(self, event) -> None:
        super().keyPressEvent(event)
        if _is_enter(event):
            close_keyboard_later(self)
