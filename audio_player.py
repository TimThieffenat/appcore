"""Lecture des sons de guitare avec Qt Multimedia.

- `AudioPlayer` mélange en continu les sons en cours (« voix ») et les envoie
  à la sortie audio, convertis au format de la carte son (stéréo, flottant…).
  Comme sur une guitare, une note ou un accord touché continue de sonner quand
  on en joue un autre : seule une corde rejouée coupe la note qu'elle portait.
  Une suite (lick, gamme, morceau) remplacée ou arrêtée s'éteint en un court
  fondu, sans claquement.
- `Playback` suit une lecture à la fois pour l'interface et appelle les pages
  au fil des événements (accord joué, note jouée…) pour les surligner.
Sans sortie audio, la lecture reste « visuelle » (le temps avance quand même).
"""

from __future__ import annotations

import logging
import threading
from array import array
from itertools import repeat
from operator import add, mul

from PySide6.QtCore import QElapsedTimer, QIODevice, QObject, Qt, QTimer

from appcore.guitar_synth import FAST, audioop, fade_out, mix

try:
    from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
    HAVE_AUDIO = True
except ImportError:
    HAVE_AUDIO = False

log = logging.getLogger(__name__)

<<<<<<< Updated upstream
BUFFER_SECONDS = 0.08
CUT_SECONDS = 0.012     # même corde rejouée : la note d'avant s'éteint aussitôt
FADE_SECONDS = 0.12     # suite remplacée ou arrêtée : fondu rapide
IDLE_STOP_MS = 1500     # plus rien à jouer depuis 1,5 s : la sortie audio s'arrête
=======
# Sound asked for in advance by the audio output: a touched note is heard that
# much later, so as little as possible (the metronome runs with the same 50 ms).
# If the sound crackles on a slow device, this is the value to raise.
BUFFER_SECONDS = 0.05
CUT_SECONDS = 0.012     # same string played again: the previous note stops at once
FADE_SECONDS = 0.12     # sequence replaced or stopped: quick fade
# Nothing left to play for 20 s: the audio output stops. Starting it again takes
# a moment (up to a tenth of a second on a phone), heard as a late first note:
# between two notes touched on the neck, the output stays open and plays silence.
IDLE_STOP_MS = 20000
>>>>>>> Stashed changes
IDLE_TICK_MS = 250


class _Voice:
    """Un son en cours : PCM 16 bits mono, à partir de l'image `start`."""

    __slots__ = ("pcm", "start", "strings", "one_shot")

    def __init__(self, pcm: bytes, start: int, strings: frozenset, one_shot: bool) -> None:
        self.pcm, self.start, self.strings, self.one_shot = pcm, start, strings, one_shot

    @property
    def end(self) -> int:
        return self.start + len(self.pcm) // 2

<<<<<<< Updated upstream
    def cut(self, at: int, fade: int) -> None:
        """S'éteint à partir de l'image `at`, en `fade` images."""
=======
    def cut(self, at: int, fade: int) -> "_Voice | None":
        """Dies out from frame `at`, over `fade` frames. The sound is not copied
        (a song weighs tens of megabytes, and the audio output waits meanwhile):
        the voice just stops at `at`, and its short fading end is returned as a
        voice of its own, to play with the others (None: nothing to cut)."""
>>>>>>> Stashed changes
        keep = at - self.start + fade
        if keep * 2 >= len(self.pcm):
            return None
        keep = max(0, keep)
        head = max(0, keep - fade)
        view = memoryview(self.pcm)
        end = fade_out(bytes(view[2 * head:2 * keep]), fade)
        self.pcm = view[:2 * head]
        return _Voice(end, self.start + head, self.strings, self.one_shot) if end else None


def _sum(frames: int, segments: list[tuple[int, bytes]]) -> bytes:
    """Somme de morceaux de PCM 16 bits mono placés dans `frames` images."""
    if not segments:
        return bytes(2 * frames)
    if len(segments) == 1 and segments[0][0] == 0 and len(segments[0][1]) == 2 * frames:
        return segments[0][1]
    if audioop:
        acc = bytearray(2 * frames)
        for offset, pcm in segments:
            a, b = 2 * offset, 2 * offset + len(pcm)
            acc[a:b] = audioop.add(bytes(acc[a:b]), pcm, 2)
        return bytes(acc)
<<<<<<< Updated upstream
    # Sans audioop (Python 3.13 et plus, donc l'app Android en Python 3.14) :
    # additions par tranches avec map(), sans boucle Python par échantillon
    # (ce code tourne pendant la lecture, à chaque bloc demandé par la sortie).
=======
    # Without audioop (Python 3.13 and later, so the Android app on Python 3.14):
    # this code runs during playback, for each block the output asks for.
    if FAST:   # big integers as vectors: no work per sample (see guitar_synth)
        return mix(frames, segments)
    # else additions by slices with map(), without a Python loop per sample
