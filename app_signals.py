"""Signals shared between pages (e.g. the settings changed)."""

from PySide6.QtCore import QObject, Signal


class _Bus(QObject):
    settings_changed = Signal()   # a setting changed: pages redraw
    language_changed = Signal()   # boot.py rebuilds the window in the new language
    profile_changed = Signal()    # the user's data changed (progress,
                                  # favourites…): pages showing it update
    pro_changed = Signal()        # in-app purchase (Pro version): owned, price or state


bus = _Bus()
