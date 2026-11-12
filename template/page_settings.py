"""The "Settings" page: the base's one (language, theme, note names,
instrument, error report). To add a setting, override rows():

    def rows(self):
        self.speed_box = ui.combo(chars=18, min_width=200)
        ...
        self.speed_box.currentIndexChanged.connect(
            lambda *_: self.save("speed", self.speed_box.currentData()))
        return [self.language_row(), self.theme_row(), self.notation_row(),
                (tr("Speed"), self.speed_box), self.sound_row(), self.report_row()]

save(key, value) saves the setting, writes it to the log and notifies
the pages (bus.settings_changed). credits() gives the text under the card.
"""

from __future__ import annotations

from appcore.i18n import N_
from appcore.page_settings import SettingsPage as BaseSettingsPage


class SettingsPage(BaseSettingsPage):
    SOUND_LABEL = N_("Instrument")
