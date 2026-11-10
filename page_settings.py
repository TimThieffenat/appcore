"""The base's "Settings" page: language, theme, note names, sound, error
report, and the app's own settings.

Each app makes a subclass of it (its page_settings.py) that adds its
rows by overriding rows(), and possibly sound_demo(), credits(),
voice_text() / voice_refused() (instrument reserved to the Pro version…):

    class SettingsPage(BaseSettingsPage):
        SOUND_LABEL = N_("Guitar sound")

        def rows(self):
            self.capo_box = ui.combo(chars=18, min_width=200)
            ...
            return [self.language_row(), self.theme_row(), self.notation_row(),
                    (tr("Capo"), self.capo_box), self.sound_row(), self.report_row()]

Rows are set with save(key, value): the setting is saved,
written to the log, and the pages redrawn (bus.settings_changed).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from appcore import app, crash_report, i18n, sound
from appcore import music_theory as mt
from appcore import ui_common as ui
from appcore.app_signals import bus
from appcore.guitar_synth import VOICES, arpeggio
from appcore.i18n import N_, tr
from appcore.style import SYSTEM, apply_theme, theme_choice

THEME_LABELS = [(N_("Same as phone"), SYSTEM), (N_("Light (pastel)"), "light"),
                (N_("Dark (neon)"), "dark")]
log = logging.getLogger(__name__)


class SettingsPage(QWidget):
    SOUND_LABEL = N_("Instrument")   # label of the sound row (translated when shown)
    CARD_WIDTH = 520                 # maximum width of the settings card

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self.settings = QSettings()

        title = QLabel(tr("Settings"))
        title.setObjectName("title")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        # narrow screen (phone in portrait): the label goes above
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        for text, widget in self.rows():
            label = QLabel(text)
            label.setObjectName("muted")
            form.addRow(label, widget)
        about = QLabel(f"{app.name()} {app.version()}\n" + self.credits())
        about.setObjectName("muted")
        about.setWordWrap(True)
        about.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # A centred card of limited width: readable on every screen
        card = QFrame()
        card.setObjectName("sidePanel")
        card.setMaximumWidth(self.CARD_WIDTH)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 16)
        card_layout.setSpacing(12)
        card_layout.addWidget(title)
        card_layout.addLayout(form)
        row = QHBoxLayout()
        if app.portrait():          # narrow screen: the full width
            row.addWidget(card, 1)
        else:
            row.addStretch(1)
            row.addWidget(card, 4)
            row.addStretch(1)

        content = QWidget()
        inner = QVBoxLayout(content)
        inner.setContentsMargins(16, 10, 16, 10)
        inner.setSpacing(10)
        inner.addStretch(1)
        inner.addLayout(row)
        inner.addStretch(1)
        inner.addWidget(about)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ui.scroll_area(content))

    # --- Rows ------------------------------------------------------------------------------
    def rows(self) -> list[tuple[str, QWidget]]:
        """The card's rows, in order: (translated label, control)."""
        return [self.language_row(), self.theme_row(), self.notation_row(),
                self.sound_row(), self.report_row()]

    def language_row(self) -> tuple[str, QWidget]:
        box = ui.combo(chars=18, min_width=200)
        phone = i18n.LANGUAGES[i18n.system_language()]
        box.addItem(tr("Same as phone ({language})", language=phone), i18n.SYSTEM)
        for code, name in i18n.LANGUAGES.items():
            box.addItem(name, code)    # each language in its own language
        box.setCurrentIndex(max(0, box.findData(str(self.settings.value("language", i18n.SYSTEM)))))
        box.currentIndexChanged.connect(self._on_language)
        self.language_box = box
        return tr("Language"), box

    def theme_row(self) -> tuple[str, QWidget]:
        box = ui.combo(chars=18, min_width=200)
        for label, key in THEME_LABELS:
            box.addItem(tr(label), key)
        box.setCurrentIndex(max(0, box.findData(theme_choice(self.settings.value("theme", SYSTEM)))))
        box.currentIndexChanged.connect(self._on_theme)
        self.theme_box = box
        return tr("Theme"), box

    def notation_row(self) -> tuple[str, QWidget]:
        box = ui.combo(chars=18, min_width=200)
        for key in mt.NOTATIONS:
            box.addItem(mt.notation_label(key), key)
        box.setCurrentIndex(max(0, box.findData(ui.notation(self.settings))))
        box.currentIndexChanged.connect(lambda *_: self.save("notation", box.currentData()))
        self.notation_box = box
        return tr("Note names"), box

    def sound_row(self) -> tuple[str, QWidget]:
        self.sound_box = ui.combo(chars=18, min_width=200)
        self.fill_sounds()
        self.sound_box.currentIndexChanged.connect(self._on_sound)
        return tr(self.SOUND_LABEL), self.sound_box

    def fill_sounds(self) -> None:
        """(Re)fills the list of instruments (after a purchase, for example)."""
        box = self.sound_box
        box.blockSignals(True)
        box.clear()
        for key in sound.voices():
            box.addItem(self.voice_text(key), key)
        box.setCurrentIndex(max(0, box.findData(sound.voice())))
        box.blockSignals(False)

    def voice_text(self, key: str) -> str:
        """The text of an instrument in the list."""
        return tr(VOICES[key][0])

    def voice_refused(self, key: str) -> None:
        """A non-allowed instrument was chosen (sound.set_voice_filter):
        the list goes back to the previous instrument; the app can offer the purchase."""

    def report_row(self) -> tuple[str, QWidget]:
        button = QPushButton(tr("Show"))
        button.setToolTip(tr("What went wrong and what the app did, to send by email "
                             "if the app misbehaves"))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(lambda *_: self._show_report())
        self.report_button = button
        return tr("Error report"), button

    def credits(self) -> str:
        """The credits under the card (sounds, font…)."""
        return tr("Guitars: FluidR3_GM by Frank Wen (CC BY 3.0) · "
                  "Symbols: DejaVu Sans (Bitstream Vera license)")

    def sound_demo(self) -> None:
        """Plays the instrument just chosen (an arpeggiated C major
        chord). An app can play something else."""
        sound.playback().play(arpeggio(sound.synth(), (48, 55, 60, 64, 67)), self)

    # --- Saving ----------------------------------------------------------------------------
    def save(self, key: str, value) -> None:
        """Saves a setting and notifies the pages (bus.settings_changed)."""
        self.settings.setValue(key, value)
        log.info("setting %s = %s", key, value)
        bus.settings_changed.emit()

    def _on_language(self, *_) -> None:
        """Another language: the window is rebuilt in that language (boot.py)."""
        choice = self.language_box.currentData()
        self.settings.setValue("language", choice)
        log.info("setting language = %s", choice)
        code = i18n.resolve(choice)
        if code != i18n.language():
            i18n.set_language(code)
            bus.language_changed.emit()

    def _on_sound(self, *_) -> None:
        """Another instrument: save it, prepare its notes and play it."""
        voice = self.sound_box.currentData()
        if not sound.voice_allowed(voice):
            self.fill_sounds()            # back to the previous instrument
            self.voice_refused(voice)
            return
        key = sound.setting_key()
        self.settings.setValue(key, voice)
        log.info("setting %s = %s", key, voice)
        bus.settings_changed.emit()
        sound.start_warm_up()
        self.sound_demo()

    def _show_report(self) -> None:
        crash_report.show_over(self.window(), crash_report.full_report(), tr("Error report"),
                               can_clear=True)

    def _on_theme(self, *_) -> None:
        name = self.theme_box.currentData()
        self.settings.setValue("theme", name)
        log.info("setting theme = %s", name)
        apply_theme(QApplication.instance(), name)
        bus.settings_changed.emit()
