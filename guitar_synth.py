"""The sound of notes: recorded acoustic guitar, or synthesised keyboard.

Three instruments: steel-string guitar (sounds/guitar), nylon-string guitar
(sounds/guitar_nylon), see sounds/CREDITS.md, and a soft synthesised keyboard
(for musicians who do not play the guitar). A note with no recording is obtained by transposing the
nearest one. If the files are missing, a synthesised plucked string
(Karplus-Strong) takes over.

Each app chooses the instruments it offers (VOICES of its app_info.py).
`played(..., cents=…)` gives a deliberately detuned note; the "keys"
voice (keyboard) is computed note by note. The recordings are in
appcore/sounds/ (see sounds/CREDITS.md), shared by all apps.

Without Qt and without external dependencies:
- each pitch is prepared once, kept in memory and, if a cache folder
  is given, on disk (instant afterwards);
- mixing uses the standard "audioop" module when it exists
  (Python ≤ 3.12), otherwise big integers used as vectors of samples
  (see "PCM arithmetic without audioop"): no work per sample in Python.
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
>>>>>>> cd8568b2db1df3c3447fb719d6d9f9337386d048

Output format: signed 16-bit PCM, mono, at the chosen sample rate
(the audio output's).
"""

from __future__ import annotations

import logging
import math
import random
import struct
import sys
import threading
import warnings
import zlib
from array import array
from itertools import repeat
from operator import add, mul, sub, truediv
from dataclasses import dataclass, field
from pathlib import Path

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    try:  # fast (C code); removed in Python 3.13 (else the "audioop-lts" package)
        import audioop
    except ImportError:
        audioop = None

log = logging.getLogger(__name__)

CACHE_VERSION = "v2"   # v2: real recordings
SOUNDS_DIR = Path(__file__).with_name("sounds")
GUITAR_DIR = SOUNDS_DIR / "guitar"
# Instruments to choose from: name -> (label, recordings folder or None)
VOICES = {
    "steel": ("Steel-string acoustic", "guitar"),
    "nylon": ("Nylon-string (classical)", "guitar_nylon"),
    "keys": ("Soft keys (all musicians)", None),
}
DEFAULT_VOICE = "steel"
KEYS_RATE = 22050      # the keyboard is computed at this rate, then converted
# Notes at a given volume are kept ready (a touched note then sounds at once); a
# note is about 250 KB: beyond this size, they are dropped and prepared again
# when needed.
VARIANTS_BYTES = 64 * 1024 * 1024
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
>>>>>>> cd8568b2db1df3c3447fb719d6d9f9337386d048


def voice_dir(voice: str) -> Path | None:
    folder = VOICES.get(voice, VOICES[DEFAULT_VOICE])[1]
    return SOUNDS_DIR / folder if folder else None


