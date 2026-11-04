"""Signaux partagés entre les pages (ex. : les réglages ont changé)."""

from PySide6.QtCore import QObject, Signal


class _Bus(QObject):
    settings_changed = Signal()   # un réglage a changé : les pages se redessinent
    language_changed = Signal()   # boot.py refait la fenêtre dans la nouvelle langue
    profile_changed = Signal()    # les données de l'utilisateur ont changé (progression,
                                  # favoris…) : les pages qui les montrent se mettent à jour
    pro_changed = Signal()        # achat dans l'app (version Pro) : acquis, prix ou état


bus = _Bus()
