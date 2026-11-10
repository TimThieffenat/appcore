"""Main window: icon rail on the left, pages on the right.

Designed for a phone in landscape: the rail is narrow (icon + short word)
and each page takes all the rest of the screen.

Pages come from the app (main.py): a list of (label, icon, class),
the label marked N_() (translated here), the icon a name from appcore/icons.py
or from the app's icons.py. A page can have:
- app_paused() / app_resumed(): the app goes to the background / comes back;
- handle_key(event) -> bool: keys (Android Back, Esc, digits…),
  True if the page handled it. Otherwise Back returns to the first page.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from appcore import app, sound
from appcore.app_signals import bus
from appcore.i18n import tr
from appcore.icons import nav_icon
from appcore.style import current_palette

log = logging.getLogger(__name__)


def settings_index(pages) -> int:
    """The settings page (the one whose class comes from appcore.page_settings),
    else the last one."""
    from appcore.page_settings import SettingsPage
    for i, (_, _, page_class) in enumerate(pages):
        if isinstance(page_class, type) and issubclass(page_class, SettingsPage):
            return i
    return max(0, len(pages) - 1)

# Android puts the app aside (screen off, Home button, another app): its
# drawing surface is destroyed. Nothing must draw or play any more.
PAUSED_STATES = (Qt.ApplicationState.ApplicationSuspended,
                 Qt.ApplicationState.ApplicationHidden)

RAIL_WIDTH = 84
BUTTON_MIN, BUTTON_MAX = 32, 50   # height of a rail button (depends on the screen)
# Fewer pages: bigger buttons (at most BIG_BUTTON_MAX, PerfectPitch)
FEW_PAGES, BIG_BUTTON_MAX = 5, 64


class MainWindow(QMainWindow):
    def __init__(self, pages) -> None:
        super().__init__()
        self.pages = list(pages)
        self.setWindowTitle(app.name())
        self.resize(1000, 480)
        self.setMinimumSize(560, 300)

        rail = QFrame()
        self.rail = rail
        rail.setObjectName("rail")
        rail.setFixedWidth(RAIL_WIDTH)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(6, 4, 6, 4)
        rail_layout.setSpacing(1)

        self.stack = QStackedWidget()
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[tuple[QToolButton, str]] = []

        for index, (label, icon, page_class) in enumerate(self.pages):
            button = QToolButton()
            button.setObjectName("navButton")
            button.setText(tr(label))
            button.setToolTip(tr(label))
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(20, 20))
            button.setFixedSize(RAIL_WIDTH - 12, 41)  # adjusted to the screen height
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(button, index)
            rail_layout.addWidget(button)
            self.buttons.append((button, icon))
            self.stack.addWidget(page_class())
        rail_layout.addStretch(1)

        self.group.idClicked.connect(self._show_page)
        self.group.button(0).setChecked(True)
        self.stack.setCurrentIndex(0)
        self._refresh_icons()
        bus.settings_changed.connect(self._refresh_icons)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(rail)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self._app_paused = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_rail()

    def _fit_rail(self) -> None:
        """The rail buttons share the screen height: every page stays
        visible from a small phone to a desktop."""
        count = len(self.buttons)
        available = self.rail.height() - 8 - (count - 1)
        biggest = BIG_BUTTON_MAX if count <= FEW_PAGES else BUTTON_MAX
        height = int(max(BUTTON_MIN, min(biggest, available / max(1, count))))
        icon = 16 if height < 37 else 18 if height < 41 else 20 if height < 46 else \
            22 if height < 54 else 24
        style = Qt.ToolButtonStyle.ToolButtonTextUnderIcon if height >= 33 \
            else Qt.ToolButtonStyle.ToolButtonIconOnly
        for button, _ in self.buttons:
            button.setFixedSize(RAIL_WIDTH - 12, height)
            button.setIconSize(QSize(icon, icon))
            button.setToolButtonStyle(style)

    def _show_page(self, index: int) -> None:
        sound.playback().stop()  # a page's sound does not carry over to the next one
        self.stack.setCurrentIndex(index)
        log.info("page: %s", self.pages[index][0] if 0 <= index < len(self.pages) else index)

    def show_page(self, index: int) -> None:
        """Shows a page as if its button had been tapped (without sound)."""
        if 0 <= index < len(self.buttons):
            self.group.button(index).setChecked(True)
            self.stack.setCurrentIndex(index)

    # --- Keys: Back (Android), Esc, digits… --------------------------------------------
    def keyPressEvent(self, event) -> None:
        page = self.stack.currentWidget()
        if hasattr(page, "handle_key") and page.handle_key(event):
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Back, Qt.Key.Key_Escape) and self.stack.currentIndex() != 0:
            self.show_page(0)    # Back from another page: the first page
            event.accept()
            return
        super().keyPressEvent(event)

    # --- Background (Android) ----------------------------------------------------------
    def on_app_state_changed(self, state) -> None:
        """Connected to QApplication.applicationStateChanged (see boot.py)."""
        log.info("app state: %s", getattr(state, "name", state))
        if state in PAUSED_STATES:
            self.pause_app()
        elif state == Qt.ApplicationState.ApplicationActive:
            self.resume_app()

    def _pages(self) -> list[QWidget]:
        return [self.stack.widget(i) for i in range(self.stack.count())]

    def pause_app(self) -> None:
        """The app goes to the background: stop the sound, the microphone and the
        timers that redraw the screen (otherwise Qt draws on a destroyed
        surface: "eglSwapBuffers failed", black screen when coming back)."""
        if self._app_paused:
            return
        self._app_paused = True
        sound.playback().stop(fade=False)   # right away: the app no longer runs
        for page in self._pages():
            if hasattr(page, "app_paused"):
                page.app_paused()

    def resume_app(self) -> None:
        """Back to the foreground: restart what needs it and
        redraw everything on the new surface."""
        if not self._app_paused:
            return
        self._app_paused = False
        for page in self._pages():
            if hasattr(page, "app_resumed"):
                page.app_resumed()
        self.update()
        # the Android surface can arrive right after the signal: second pass
        QTimer.singleShot(250, self.update)

    def _refresh_icons(self, *_) -> None:
        pal = current_palette()
        for button, icon in self.buttons:
            button.setIcon(nav_icon(icon, pal["muted"], pal["accent_text"]))