def load_snd(path: Path) -> tuple[int, bytes] | None:
    """.snd file: zlib( rate uint32 + 16-bit mono PCM ). None if unreadable."""
    try:
        data = zlib.decompress(path.read_bytes())
    except (OSError, zlib.error):
        return None
    if len(data) < 8:
        return None
    rate = struct.unpack("<I", data[:4])[0]
    pcm = data[4:4 + (len(data) - 4) // 2 * 2]
    if sys.byteorder != "little":
        samples = array("h")
        samples.frombytes(pcm)
        samples.byteswap()
        pcm = samples.tobytes()
    return rate, pcm


def resample(pcm: bytes, in_rate: float, out_rate: int) -> bytes:
    """Changes the sample rate. With in_rate higher than the recording's
    real rate, the note is transposed upwards."""
    in_rate = max(1, int(round(in_rate)))
    if in_rate == out_rate:
        return pcm
    if audioop:
        return audioop.ratecv(pcm, 2, 1, in_rate, out_rate, None)[0]
    # Without audioop (Python 3.13 and later, so the Android app on Python 3.14):
    # linear interpolation written with map() and the operator module's
    # functions, without a Python loop per sample (about 10 times faster).
    src = array("h")
    src.frombytes(pcm)
    if len(src) < 2:
        return pcm
    src.append(src[-1])              # the last sample has a neighbour
    step = in_rate / out_rate
    count = int((len(src) - 2) / step)
    pos = list(map(mul, range(count), repeat(step)))
    idx = list(map(int, pos))
    a = list(map(src.__getitem__, idx))
    b = map(src.__getitem__, map(add, idx, repeat(1)))
    out = map(add, a, map(mul, map(sub, b, a), map(sub, pos, idx)))
    return array("h", map(int, out)).tobytes()

_SAMPLE_NOTES: dict[str, list[int]] = {}


def sample_notes(voice: str = DEFAULT_VOICE) -> list[int]:
    """The recorded MIDI notes of a guitar (empty if the folder is missing)."""
    if voice not in _SAMPLE_NOTES:
        folder = voice_dir(voice)
        try:
            _SAMPLE_NOTES[voice] = sorted(int(p.stem) for p in folder.glob("*.snd")
                                          if p.stem.isdigit()) if folder else []
        except OSError:
            _SAMPLE_NOTES[voice] = []
        if not _SAMPLE_NOTES[voice] and voice in VOICES and VOICES[voice][1]:
            log.warning("no recorded notes for the %s guitar: synthesised sound", voice)
    return _SAMPLE_NOTES[voice]


def midi_freq(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def _to_int16(samples) -> array:
    peak = max(1e-9, max(abs(s) for s in samples))
    k = 0.9 * 32767 / peak
    return array("h", (int(s * k) for s in samples))


def pluck(freq: float, sample_rate: int, seconds: float, seed: int = 7,
          pick_position: float = 0.14) -> array:
    """Plucked string: filtered noise looping in a delay line."""
    period = sample_rate / freq
    length = int(period - 0.5)
    frac = period - 0.5 - length
    if frac < 0.1:  # keeps the all-pass filter stable
        length -= 1
        frac += 1.0
    length = max(2, length)
    coef = (1.0 - frac) / (1.0 + frac)  # fractional delay: exact tuning

    rnd = random.Random(seed)
    excite = [rnd.uniform(-1.0, 1.0) for _ in range(length)]
    for _ in range(2):  # softer attack (a pick, not a razor blade)
        excite = [0.5 * (excite[i] + excite[i - 1]) for i in range(length)]
    gap = max(1, int(round(pick_position * length)))  # pick position
    excite = [excite[i] - 0.7 * excite[i - gap] for i in range(length)]
    mean = sum(excite) / length
    buf = [x - mean for x in excite]

    # decay: low notes ring longer than high ones
    t60 = max(1.6, min(6.0, 8.2 - 0.072 * (12 * math.log2(freq / 440.0) + 69)))
    decay = 0.001 ** (1.0 / (t60 * freq))

    total = int(sample_rate * seconds)
    out = array("f", bytes(4 * total))
    idx = 0
    prev = 0.0
    ap_x = ap_y = 0.0
    body = 0.0
    for n in range(total):
        x = buf[idx]
        lp = 0.5 * (x + prev)
        prev = x
        ap = coef * lp + ap_x - coef * ap_y
        ap_x, ap_y = lp, ap
        buf[idx] = decay * ap
        idx += 1
        if idx == length:
            idx = 0
        body += 0.45 * (x - body)  # slight warmth (low-pass)
        out[n] = body
    # tiny fade in / out: no click
    fade_in = min(total, int(0.002 * sample_rate))
    for i in range(fade_in):
        out[i] *= i / fade_in
    fade_out = min(total, int(0.05 * sample_rate))
    for i in range(fade_out):
        out[total - 1 - i] *= i / fade_out
    return _to_int16(out)


def noise_burst(sample_rate: int, seconds: float = 0.035, seed: int = 3) -> array:
    """Muted strum ("chuck"): very short dull noise."""
    rnd = random.Random(seed)
    total = int(sample_rate * seconds)
    out = []
    low = 0.0
    for n in range(total):
        low += 0.25 * (rnd.uniform(-1, 1) - low)
        out.append(low * math.exp(-n / (0.008 * sample_rate)))
    return _to_int16(out)


def keys_tone(freq: float, sample_rate: int = KEYS_RATE, seconds: float = 2.2) -> array:
    """Soft keyboard note (electric piano): a few harmonics that
    die out, the high ones faster, and a slight "tine" at the attack."""
    total = int(sample_rate * seconds)
    out = array("f", bytes(4 * total))
    nyquist = sample_rate / 2
    # (harmonic rank, volume, decay time in s)
    partials = [(1.0, 1.0, 1.25), (2.0, 0.42, 0.65), (3.0, 0.20, 0.42),
                (4.0, 0.10, 0.30), (5.0, 0.05, 0.22), (7.03, 0.10, 0.05)]
    low_boost = max(0.0, min(1.0, (300.0 - freq) / 250.0))   # rounder low notes
    for ratio, amp, tau in partials:
        f = freq * ratio
        if f >= nyquist * 0.9:
            continue
        if ratio > 1:
            amp *= 1.0 - 0.5 * low_boost
        tau *= max(0.5, min(1.6, 440.0 / freq) ** 0.35)
        w = 2 * math.pi * f / sample_rate
        # sine by rotation (2 multiplications per sample)
        c, s = math.cos(w), math.sin(w)
        x, y = 1.0, 0.0
        k = math.exp(-1.0 / (tau * sample_rate))
        env = amp
        for n in range(total):
            out[n] += env * y
            x, y = x * c - y * s, x * s + y * c
            env *= k
    attack = int(0.004 * sample_rate)
    for i in range(min(attack, total)):
        out[i] *= i / attack
    tail = min(total, int(0.08 * sample_rate))
    for i in range(tail):
        out[total - 1 - i] *= i / tail
    return _to_int16(out)


# --- PCM arithmetic without audioop: big integers as vectors -------------------------------
#
# Without audioop (Python 3.13 and later, so the Android app), anything done sample
# by sample costs about 50 ns per sample, even hidden in map(): on a fast computer,
# mixing a four-minute song took 8 s (and froze the screen for half a second at
# a time), one touched note 20 ms; a phone is several times slower. Python's big
# integers do the same sums at the speed of a memory copy: a sound becomes ONE integer whose
# 32-bit "digits" are its samples, and adding two such integers adds all their
# samples at once. A sound is split in two integers (its samples of even rank and
# of odd rank): 16-bit samples then sit in 32-bit digits, with room for the sum of
# thousands of sounds. Samples are stored + 32768 (0..65535) so that no digit is
# negative: digits never borrow from their neighbours, and a slice of the integer
# is a slice of the sound.

FAST = audioop is None and sys.byteorder == "little"   # this arithmetic is in use
_ONES = (1, 1)   # (count, the integer made of `count` digits worth 1)


def _ones(count: int) -> int:
    """`count` 32-bit digits all worth 1: `k * _ones(n)` writes k in n digits."""
    global _ONES
    have, value = _ONES
    while have < count:
        value |= value << (32 * have)
        have *= 2
        _ONES = (have, value)   # one assignment: safe from several threads
    return value >> (32 * (have - count)) if count > 0 else 0


def _digits(pcm, count: int) -> tuple[int, int]:
    """16-bit PCM of `count` samples -> (samples of even rank, of odd rank), each
    an integer of 32-bit digits worth sample + 32768."""
    raw = int.from_bytes(pcm, "little")
    n_even, n_odd = (count + 1) // 2, count // 2
    even = (raw & (0xFFFF * _ones(n_even))) ^ (0x8000 * _ones(n_even))
    odd = ((raw >> 16) & (0xFFFF * _ones(n_odd))) ^ (0x8000 * _ones(n_odd))
    return even, odd


def _pcm(even: int, odd: int, count: int) -> bytes:
    """The reverse of _digits: digits worth sample + 32768 -> 16-bit PCM."""
    n_even, n_odd = (count + 1) // 2, count // 2
    raw = (even ^ (0x8000 * _ones(n_even))) | ((odd ^ (0x8000 * _ones(n_odd))) << 16)
    return raw.to_bytes(2 * count, "little")


def _clamp(total: int, count: int) -> int:
    """Digits worth sum + 2**31 + 32768 -> digits worth sample + 32768, the sum
    brought back between -32768 and 32767 (all the digits at once)."""
    ones = _ones(count)
    if total & (0xFFFF0000 * ones) == 0x80000000 * ones:   # nothing goes over: the usual case
        return total & (0xFFFF * ones)
    under = ((total >> 31) & ones) ^ ones                  # 1 where the sum < -32768
    high = (total >> 16) & (0x7FFF * ones)
    over = (((high + 0x7FFF * ones) >> 15) & ones) & (under ^ ones)   # 1 where the sum > 32767
    return ((total & (0xFFFF * ones)) | (over * 0xFFFF)) & ~(under * 0xFFFF)


def _finish(even: int, odd: int, count: int) -> bytes:
    """Sums (integers of signed digits, even and odd ranks) -> clipped 16-bit PCM."""
    n_even, n_odd = (count + 1) // 2, count // 2
    return _pcm(_clamp(even + 0x80008000 * _ones(n_even), n_even),
                _clamp(odd + 0x80008000 * _ones(n_odd), n_odd), count)


def _signed(pcm, count: int) -> tuple[int, int]:
    """Like _digits, with digits worth the sample itself (signed): ready to be
    added to a sum. Such an integer can no longer be sliced."""
    even, odd = _digits(pcm, count)
    return (even - 0x8000 * _ones((count + 1) // 2), odd - 0x8000 * _ones(count // 2))


def mix(frames: int, segments) -> bytes:
    """Sum of 16-bit mono PCM pieces [(offset in frames, pcm)] placed in `frames`
    frames, clipped: what audioop would do, when it is missing (see FAST). The
    pieces must fit in the frames; made for short blocks (the audio output's)."""
    even = odd = 0
    for offset, pcm in segments:
        e, o = _signed(pcm, len(pcm) // 2)
        if offset % 2 == 0:
            even += e << (16 * offset)
            odd += o << (16 * offset)
        else:   # shifted by one sample: the ranks swap
            odd += e << (16 * (offset - 1))
            even += o << (16 * (offset + 1))
    return _finish(even, odd, frames)


_CHUNK = 1 << 18   # samples handled at once: a whole note, yet integers of 1 MB at most


def _scale_fast(pcm: bytes, gain: float) -> bytes:
    """pcm * gain for 0 <= gain <= 1, to the nearest 1/32768 (rounded down)."""
    g = int(round(gain * 32768))
    out = []
    for start in range(0, len(pcm) // 2, _CHUNK):
        chunk = pcm[2 * start:2 * (start + _CHUNK)]
        count = len(chunk) // 2
        scaled = []
        for digits, n in zip(_digits(chunk, count), ((count + 1) // 2, count // 2)):
            ones = _ones(n)
            # digit = sample + 32768, so (digit * g) >> 15 = (sample * g >> 15) + g
            scaled.append(((digits * g >> 15) & (0xFFFF * ones)) + (32768 - g) * ones)
        out.append(_pcm(scaled[0], scaled[1], count))
    return b"".join(out)


# --- PCM operations (audioop if available) ----------------------------------------------
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
>>>>>>> cd8568b2db1df3c3447fb719d6d9f9337386d048

def scale(pcm: bytes, gain: float) -> bytes:
    if gain == 1.0:
        return pcm
    if audioop:
        return audioop.mul(pcm, 2, gain)
    if FAST and 0.0 <= gain <= 1.0:
        return _scale_fast(pcm[:len(pcm) // 2 * 2], gain)
    data = array("h")
    data.frombytes(pcm)
    values = array("i", map(int, map(mul, data, repeat(gain))))   # without a Python loop
    if values and (min(values) < -32768 or max(values) > 32767):  # gain > 1: clip
        values = array("i", (max(-32768, min(32767, x)) for x in values))
    return array("h", values).tobytes()


def _ramp(samples: array, weights) -> bytes:
    """Each sample * its weight / len(samples), without a Python loop."""
    scaled = map(truediv, map(mul, samples, weights), repeat(len(samples)))
    return array("h", map(int, scaled)).tobytes()


def fade_out(pcm: bytes, samples: int) -> bytes:
=======
    """Fade out over the last `samples` samples."""
>>>>>>> cd8568b2db1df3c3447fb719d6d9f9337386d048
    samples = min(samples, len(pcm) // 2)
    if samples <= 0:
        return pcm
    tail = array("h")
    tail.frombytes(pcm[len(pcm) - 2 * samples:])
    return pcm[:len(pcm) - 2 * samples] + _ramp(tail, range(samples, 0, -1))


def fade_in(pcm: bytes, samples: int) -> bytes:
    samples = min(samples, len(pcm) // 2)
    if samples <= 0:
        return pcm
    head = array("h")
    head.frombytes(pcm[:2 * samples])
    return _ramp(head, range(samples)) + pcm[2 * samples:]


@dataclass
class Performance:
    """A sound ready to play: 16-bit mono PCM, its duration, and events
    (time, value) the interface uses to highlight what plays
    (audio_player.Playback). Apps build them (their performance.py)."""

    pcm: bytes
    sample_rate: int
    duration: float
    events: list[tuple[float, object]] = field(default_factory=list)
    # A "struck" sound (a note, a chord): the next sound does not cut it, it
    # keeps ringing, except on the strings the next one plays again. A sequence
    # (lick, scale, song) dies out when something else is played.
    one_shot: bool = False
    strings: frozenset[int] = frozenset()   # strings played (index in the tuning)


def arpeggio(synth: "GuitarSynth", midis, step: float = 0.18, seconds: float = 1.6,
             gain: float = 0.55) -> Performance:
    """Notes played one after the other (trying an instrument, settings)."""
    sr = synth.sample_rate
    midis = list(midis)
    total = step * max(0, len(midis) - 1) + seconds + 0.3
    mixer = Mixer(sr, total)
    for i, midi in enumerate(midis):
        mixer.add(synth.played(midi, gain, seconds), i * step)
    return Performance(mixer.to_bytes(), sr, total, [])


class Mixer:
    """Sum of sounds placed in time, each with its volume.

    `seconds`: the length of the whole. None when it is not known in advance:
    the mix then grows with the sounds added (each one can be mixed as soon as
    it is ready, without keeping them all), and to_bytes(seconds) gives it its
    final length.
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
>>>>>>> cd8568b2db1df3c3447fb719d6d9f9337386d048

    Without audioop (Python 3.13 and later, so the Android app on Python 3.14),
    the sum is kept in big integers (see "PCM arithmetic without audioop"), by
    blocks of BLOCK samples: adding a sound only touches the blocks it covers,
    whatever the length of the whole. Clipping only happens at the end."""

    BLOCK = 16384   # samples per block (even)

    def __init__(self, sample_rate: int, seconds: float | None = None) -> None:
        self.sample_rate = sample_rate
        self.open = seconds is None   # no fixed length: grows with the sounds
        self.length = 0 if seconds is None else max(1, int(seconds * sample_rate))
        if audioop:
            self.buffer = bytearray()
        elif FAST:
            self._even: list[int] = []   # per block: sum of the samples of even rank
            self._odd: list[int] = []    # and of odd rank (integers of signed digits)
            self._mixed: bytes | None = None   # the result, once asked for
            self._offset = 0x8000 * _ones(self.BLOCK // 2)   # the + 32768 of a whole block
        else:
            self.acc = array("d")
        self._room(self.length)

    def _room(self, length: int) -> None:
        """Makes room for `length` samples."""
        if audioop:
            self.buffer.extend(bytes(max(0, 2 * length - len(self.buffer))))
        elif FAST:
            missing = -(-length // self.BLOCK) - len(self._even)
            if missing > 0:
                self._even += [0] * missing
                self._odd += [0] * missing
        else:
            self.acc.extend(array("d", bytes(max(0, 8 * (length - len(self.acc))))))

    def add(self, pcm: bytes, at_seconds: float, gain: float = 1.0) -> None:
        start = int(round(at_seconds * self.sample_rate))
        if not pcm or (start >= self.length and not self.open):
            return
        if start < 0:
            pcm = pcm[-2 * start:]
            start = 0
        count = len(pcm) // 2
        if not self.open:
            count = min(count, self.length - start)
        elif start + count > self.length:
            self.length = start + count
            self._room(self.length)
        if count <= 0:
            return
        if audioop:
            a, b = 2 * start, 2 * (start + count)
            chunk = pcm[:2 * count] if gain == 1.0 else audioop.mul(pcm[:2 * count], 2, gain)
            self.buffer[a:b] = audioop.add(bytes(self.buffer[a:b]), chunk, 2)
        elif FAST:
            if self._mixed is not None:   # a sound added after to_bytes(): the sum
                mixed, self._mixed = self._mixed, None   # starts again from its result
                self.add(mixed, 0.0)
            sound = pcm if len(pcm) == 2 * count else pcm[:2 * count]
            if gain != 1.0:
                sound = scale(sound, gain)
            for done in range(0, count, _CHUNK):   # one pass for a note
                chunk = sound if count <= _CHUNK else sound[2 * done:2 * (done + _CHUNK)]
                size = len(chunk) // 2
                even, odd = _digits(chunk, size)
                first = (start + done) // 2
                if (start + done) % 2 == 0:
                    self._put(self._even, first, even, (size + 1) // 2)
                    self._put(self._odd, first, odd, size // 2)
                else:   # shifted by one sample: the ranks swap
                    self._put(self._odd, first, even, (size + 1) // 2)
                    self._put(self._even, first + 1, odd, size // 2)
        else:
            src = array("h")
            src.frombytes(pcm[:2 * count])
            end = start + count
            scaled = src if gain == 1.0 else map(mul, src, repeat(gain))
            self.acc[start:end] = array("d", map(add, self.acc[start:end], scaled))

    def _put(self, blocks: list[int], first: int, digits: int, count: int) -> None:
        """Adds `count` digits (worth sample + 32768) from digit `first` on, in
        the blocks they cover."""
        half = self.BLOCK // 2
        block, pos = divmod(first, half)
        while count > 0:
            take = min(half - pos, count)
            piece = digits
            if take < count:
                piece &= (1 << (32 * take)) - 1
                digits >>= 32 * take
            offset = self._offset if take == half else 0x8000 * _ones(take)
            blocks[block] += (piece - offset) << (32 * pos)
            count -= take
            block += 1
            pos = 0

    def to_bytes(self, seconds: float | None = None) -> bytes:
        """The mix; `seconds`: its length (else the one given at the start, or
        the end of the last sound)."""
        length = self.length if seconds is None else max(1, int(seconds * self.sample_rate))
        if audioop:
            mixed = bytes(self.buffer[:2 * length])
        elif FAST:
            if self._mixed is None:
                out = []
                for block in range(min(len(self._even), -(-length // self.BLOCK))):
                    out.append(_finish(self._even[block], self._odd[block], self.BLOCK))
                    self._even[block] = self._odd[block] = 0   # frees the memory as it goes
                if len(out) * self.BLOCK > length:   # the last block, cut to the length
                    out[-1] = out[-1][:2 * (length - (len(out) - 1) * self.BLOCK)]
                self._mixed = b"".join(out)
            mixed = self._mixed[:2 * length]
        else:
            values = array("i", map(int, self.acc[:length]))
            if values and (min(values) < -32768 or max(values) > 32767):
                values = array("i", (max(-32768, min(32767, x)) for x in values))
            mixed = array("h", values).tobytes()
        return mixed + bytes(2 * length - len(mixed))   # silence up to the length asked for


# --- The synthesiser ---------------------------------------------------------------------

class GuitarSynth:
    """Supplies the sound of each note (computed once, then cached)."""

    def __init__(self, sample_rate: int = 44100, cache_dir: Path | None = None,
                 voice: str = DEFAULT_VOICE) -> None:
        self.sample_rate = sample_rate
        self.voice = voice if voice in VOICES else DEFAULT_VOICE
        self.cache_dir = (Path(cache_dir) / f"{CACHE_VERSION}_{self.voice}_{sample_rate}"
                          if cache_dir else None)
        self._notes: dict[int, bytes] = {}
        self._variants: dict[tuple, bytes] = {}
        self._variants_bytes = 0
        self._lock = threading.Lock()
        self._chuck: bytes | None = None

    # Full note (let ring) -----------------------------------------------------------------
    def note(self, midi: int) -> bytes:
        midi = int(midi)
        with self._lock:
            pcm = self._notes.get(midi)
        if pcm is not None:
            return pcm
        pcm = self._load(midi)
        if pcm is None and self.voice == "keys":
            raw = keys_tone(midi_freq(midi)).tobytes()
            pcm = scale(resample(raw, KEYS_RATE, self.sample_rate), 0.8)
            self._store(midi, pcm)
        if pcm is None:
            pcm = self._recorded(midi)
            if pcm is None:  # no recording: synthesised string
                seconds = max(1.3, min(3.0, 3.6 - 0.035 * (midi - 40)))
                pcm = pluck(midi_freq(midi), self.sample_rate, seconds, seed=midi).tobytes()
            self._store(midi, pcm)
        with self._lock:
            self._notes[midi] = pcm
        return pcm

    def _recorded(self, midi: int) -> bytes | None:
        """The nearest recorded note, transposed if needed."""
        notes = sample_notes(self.voice)
        if not notes:
            return None
        # the nearest; on a tie, the one above (transposing down
        # sounds more natural than up)
        source = min(notes, key=lambda n: (abs(n - midi), -n))
        folder = voice_dir(self.voice)
        loaded = load_snd(folder / f"{source}.snd") if folder else None
        if loaded is None:
            return None
        rate, pcm = loaded
        shift = 2.0 ** ((midi - source) / 12.0)
        return resample(pcm, rate * shift, self.sample_rate)

    def _path(self, midi: int) -> Path | None:
        return self.cache_dir / f"{midi}.pcm" if self.cache_dir else None

    def _load(self, midi: int) -> bytes | None:
        path = self._path(midi)
        try:
            if path and path.exists():
                data = path.read_bytes()
                if len(data) > 1000 and len(data) % 2 == 0:
                    return data
        except OSError:
            pass
        return None

    def _store(self, midi: int, pcm: bytes) -> None:
        path = self._path(midi)
        if not path:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(f".{threading.get_ident()}.tmp")  # one per thread
            tmp.write_bytes(pcm)
            tmp.replace(path)
        except OSError:
            pass  # the disk cache is a bonus

    def warm_up(self, midis) -> None:
        """Prepares the notes in advance (run it in a background thread)."""
        for midi in midis:
            self.note(midi)

    # Variants -------------------------------------------------------------------------------
    def _cached(self, key: tuple, make) -> bytes:
        with self._lock:
            pcm = self._variants.get(key)
        if pcm is None:
            pcm = make()
            with self._lock:
                if len(self._variants) > 600 or self._variants_bytes > VARIANTS_BYTES:
                    self._variants.clear()
                    self._variants_bytes = 0
                if key not in self._variants:
                    self._variants_bytes += len(pcm)
                self._variants[key] = pcm
        return pcm

    def detuned(self, midi: int, cents: float) -> bytes:
        """The note, higher (cents > 0) or lower by `cents` hundredths
        of a semitone: the recording is read a little faster or slower."""
        c = round(cents, 1)
        if not c:
            return self.note(midi)
        return self._cached(("cents", midi, c), lambda: resample(
            self.note(midi), self.sample_rate * 2.0 ** (c / 1200.0), self.sample_rate))

    def played(self, midi: int, gain: float, seconds: float | None = None,
               skip: float = 0.0, muted: bool = False, cents: float = 0.0) -> bytes:
        """Note played: volume, duration (muted at the end), attack skipped (legato),
        detuning in cents ("Wrong note" mode)."""
        g = round(gain, 2)
        c = round(cents, 1)
        if muted:
            base = self._cached(("muted", midi, g), lambda: self._muted(midi, g))
        elif c:
            base = self._cached(("gain", midi, g, c), lambda: scale(self.detuned(midi, c), g))
        else:
            base = self._cached(("gain", midi, g), lambda: scale(self.note(midi), g))
        start = int(skip * self.sample_rate) * 2
        pcm = base[start:]
        if start:
            pcm = fade_in(pcm, int(0.004 * self.sample_rate))
        if seconds is not None:
            end = max(2, int(seconds * self.sample_rate)) * 2
            if end < len(pcm):
                pcm = fade_out(pcm[:end], int(0.012 * self.sample_rate))
        return pcm

    def _muted(self, midi: int, gain: float) -> bytes:
        """Palm mute: dull, short sound."""
        sr = self.sample_rate
        src = array("h")
        src.frombytes(self.note(midi)[: 2 * int(0.16 * sr)])
        out = array("h", bytes(2 * len(src)))
        low = 0.0
        for i, x in enumerate(src):
            low += 0.18 * (x - low)
            out[i] = int(low * gain * 1.6 * math.exp(-i / (0.045 * sr)))
        return out.tobytes()

    def chuck(self, gain: float) -> bytes:
        if self._chuck is None:
            self._chuck = self._dead_strum() or noise_burst(self.sample_rate).tobytes()
        return self._cached(("chuck", round(gain, 2)), lambda: scale(self._chuck, gain))

    def _dead_strum(self) -> bytes | None:
        """"Chuck": the six strings struck but muted by the palm. The
        attack of each open string is kept (the pick noise and the very
        start of the note), cut off very quickly and dulled."""
        if not sample_notes(self.voice):
            return None
        sr = self.sample_rate
        length = int(0.06 * sr)
        mix = [0.0] * length
        for k, midi in enumerate((40, 45, 50, 55, 59, 64)):
            src = array("h")
            src.frombytes(self.note(midi)[: 2 * length])
            delay = int(k * 0.0025 * sr)  # the stroke sweeps across the strings
            low = 0.0
            for i, x in enumerate(src[: length - delay]):
                low += 0.35 * (x - low)
                mix[i + delay] += low * math.exp(-i / (0.009 * sr))
        rnd = random.Random(5)
        hiss = 0.0
        for i in range(length):  # a little friction on the strings
            hiss += 0.3 * (rnd.uniform(-1.0, 1.0) - hiss)
            mix[i] += 2500.0 * hiss * math.exp(-i / (0.006 * sr))
        return _to_int16(mix).tobytes()
