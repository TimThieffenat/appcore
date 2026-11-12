"""Shared access to sound: a single playback and a single synthesiser for the app.

The instrument is a setting (key SOUND_SETTING of app_info.py, for example
"sound/guitar"), chosen among the app's VOICES. An app can extend this
module in its own sound.py (`from appcore.sound import *` then its
shortcuts: play a chord, a question…).
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

from appcore import app
from appcore.audio_player import Playback
from appcore.guitar_synth import DEFAULT_VOICE, VOICES, GuitarSynth

_playback: Playback | None = None
_synth: GuitarSynth | None = None
_voice_allowed = None    # see set_voice_filter


def set_voice_filter(allowed) -> None:
    """`allowed(voice) -> bool`: a reserved instrument (Pro version…) that is
    not allowed falls back to the app's first one. None: all allowed."""
    global _voice_allowed
    _voice_allowed = allowed


def pro_voices() -> tuple[str, ...]:
    """The instruments reserved to the Pro version (PRO_VOICES of app_info.py)."""
    from appcore import pro
    return tuple(app.get("PRO_VOICES", ()) or ()) if pro.enabled() else ()


def voice_allowed(key: str) -> bool:
    if key in pro_voices():
        from appcore import pro
        if not pro.is_pro():
            return False
    if _voice_allowed is None:
        return True
    try:
        return bool(_voice_allowed(key))
    except Exception:  # noqa: BLE001 — when in doubt: the basic instrument
        return False


def playback() -> Playback:
    global _playback
    if _playback is None:
        _playback = Playback()
    return _playback


def voices() -> list[str]:
    """The instruments the app offers (VOICES of app_info.py), in order."""
    chosen = [v for v in app.get("VOICES") if v in VOICES]
    return chosen or [DEFAULT_VOICE]


def setting_key() -> str:
    return str(app.get("SOUND_SETTING"))


def voice() -> str:
    """The instrument chosen in the settings (else the app's first one)."""
    available = voices()
    value = str(QSettings().value(setting_key(), available[0]))
    return value if value in available and voice_allowed(value) else available[0]


def synth() -> GuitarSynth:
    """The synthesiser of the chosen instrument (rebuilt if the setting changed)."""
    global _synth
    current = voice()
    if _synth is None or _synth.voice != current:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        cache = Path(base) / "sound_cache" if base else None
        _synth = GuitarSynth(playback().player.sample_rate, cache, current)
    return _synth


def start_warm_up() -> None:
    """Prepares the notes in the background (WARM_UP_NOTES of app_info.py:
    most used first)."""
    order = [int(n) for n in app.get("WARM_UP_NOTES")]
    threading.Thread(target=synth().warm_up, args=(order,), daemon=True).start()
