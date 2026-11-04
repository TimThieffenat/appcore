"""Menus déroulants faits pour le doigt, les mêmes dans toute l'app.

`TouchComboBox` garde toute l'interface de QComboBox (éléments, index,
signaux) mais n'utilise pas sa liste : celle de Qt est pensée pour la souris.
Sur téléphone elle s'ouvrait et se refermait toute seule, choisissait la ligne
sous le doigt au moindre glissement et restait en surbrillance.

- La case s'ouvre sur un vrai toucher : appui puis relâché sur la case, sans
  glisser. Faire défiler une barre en partant d'une case ne l'ouvre pas, et la
  molette de la souris ne change plus la valeur par accident.
- Pas de bouton flèche : toute la case est le bouton.
- La liste (`ChoiceSheet`) s'ouvre au milieu de l'écran, par-dessus un voile :
  grandes lignes, choix actuel coché et visible, défilement au doigt.
- Une ligne n'est choisie que si le doigt n'a pas glissé et que la liste n'a
  pas défilé ; toucher le voile (ou Échap / retour) ferme sans rien changer.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QScrollArea,
    QScroller,
    QVBoxLayout,
    QWidget,
)

SLOP = 14            # px : au-delà, le doigt a glissé (ce n'est plus un toucher)
ROW_HEIGHT = 44      # px : hauteur d'une ligne (cible confortable pour le doigt)
GUARD_S = 0.25       # s : la liste ignore les touchers juste après son ouverture
CARD_MAX_WIDTH = 460


def _on_android() -> bool:
    return QGuiApplication.platformName() == "android"


def _global(event) -> QPoint:
    return event.globalPosition().toPoint()


def _moved(a: QPoint, b: QPoint) -> int:
    return abs(a.x() - b.x()) + abs(a.y() - b.y())


def _refresh(widget: QWidget) -> None:
    """Réapplique la feuille de style après un changement de propriété."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class TouchComboBox(QComboBox):
    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # pas de surbrillance « focus »
        self._down: QPoint | None = None
        self.sheet: ChoiceSheet | None = None

    # --- Toucher ------------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._down = _global(event)   # on attend le relâché pour ouvrir
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._down is not None and _moved(_global(event), self._down) > SLOP:
            self._down = None             # le doigt glisse : ce n'est pas un toucher
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        down, self._down = self._down, None
        if (event.button() == Qt.MouseButton.LeftButton and down is not None
                and _moved(_global(event), down) <= SLOP
                and self.rect().contains(event.position().toPoint())):
            self.showPopup()
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        event.accept()

    def wheelEvent(self, event) -> None:
        event.ignore()   # la molette fait défiler la page, pas la valeur

    # --- Liste ----------------------------------------------------------------------------
    def showPopup(self) -> None:
        if self.sheet is None and self.count() and self.isEnabled():
            self.sheet = ChoiceSheet(self)

    def hidePopup(self) -> None:
        if self.sheet is not None:
            self.sheet.dismiss()

    def _sheet_closed(self) -> None:
        self.sheet = None
        self.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        self.update()


