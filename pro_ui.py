"""Interface pieces of the Pro version (see pro.py), shared by the apps.

- `PurchaseControls`: the status line, "Restore purchase" and "Unlock for
  €4.99" buttons, kept up to date (price, waiting, errors, already bought). The
  app places the three widgets in its own sheet or page.
- `gate(page_class, wall_class)`: a page reserved to Pro. Until Pro is
  bought, it shows the app's "wall" (what the page does, what Pro opens, the
  PurchaseControls); once bought, the real page takes its place (created only
  then: start-up stays as fast). The window draws a small gold padlock on the
  icon of such a page (`locked_icon`, a page class with `PRO = True`).
- `badge(p, ...)`: that padlock, for the app's own drawings.

The Pro row of the settings (and the unlock code) is in page_settings.py.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QPushButton, QStackedWidget, QWidget

from appcore import bridge, icons, pro
from appcore import ui_common as ui
from appcore.app_signals import bus
from appcore.i18n import tr
from appcore.style import current_palette

log = logging.getLogger(__name__)


# --- Padlock -------------------------------------------------------------------------------
def badge(p: QPainter, cx: float, cy: float, r: float, pal: dict) -> None:
    """Gold disc with a padlock (centre cx, cy; radius r; 24-unit grid)."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(pal["bg"]))
    p.drawEllipse(QPointF(cx, cy), r + 1.0, r + 1.0)
    p.setBrush(QColor(pal["gold"]))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.restore()
    icons.paint(p, "lock", QRectF(cx - r * 0.82, cy - r * 0.86, r * 1.64, r * 1.64),
                pal["bg"], width=2.6)


def _locked_pixmap(name: str, color: str, pal: dict) -> QPixmap:
    ratio = icons.RATIO
    size = icons.SIZE
    pm = QPixmap(int(size * ratio), int(size * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    icons.paint(p, name, QRectF(0, 0, size, size), color)
    badge(p, 18.5, 18.5, 5.3, pal)
    p.end()
    return pm


def locked_icon(name: str, normal: str, active: str) -> QIcon:
    """The navigation icon of a Pro page not bought yet (with the padlock)."""
    pal = current_palette()
    icon = QIcon()
    icon.addPixmap(_locked_pixmap(name, normal, pal), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(_locked_pixmap(name, active, pal), QIcon.Mode.Normal, QIcon.State.On)
    return icon


def is_pro_page(page_class) -> bool:
    return getattr(page_class, "PRO", False) is True


# --- Purchase buttons ----------------------------------------------------------------------
class PurchaseControls(QObject):
    """`status` (QLabel), `restore_button` and `buy_button`, kept up to date.

    On a phone, "Restore purchase" shows while Pro is not there; on a computer,
    "Lock again (test)" shows once it is (to test again). `owned_text`: what
    the status line says once Pro is bought (empty: nothing)."""

    def __init__(self, parent: QWidget, owned_text: str = "") -> None:
        super().__init__(parent)
        self.owned_text = owned_text
        self.status = ui.label("", "muted", wrap=True)
        self.restore_button = QPushButton(tr("Restore purchase") if bridge.available()
                                          else tr("Lock again (test)"))
        self.restore_button.setObjectName("toggle")
        self.restore_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.restore_button.clicked.connect(lambda *_: pro.restore())
        self.buy_button = QPushButton("")
        self.buy_button.setObjectName("primary")
        self.buy_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buy_button.clicked.connect(lambda *_: self.buy())
        bus.pro_changed.connect(self.refresh)
        self.refresh()

    def buy(self) -> None:
        log.info("pro: buy from %s", self.parent().__class__.__name__)
        pro.buy()

    def refresh(self, *_) -> None:
        owned = pro.is_pro()
        price = pro.price()
        self.buy_button.setText(tr("Unlock for {price}", price=price) if price
                                else tr("Unlock Pro"))
        self.buy_button.setVisible(not owned)
        self.buy_button.setEnabled(not pro.pending())
        self.restore_button.setVisible(owned != bridge.available())
        if owned:
            text, name = self.owned_text, "good"
        else:
            text, name = pro.status(), "muted"
            if not text and not bridge.available():
                text = tr("Computer version: unlocking is free, for testing.")
        self.status.setText(text)
        if self.status.objectName() != name:
            self.status.setObjectName(name)
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)


# --- Pages reserved to Pro -----------------------------------------------------------------
class ProGate(QStackedWidget):
    """A Pro page: the app's wall, or the real page once bought."""

    PRO = True
    PAGE: type = QWidget
    WALL: type = QWidget

    def __init__(self) -> None:
        super().__init__()
        self.wall = self.WALL()
        self.addWidget(self.wall)
        self.page: QWidget | None = None
        bus.pro_changed.connect(self._sync)
        self._sync()

    def _sync(self, *_) -> None:
        if pro.is_pro():
            if self.page is None:
                log.info("pro page opened: %s", self.PAGE.__name__)
                self.page = self.PAGE()
                self.addWidget(self.page)
            self.setCurrentWidget(self.page)
        else:
            self.setCurrentWidget(self.wall)

    def _active(self) -> QWidget | None:
        return self.page if self.page is not None and self.currentWidget() is self.page else None

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not pro.is_pro():
            pro.start()             # Google Play: price and purchases read again

    # what the window asks of pages (main_window.py)
    def app_paused(self) -> None:
        if self.page is not None and hasattr(self.page, "app_paused"):
            self.page.app_paused()

    def app_resumed(self) -> None:
        if self.page is not None and hasattr(self.page, "app_resumed"):
            self.page.app_resumed()

    def handle_key(self, event) -> bool:
        page = self._active()
        return bool(page is not None and hasattr(page, "handle_key") and page.handle_key(event))


def gate(page_class: type, wall_class: type) -> type:
    """The class to put in pages() for a page reserved to Pro: `wall_class()`
    is shown until Pro is bought, then `page_class()`."""
    return type(page_class.__name__ + "Pro", (ProGate,),
                {"PAGE": page_class, "WALL": wall_class})
