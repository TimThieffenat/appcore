"""Fenêtre principale : rail d'icônes à gauche, pages à droite.

Pensée pour un téléphone en paysage : le rail est étroit (icône + mot court)
et chaque page occupe tout le reste de l'écran.

Les pages viennent de l'app (main.py) : une liste de (libellé, icône, classe),
le libellé marqué N_() (traduit ici), l'icône un nom de appcore/icons.py ou de
l'icons.py de l'app. Une page peut avoir :
- app_paused() / app_resumed() : l'app passe en arrière-plan / revient ;
- handle_key(event) -> bool : touches (Retour d'Android, Échap, chiffres…),
  True si la page l'a traitée. Sinon Retour ramène à la première page.
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
    """La page des réglages (celle dont la classe vient de appcore.page_settings),
    sinon la dernière."""
    from appcore.page_settings import SettingsPage
    for i, (_, _, page_class) in enumerate(pages):
        if isinstance(page_class, type) and issubclass(page_class, SettingsPage):
            return i
    return max(0, len(pages) - 1)

# Android met l'app de côté (écran éteint, bouton Accueil, autre app) : sa
# surface d'affichage est détruite. Rien ne doit plus dessiner ni jouer.
PAUSED_STATES = (Qt.ApplicationState.ApplicationSuspended,
                 Qt.ApplicationState.ApplicationHidden)

RAIL_WIDTH = 84
BUTTON_MIN, BUTTON_MAX = 32, 50   # hauteur d'un bouton du rail (selon l'écran)
# Moins de pages : des boutons plus grands (au plus BIG_BUTTON_MAX, PerfectPitch)
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
            button.setFixedSize(RAIL_WIDTH - 12, 41)  # ajusté à la hauteur de l'écran
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
        """Les boutons du rail se partagent la hauteur de l'écran : toutes les
        pages restent visibles du petit téléphone à l'ordinateur."""
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
        sound.playback().stop()  # le son d'une page ne suit pas sur la suivante
        self.stack.setCurrentIndex(index)
        log.info("page: %s", self.pages[index][0] if 0 <= index < len(self.pages) else index)

    def show_page(self, index: int) -> None:
        """Affiche une page comme si on avait touché son bouton (sans son)."""
        if 0 <= index < len(self.buttons):
            self.group.button(index).setChecked(True)
            self.stack.setCurrentIndex(index)

    # --- Touches : Retour (Android), Échap, chiffres… ---------------------------------
    def keyPressEvent(self, event) -> None:
        page = self.stack.currentWidget()
        if hasattr(page, "handle_key") and page.handle_key(event):
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Back, Qt.Key.Key_Escape) and self.stack.currentIndex() != 0:
            self.show_page(0)    # Retour depuis une autre page : la première page
            event.accept()
            return
        super().keyPressEvent(event)

    # --- Arrière-plan (Android) ------------------------------------------------------
    def on_app_state_changed(self, state) -> None:
        """Branché sur QApplication.applicationStateChanged (voir main.py)."""
        log.info("app state: %s", getattr(state, "name", state))
        if state in PAUSED_STATES:
            self.pause_app()
        elif state == Qt.ApplicationState.ApplicationActive:
            self.resume_app()

    def _pages(self) -> list[QWidget]:
        return [self.stack.widget(i) for i in range(self.stack.count())]

    def pause_app(self) -> None:
        """L'app passe en arrière-plan : on coupe le son, le micro et les
        minuteries qui redessinent l'écran (sinon Qt dessine sur une surface
        détruite : « eglSwapBuffers failed », écran noir au retour)."""
        if self._app_paused:
            return
        self._app_paused = True
        sound.playback().stop(fade=False)   # tout de suite : l'app ne tourne plus
        for page in self._pages():
            if hasattr(page, "app_paused"):
                page.app_paused()

    def resume_app(self) -> None:
        """Retour au premier plan : on relance ce qui doit l'être et on
        redessine tout sur la nouvelle surface."""
        if not self._app_paused:
            return
        self._app_paused = False
        for page in self._pages():
            if hasattr(page, "app_resumed"):
                page.app_resumed()
        self.update()
        # la surface Android peut arriver juste après le signal : second passage
        QTimer.singleShot(250, self.update)

    def _refresh_icons(self, *_) -> None:
        pal = current_palette()
        for button, icon in self.buttons:
            button.setIcon(nav_icon(icon, pal["muted"], pal["accent_text"]))
