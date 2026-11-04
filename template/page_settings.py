"""Page « Settings » : celle du socle (langue, thème, noms des notes,
instrument, rapport d'erreur). Pour ajouter un réglage, redéfinir rows() :

    def rows(self):
        self.speed_box = ui.combo(chars=18, min_width=200)
        ...
        self.speed_box.currentIndexChanged.connect(
            lambda *_: self.save("speed", self.speed_box.currentData()))
        return [self.language_row(), self.theme_row(), self.notation_row(),
                (tr("Speed"), self.speed_box), self.sound_row(), self.report_row()]

save(clé, valeur) enregistre le réglage, l'écrit dans le journal et prévient
les pages (bus.settings_changed). credits() donne le texte sous la carte.
"""

from __future__ import annotations

from appcore.i18n import N_
from appcore.page_settings import SettingsPage as BaseSettingsPage


class SettingsPage(BaseSettingsPage):
    SOUND_LABEL = N_("Instrument")