>>>>>>> Stashed changes
    total = array("i", bytes(4 * frames))
    for offset, pcm in segments:
        src = array("h")
        src.frombytes(pcm)
        end = offset + len(src)
        total[offset:end] = array("i", map(add, total[offset:end], src))
    if total and (min(total) < -32768 or max(total) > 32767):
        total = array("i", (32767 if x > 32767 else -32768 if x < -32768 else x for x in total))
    return array("h", total).tobytes()


class _Mix(QIODevice):
    """Fournit à la sortie audio la somme des voix en cours, au fil de l'eau
    (la sortie « tire » le son ; voir aussi metronome_engine)."""

    def __init__(self, convert, frame_bytes: int) -> None:
        super().__init__()
        self.convert = convert            # mono 16 bits -> format de la carte son
        self.frame_bytes = frame_bytes    # octets par image à la sortie
        self.lock = threading.Lock()      # la sortie peut lire depuis un autre fil
        self.voices: list[_Voice] = []
        self.frames = 0                   # images fournies depuis le départ de la sortie

    def reset(self) -> None:
        with self.lock:
            self.voices = []
            self.frames = 0

    def add(self, pcm: bytes, strings: frozenset, one_shot: bool, sample_rate: int) -> int:
        """Ajoute un son à partir de la prochaine image fournie et coupe ce qu'il
        remplace. Renvoie l'image de départ du son."""
        with self.lock:
            now = self.frames
            voices = []
            for voice in self.voices:
                if voice.end <= now:
                    continue
<<<<<<< Updated upstream
                if not voice.one_shot:        # une suite s'arrête
                    voice.cut(now, int(FADE_SECONDS * sample_rate))
                elif voice.strings & strings:  # corde rejouée
                    voice.cut(now, int(CUT_SECONDS * sample_rate))
=======
                end = None
                if not voice.one_shot:        # a sequence stops
                    end = voice.cut(now, int(FADE_SECONDS * sample_rate))
                elif voice.strings & strings:  # string played again
                    end = voice.cut(now, int(CUT_SECONDS * sample_rate))
>>>>>>> Stashed changes
                voices.append(voice)
                if end is not None:
                    voices.append(end)
            voices.append(_Voice(pcm, now, strings, one_shot))
            self.voices = voices
            return now

    def fade_all(self, fade: int) -> None:
        with self.lock:
            ends = [voice.cut(self.frames, fade) for voice in self.voices]
            self.voices += [end for end in ends if end is not None]

    def silent(self) -> bool:
        with self.lock:
            return all(voice.end <= self.frames for voice in self.voices)

    def readData(self, maxlen: int) -> bytes:
        frames = maxlen // self.frame_bytes
        if frames <= 0:
            return b""
        with self.lock:
            t0 = self.frames
            t1 = self.frames = t0 + frames
            self.voices = [v for v in self.voices if v.end > t0]
            segments = []
            for voice in self.voices:
                a, b = max(t0, voice.start), min(t1, voice.end)
                if a < b:
                    segments.append((a - t0, voice.pcm[2 * (a - voice.start):2 * (b - voice.start)]))
        if not segments:   # silence (the output stays open between two notes): nothing to compute
            return bytes(frames * self.frame_bytes)
        return self.convert(_sum(frames, segments))

    def writeData(self, data) -> int:
        return 0

    def bytesAvailable(self) -> int:
        return 1 << 20

    def isSequential(self) -> bool:
        return True