class ChoiceRow(QLabel):
    """Une ligne de la liste ; choisie seulement sur un vrai toucher."""

    def __init__(self, sheet: "ChoiceSheet", index: int, text: str, current: bool) -> None:
        super().__init__(("✓  " if current else "") + text)
        self.sheet = sheet
        self.index = index
        self.setObjectName("choiceRow")
        self.setProperty("current", current)
        self.setProperty("pressed", False)
        self.setMinimumHeight(ROW_HEIGHT)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._down: QPoint | None = None
        self._scroll = 0

    def _press_look(self, on: bool) -> None:
        if self.property("pressed") != on:
            self.setProperty("pressed", on)
            _refresh(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.sheet.guarded():
            self._down = _global(event)
            self._scroll = self.sheet.scroll_value()
            self._press_look(True)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._down is not None and (_moved(_global(event), self._down) > SLOP
                                       or abs(self.sheet.scroll_value() - self._scroll) > 2):
            self._down = None
            self._press_look(False)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        down, self._down = self._down, None
        self._press_look(False)
        if (event.button() == Qt.MouseButton.LeftButton and down is not None
                and _moved(_global(event), down) <= SLOP
                and abs(self.sheet.scroll_value() - self._scroll) <= 2
                and self.rect().contains(event.position().toPoint())
                and not self.sheet.scrolling()):
            self.sheet.choose(self.index)
        event.accept()


class ChoiceSheet(QWidget):
    """La liste d'un menu, au centre de la fenêtre, sur un voile."""

    def __init__(self, combo: TouchComboBox) -> None:
        window = combo.window()
        super().__init__(window)
        self.combo = combo
        self.window_ = window
        self.opened = time.monotonic()
        self._down: QPoint | None = None
        self.setObjectName("choiceSheet")

        self.card = QFrame(self)
        self.card.setObjectName("choiceCard")
        self.list_area = QScrollArea(self.card)
        self.list_area.setObjectName("plain")
        self.list_area.setFrameShape(QFrame.Shape.NoFrame)
        self.list_area.setWidgetResizable(True)
        self.list_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("stripContent")
        rows = QVBoxLayout(content)
        rows.setContentsMargins(6, 6, 6, 6)
        rows.setSpacing(2)
        self.rows: list[ChoiceRow] = []
        current = combo.currentIndex()
        for i in range(combo.count()):
            row = ChoiceRow(self, i, combo.itemText(i), i == current)
            rows.addWidget(row)
            self.rows.append(row)
        rows.addStretch(1)
        self.list_area.setWidget(content)
        self.list_area.viewport().setAutoFillBackground(False)
        if _on_android():
            QScroller.grabGesture(self.list_area.viewport(),
                                  QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(4, 4, 4, 4)
        card_layout.addWidget(self.list_area)

        self.place()
        window.installEventFilter(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)   # reçoit Échap / retour
        self.show()
        self.raise_()
        self.setFocus()
        if 0 <= current < len(self.rows):  # le choix actuel, au milieu de la liste
            self.list_area.ensureWidgetVisible(self.rows[current], 0,
                                            max(0, self.card.height() // 2 - ROW_HEIGHT))

    # --- Placement ------------------------------------------------------------------------
    def place(self) -> None:
        w, h = self.window_.width(), self.window_.height()
        self.setGeometry(0, 0, w, h)
        width = min(CARD_MAX_WIDTH, max(220, self.combo.width() + 120), w - 32)
        content = len(self.rows) * (ROW_HEIGHT + 2) + 20
        height = min(content, h - 32)
        self.card.setGeometry((w - width) // 2, (h - height) // 2, width, height)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.window_ and event.type() == QEvent.Type.Resize:
            self.place()
        return False

    # --- État -----------------------------------------------------------------------------
    def guarded(self) -> bool:
        return time.monotonic() - self.opened < GUARD_S

    def scroll_value(self) -> int:
        return self.list_area.verticalScrollBar().value()

    def scrolling(self) -> bool:
        if not _on_android():
            return False
        state = QScroller.scroller(self.list_area.viewport()).state()
        return state in (QScroller.State.Dragging, QScroller.State.Scrolling)

    # --- Choisir / fermer -------------------------------------------------------------------
    def choose(self, index: int) -> None:
        combo = self.combo
        self.dismiss()
        if index != combo.currentIndex():
            combo.setCurrentIndex(index)   # émet currentIndexChanged comme avant

    def dismiss(self) -> None:
        if self.combo.sheet is not self:
            return
        self.window_.removeEventFilter(self)
        self.hide()
        self.deleteLater()
        self.combo._sheet_closed()

    # --- Voile ----------------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 120))
        p.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.guarded():
            self._down = _global(event)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        down, self._down = self._down, None
        if (down is not None and _moved(_global(event), down) <= SLOP
                and not self.card.geometry().contains(event.position().toPoint())):
            self.dismiss()   # toucher à côté de la liste : on ferme sans rien changer
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            event.accept()
        elif event.key() == Qt.Key.Key_Back:
            event.accept()   # fermé au relâché (sinon Android quitte l'app)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Back:
            self.dismiss()
            event.accept()
        else:
            super().keyReleaseEvent(event)
