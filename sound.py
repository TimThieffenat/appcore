"""Accès partagé au son : une seule lecture et un seul synthétiseur pour l'app.

L'instrument est un réglage (clé SOUND_SETTING de app_info.py, par exemple
« sound/guitar »), choisi parmi les VOICES de l'app. Une app peut compléter ce
module dans son propre sound.py (`from appcore.sound import *` puis ses
raccourcis : jouer un accord, une question…).
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
_voice_allowed = None    # voir set_voice_filter


def set_voice_filter(allowed) -> None:
    """`allowed(voice) -> bool` : un instrument réservé (version Pro…) qui n'est
    pas permis redevient le premier de l'app. None : tous permis."""
    global _voice_allowed
    _voice_allowed = allowed


def voice_allowed(key: str) -> bool:
    if _voice_allowed is None:
        return True
    try:
        return bool(_voice_allowed(key))
    except Exception:  # noqa: BLE001 — en cas de doute : l'instrument de base
        return False


def playback() -> Playback:
    global _playback
    if _playback is None:
        _playback = Playback()
    return _playback


def voices() -> list[str]:
    """Les instruments que l'app propose (VOICES de app_info.py), dans l'ordre."""
    chosen = [v for v in app.get("VOICES") if v in VOICES]
    return chosen or [DEFAULT_VOICE]


def setting_key() -> str:
    return str(app.get("SOUND_SETTING"))


def voice() -> str:
    """L'instrument choisi dans les réglages (sinon le premier de l'app)."""
    available = voices()
    value = str(QSettings().value(setting_key(), available[0]))
    return value if value in available and voice_allowed(value) else available[0]


def synth() -> GuitarSynth:
    """Le synthétiseur de l'instrument choisi (refait si le réglage a changé)."""
    global _synth
    current = voice()
    if _synth is None or _synth.voice != current:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        cache = Path(base) / "sound_cache" if base else None
        _synth = GuitarSynth(playback().player.sample_rate, cache, current)
    return _synth


def start_warm_up() -> None:
    """Prépare les notes en arrière-plan (WARM_UP_NOTES de app_info.py :
    les plus utilisées d'abord)."""
    order = [int(n) for n in app.get("WARM_UP_NOTES")]
    threading.Thread(target=synth().warm_up, args=(order,), daemon=True).start()