class AudioPlayer(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.audio_ok = False
        self.sample_rate = 44100
        self.channels = 1
        self.float_samples = False
        self.sink = None
        self._clock = QElapsedTimer()
        self._running = False
        self._start = 0           # image de départ du dernier son lancé
        self._quiet_ticks = 0
        self._idle = QTimer(self)
        self._idle.setInterval(IDLE_TICK_MS)
        self._idle.timeout.connect(self._check_idle)
        fmt = self._choose_format() if HAVE_AUDIO else None
        if fmt is not None:
            self.sample_rate = fmt.sampleRate()
            self.channels = fmt.channelCount()
            self.float_samples = fmt.sampleFormat() == QAudioFormat.SampleFormat.Float
            self.sink = QAudioSink(QMediaDevices.defaultAudioOutput(), fmt)
            frame = self.channels * (4 if self.float_samples else 2)
            self.sink.setBufferSize(int(self.sample_rate * BUFFER_SECONDS) * frame)
            self.audio_ok = True
            log.info("sound: %d Hz, %d channel(s), %s", self.sample_rate, self.channels,
                     "float" if self.float_samples else "16 bits")
        else:
            log.warning("no sound: %s", "no audio output found" if HAVE_AUDIO
                        else "Qt Multimedia is missing")
        self._mix = _Mix(self._convert, self.channels * (4 if self.float_samples else 2))
        self._mix.open(QIODevice.OpenModeFlag.ReadOnly)

    @staticmethod
    def _choose_format():
        try:
            device = QMediaDevices.defaultAudioOutput()
        except Exception:
            log.warning("audio output unavailable", exc_info=True)
            return None
        if device.isNull():
            return None
        preferred = device.preferredFormat()
        for sample_format in (QAudioFormat.SampleFormat.Int16, QAudioFormat.SampleFormat.Float):
            fmt = QAudioFormat()
            fmt.setSampleRate(preferred.sampleRate() or 44100)
            fmt.setChannelCount(max(1, preferred.channelCount()))
            fmt.setSampleFormat(sample_format)
            if device.isFormatSupported(fmt):
                return fmt
        log.warning("audio output: no supported format (preferred %d Hz, %d channel(s))",
                    preferred.sampleRate(), preferred.channelCount())
        return None

    def _convert(self, pcm: bytes) -> bytes:
        """Mono 16 bits -> format de la carte son (canaux, flottant)."""
        src = array("h")
        src.frombytes(pcm)
        if self.float_samples:
            src = array("f", map(mul, src, repeat(1.0 / 32768.0)))
        if self.channels == 1:
            return src.tobytes()
        out = array(src.typecode, bytes(src.itemsize * len(src) * self.channels))
        for c in range(self.channels):
            out[c::self.channels] = src
        return out.tobytes()

    def play(self, pcm: bytes, strings: frozenset = frozenset(), one_shot: bool = False) -> None:
        """Ajoute un son à ce qui sonne déjà (voir _Mix.add pour ce qu'il coupe)."""
        self._clock.start()
        if not self.audio_ok:
            return
        if not self._running:
            self._mix.reset()
        self._start = self._mix.add(pcm, strings, one_shot, self.sample_rate)
        self._quiet_ticks = 0
        if not self._running:
            self._running = True
            self.sink.start(self._mix)
            if getattr(self.sink.error(), "name", "NoError") != "NoError":
                log.warning("sound can't start: %s", getattr(self.sink.error(), "name", "?"))
                self.audio_ok = False
                self._running = False
                return
            self._idle.start()

    def stop(self, fade: bool = True) -> None:
        """Éteint tout ce qui sonne : en un court fondu, ou tout de suite
        (`fade=False`, par ex. quand l'app passe en arrière-plan)."""
        if not (self.audio_ok and self._running):
            return
        if fade:
            self._mix.fade_all(int(FADE_SECONDS * self.sample_rate))
        else:
            self._halt()

    def _halt(self) -> None:
        self._idle.stop()
        self._running = False
        self._quiet_ticks = 0
        if self.sink is not None:
            self.sink.stop()
        self._mix.reset()

    def _check_idle(self) -> None:
        """Plus rien ne sonne depuis un moment : on libère la sortie audio."""
        if not self._running:
            return
        if not self._mix.silent():
            self._quiet_ticks = 0
            return
        self._quiet_ticks += 1
        if self._quiet_ticks * IDLE_TICK_MS >= IDLE_STOP_MS:
            self._halt()

    def position(self) -> float:
        """Temps écoulé depuis le début du dernier son lancé (ce qu'on entend)."""
        if self.audio_ok and self._running:
            return self.sink.processedUSecs() / 1_000_000 - self._start / self.sample_rate
        return self._clock.elapsed() / 1000


class Playback(QObject):
    """Une seule lecture suivie à la fois par l'interface ; surligne au fil des
    événements. Le son d'avant, lui, peut continuer de sonner (AudioPlayer)."""

    def __init__(self) -> None:
        super().__init__()
        self.player = AudioPlayer()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self._tick)
        self.performance = None
        self.owner = None
        self._on_event = None
        self._on_finish = None
        self._next = 0

    @property
    def audio_ok(self) -> bool:
        return self.player.audio_ok

    def play(self, performance, owner=None, on_event=None, on_finish=None) -> None:
        self._end()   # l'interface de la lecture d'avant (son géré par le lecteur)
        self.performance, self.owner = performance, owner
        self._on_event, self._on_finish = on_event, on_finish
        self._next = 0
        self.player.play(performance.pcm, getattr(performance, "strings", frozenset()),
                         getattr(performance, "one_shot", False))
        self.timer.start()
        self._tick()

    def is_playing(self, owner=None) -> bool:
        return self.performance is not None and (owner is None or owner is self.owner)

    def position(self) -> float:
        return self.player.position() if self.performance is not None else 0.0

    def stop(self, fade: bool = True) -> None:
        """Arrête la lecture et éteint ce qui sonne encore (fondu rapide)."""
        self.player.stop(fade)
        self._end()

    def _end(self) -> None:
        if self.performance is None:
            return
        self.timer.stop()
        callback = self._on_finish
        self.performance = self.owner = self._on_event = self._on_finish = None
        if callback:
            callback()

    def _tick(self) -> None:
        perf = self.performance
        if perf is None:
            return
        pos = self.player.position()
        if pos >= perf.duration:
            self._end()   # le son, fini lui aussi, ne coupe rien
            return
        last = None
        while self._next < len(perf.events) and perf.events[self._next][0] <= pos:
            last = perf.events[self._next][1]
            self._next += 1
        if last is not None and self._on_event:
            self._on_event(last)
