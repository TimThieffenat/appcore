"""Page d'accueil : un exemple qui montre les outils du socle (à remplacer).

- textes : tr("…") (traduits avec locales/<code>.py) ;
- contrôles tactiles : ui.combo, ui.ToolStrip, ui.label, ui.page_margins ;
- son : sound.synth() (l'instrument des réglages) et sound.playback() ;
- réglages : bus.settings_changed quand un réglage change (thème, notes…) ;
- arrière-plan : app_paused() / app_resumed() appelés par la fenêtre.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from appcore import music_theory as mt
from appcore import sound
from appcore import ui_common as ui
from appcore.app_signals import bus
from appcore.guitar_synth import arpeggio
from appcore.i18n import tr

log = logging.getLogger(__name__)


class HomePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self.settings = QSettings()

        self.root_box = ui.combo(chars=6)
        self.play_button = QPushButton(tr("Play"))
        self.play_button.setObjectName("primary")
        self.play_button.clicked.connect(self._play)
        row = QHBoxLayout()
        row.addWidget(ui.label(tr("Root"), "muted"))
        row.addWidget(self.root_box)
        row.addStretch(1)
        row.addWidget(self.play_button)

        layout = QVBoxLayout(self)
        ui.page_margins(layout)
        layout.addWidget(ui.label(tr("Welcome"), "title"))
        layout.addWidget(ui.ToolStrip(row))
        self.hero = ui.label("", "hero", align=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hero, 1)

        self._refresh()
        self.root_box.currentIndexChanged.connect(lambda *_: self._refresh_hero())
        bus.settings_changed.connect(self._refresh)

    def _refresh(self, *_) -> None:
        """Les noms des notes suivent le réglage (lettres ou Do Ré Mi)."""
        ui.fill_roots(self.root_box, self.root_box.currentData() or "C",
                      ui.notation(self.settings))
        self._refresh_hero()

    def _refresh_hero(self) -> None:
        root = self.root_box.currentData() or "C"
        self.hero.setText(mt.key_title(root, "Major", ui.notation(self.settings)))

    def _play(self) -> None:
        """Un arpège majeur sur la note choisie, avec l'instrument des réglages."""
        root = mt.note_pc(self.root_box.currentData() or "C")
        notes = [48 + root + step for step in (0, 4, 7, 12, 16)]
        log.info("play: %s", self.root_box.currentData())
        sound.playback().play(arpeggio(sound.synth(), notes), self)

    def app_paused(self) -> None:
        """L'app passe en arrière-plan (la fenêtre a déjà coupé le son)."""

    def app_resumed(self) -> None:
        """Retour au premier plan."""
