"""Champs de saisie au clavier faits pour le téléphone (nombres et texte).

Sur Android, après « Done » le champ gardait la main : le clavier se fermait
puis se rouvrait aussitôt (la page se rafraîchissait à chaque chiffre tapé, et
Android rouvre le clavier du champ qui a la main). Ici :

- « Done » (ou Entrée) valide, rend la main et ferme le clavier pour de bon ;
- quand le clavier se ferme autrement (bouton retour…), le champ rend la main
  aussi : rien ne le rouvre tout seul ;
- un nombre n'est pris en compte qu'à la fin de la saisie (pas à chaque
  chiffre), avec un clavier numérique sans suggestions.
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
    except RuntimeError:  # widget déjà détruit
        pass
    QGuiApplication.inputMethod().hide()


def close_keyboard_later(widget: QWidget) -> None:
    """Après la touche Entrée / Done : une fois que le champ a fini de la traiter,
    il rend la main et le clavier se ferme ; une seconde fois un peu plus tard,
    au cas où un rafraîchissement de la page l'aurait rouvert."""
    QTimer.singleShot(0, lambda: _release(widget))
    QTimer.singleShot(200, lambda: _release(widget))


def _keyboard_visibility_changed() -> None:
    if not QGuiApplication.inputMethod().isVisible():
        QTimer.singleShot(250, _drop_focus_if_keyboard_hidden)


def _drop_focus_if_keyboard_hidden() -> None:
    if QGuiApplication.inputMethod().isVisible():
        return  # simple passage d'un champ à l'autre : le clavier est revenu
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
    return event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)   # « Done » d'Android = Entrée


class TouchSpinBox(QSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setKeyboardTracking(False)   # valeur prise à la fin de la saisie
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
