"""The base's "Settings" page: language, theme, note names, sound, error
report, and the app's own settings.

Each app makes a subclass of it (its page_settings.py) that adds its
rows by overriding rows(), and possibly sound_demo(), credits(),
voice_text() / voice_refused():

    class SettingsPage(BaseSettingsPage):
        SOUND_LABEL = N_("Guitar sound")

        def rows(self):
            self.capo_box = ui.combo(chars=18, min_width=200)
            ...
            return self.pro_rows() + [
                    self.language_row(), self.theme_row(), self.notation_row(),
                    (tr("Capo"), self.capo_box), self.sound_row(), self.report_row()]

Rows are set with save(key, value): the setting is saved,
written to the log, and the pages redrawn (bus.settings_changed).

An app with a Pro version (PRO_PRODUCT of app_info.py, see pro.py) puts
pro_rows() first: "<App> Pro" (button "Discover Pro", which calls the window's
open_pro(), or "Unlocked ♛"), then the unlock code for Google Play's reviewers
while Pro is closed (UNLOCK_CODE_SHA256). The instruments of PRO_VOICES show
"(Pro)" and choosing one without Pro opens the Pro version (open_pro()).
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

from appcore import app, crash_report, i18n, pro, sound
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
        self._form = form
        if pro.enabled():
            bus.pro_changed.connect(self._on_pro_changed)
            self._on_pro_changed()
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
        return self.pro_rows() + [self.language_row(), self.theme_row(),
                                  self.notation_row(), self.sound_row(), self.report_row()]

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
        """The text of an instrument in the list ("(Pro)" for those of PRO_VOICES
        while Pro is closed)."""
        text = tr(VOICES[key][0])
        if key in sound.pro_voices() and not pro.is_pro():
            text = tr("{name} (Pro)", name=text)
        return text

    def voice_refused(self, key: str) -> None:
        """A non-allowed instrument was chosen (PRO_VOICES, sound.set_voice_filter):
        the list goes back to the previous instrument, and the Pro version is shown."""
        if key in sound.pro_voices():
            self.open_pro()

    # --- Pro version (pro.py) --------------------------------------------------------------
    def pro_rows(self) -> list[tuple[str, QWidget]]:
        """"<App> Pro" and, while Pro is closed, the unlock code ([] in an app
        without a Pro version)."""
        if not pro.enabled():
            return []
        self.pro_button = QPushButton("")
        self.pro_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pro_button.clicked.connect(lambda *_: self.open_pro())
        rows = [(tr("{app} Pro", app=app.name()), self.pro_button)]
        if pro.code_enabled():
            self.code_row = self._code_row()
            rows.append((tr("Unlock code"), self.code_row))
        return rows

    def open_pro(self) -> None:
        """What the Pro version opens (the window decides: a page, a sheet…)."""
        window = self.window()
        if hasattr(window, "open_pro"):
            window.open_pro()

    def _on_pro_changed(self, *_) -> None:
        owned = pro.is_pro()
        button = getattr(self, "pro_button", None)
        if button is not None:
            button.setText(tr("Unlocked ♛") if owned else tr("Discover Pro"))
            button.setObjectName("toggle" if owned else "primary")
            button.style().unpolish(button)
            button.style().polish(button)
        row = getattr(self, "code_row", None)
        if row is not None and self._form.indexOf(row) >= 0:
            self._form.setRowVisible(row, not owned)   # the code row only while Pro is closed
        if hasattr(self, "sound_box") and sound.pro_voices():
            self.fill_sounds()

    def _code_row(self) -> QWidget:
        """The unlock code field + "Unlock", and an error line below."""
        from appcore.touch_input import close_keyboard_later

        self.code_edit = ui.text_field(tr("Enter your code"), max_length=40)
        self.code_edit.setInputMethodHints(Qt.InputMethodHint.ImhNoPredictiveText
                                           | Qt.InputMethodHint.ImhPreferUppercase)
        self.code_status = ui.label("", "muted", wrap=True)
        self.code_status.hide()

        def redeem() -> None:
            text = self.code_edit.text()
            if not text.strip():
                return
            close_keyboard_later(self.code_edit)
            if pro.redeem(text):
                self.code_edit.clear()        # Pro unlocked: the row disappears
                return
            self.code_status.setText(tr("This code is not valid."))
            self.code_status.show()

        self.code_edit.returnPressed.connect(redeem)
        self.code_edit.textEdited.connect(lambda *_: self.code_status.hide())
        button = QPushButton(tr("Unlock"))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(lambda *_: redeem())

        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(6)
        line.addWidget(self.code_edit, 1)
        line.addWidget(button)
        box = QWidget()
        column = QVBoxLayout(box)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)
        column.addLayout(line)
        column.addWidget(self.code_status)
        return box

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
