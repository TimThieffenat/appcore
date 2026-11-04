"""Le son des notes : guitare acoustique enregistrée, ou clavier synthétisé.

Trois instruments : guitare à cordes acier (sounds/guitar), à cordes nylon
(sounds/guitar_nylon), voir sounds/CREDITS.md, et un clavier doux synthétisé
(pour les musiciens qui ne jouent pas de la guitare). Une note sans enregistrement est obtenue en transposant la plus
proche. Si les fichiers manquent, une corde pincée synthétisée
(Karplus-Strong) prend le relais.

Chaque app choisit les instruments qu'elle propose (VOICES de son app_info.py).
`played(..., cents=…)` donne une note volontairement désaccordée ; la voix
« keys » (clavier) est calculée note par note. Les enregistrements sont dans
appcore/sounds/ (voir sounds/CREDITS.md), partagés par toutes les apps.

Sans Qt et sans dépendance externe :
- chaque hauteur est préparée une fois, gardée en mémoire et, si un dossier
  de cache est donné, sur disque (instantané ensuite) ;
- le mixage utilise le module standard « audioop » quand il existe
  (Python ≤ 3.12, donc sur Android), sinon une version pur Python plus lente.

Format produit : PCM 16 bits signé, mono, à la fréquence d'échantillonnage
choisie (celle de la sortie audio).
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
from operator import add, mul, sub
from dataclasses import dataclass, field
from pathlib import Path

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    try:  # rapide (code C) ; retiré de Python 3.13 (paquet « audioop-lts » sinon)
        import audioop
    except ImportError:
        audioop = None

log = logging.getLogger(__name__)

CACHE_VERSION = "v2"   # v2 : enregistrements réels
SOUNDS_DIR = Path(__file__).with_name("sounds")
GUITAR_DIR = SOUNDS_DIR / "guitar"
# Instruments au choix : nom -> (libellé, dossier des enregistrements ou None)
VOICES = {
    "steel": ("Steel-string acoustic", "guitar"),
    "nylon": ("Nylon-string (classical)", "guitar_nylon"),
    "keys": ("Soft keys (all musicians)", None),
}
DEFAULT_VOICE = "steel"
KEYS_RATE = 22050      # le clavier est calculé à cette fréquence, puis converti


def voice_dir(voice: str) -> Path | None:
    folder = VOICES.get(voice, VOICES[DEFAULT_VOICE])[1]
    return SOUNDS_DIR / folder if folder else None


def load_snd(path: Path) -> tuple[int, bytes] | None:
    """Fichier .snd : zlib( fréquence uint32 + PCM 16 bits mono ). None si illisible."""
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
    """Change la fréquence d'échantillonnage. Avec in_rate plus grand que la
    fréquence réelle de l'enregistrement, la note est transposée vers l'aigu."""
    in_rate = max(1, int(round(in_rate)))
    if in_rate == out_rate:
        return pcm
    if audioop:
        return audioop.ratecv(pcm, 2, 1, in_rate, out_rate, None)[0]
    # Sans audioop (Python 3.13 et plus, donc l'app Android en Python 3.14) :
    # interpolation linéaire écrite avec map() et les opérateurs du module
    # operator, sans boucle Python par échantillon (environ 10 fois plus rapide).
    src = array("h")
    src.frombytes(pcm)
    if len(src) < 2:
        return pcm
    src.append(src[-1])              # le dernier échantillon a un voisin
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
    """Les notes MIDI enregistrées d'une guitare (vide si le dossier manque)."""
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
    """Corde pincée : bruit filtré qui boucle dans une ligne à retard."""
    period = sample_rate / freq
    length = int(period - 0.5)
    frac = period - 0.5 - length
    if frac < 0.1:  # garde le filtre passe-tout stable
        length -= 1
        frac += 1.0
    length = max(2, length)
    coef = (1.0 - frac) / (1.0 + frac)  # retard fractionnaire : justesse exacte

    rnd = random.Random(seed)
    excite = [rnd.uniform(-1.0, 1.0) for _ in range(length)]
    for _ in range(2):  # attaque plus douce (médiator, pas lame de rasoir)
        excite = [0.5 * (excite[i] + excite[i - 1]) for i in range(length)]
    gap = max(1, int(round(pick_position * length)))  # position du médiator
    excite = [excite[i] - 0.7 * excite[i - gap] for i in range(length)]
    mean = sum(excite) / length
    buf = [x - mean for x in excite]

    # déclin : les graves sonnent plus longtemps que les aigus
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
        body += 0.45 * (x - body)  # légère chaleur (passe-bas)
        out[n] = body
    # micro fondu d'entrée / sortie : pas de clic
    fade_in = min(total, int(0.002 * sample_rate))
    for i in range(fade_in):
        out[i] *= i / fade_in
    fade_out = min(total, int(0.05 * sample_rate))
    for i in range(fade_out):
        out[total - 1 - i] *= i / fade_out
    return _to_int16(out)


def noise_burst(sample_rate: int, seconds: float = 0.035, seed: int = 3) -> array:
    """Coup étouffé (« chuck ») : bruit sourd très court."""
    rnd = random.Random(seed)
    total = int(sample_rate * seconds)
    out = []
    low = 0.0
    for n in range(total):
        low += 0.25 * (rnd.uniform(-1, 1) - low)
        out.append(low * math.exp(-n / (0.008 * sample_rate)))
    return _to_int16(out)


def keys_tone(freq: float, sample_rate: int = KEYS_RATE, seconds: float = 2.2) -> array:
    """Note de clavier doux (piano électrique) : quelques harmoniques qui
    s'éteignent, les aiguës plus vite, et un léger « tintement » à l'attaque."""
    total = int(sample_rate * seconds)
    out = array("f", bytes(4 * total))
    nyquist = sample_rate / 2
    # (rang de l'harmonique, volume, durée de déclin en s)
    partials = [(1.0, 1.0, 1.25), (2.0, 0.42, 0.65), (3.0, 0.20, 0.42),
                (4.0, 0.10, 0.30), (5.0, 0.05, 0.22), (7.03, 0.10, 0.05)]
    low_boost = max(0.0, min(1.0, (300.0 - freq) / 250.0))   # graves plus ronds
    for ratio, amp, tau in partials:
        f = freq * ratio
        if f >= nyquist * 0.9:
            continue
        if ratio > 1:
            amp *= 1.0 - 0.5 * low_boost
        tau *= max(0.5, min(1.6, 440.0 / freq) ** 0.35)
        w = 2 * math.pi * f / sample_rate
        # sinus par rotation (2 multiplications par échantillon)
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


# --- Opérations PCM (audioop si disponible) ----------------------------------------------

def scale(pcm: bytes, gain: float) -> bytes:
    if gain == 1.0:
        return pcm
    if audioop:
        return audioop.mul(pcm, 2, gain)
    data = array("h")
    data.frombytes(pcm)
    values = array("i", map(int, map(mul, data, repeat(gain))))   # sans boucle Python
    if values and (min(values) < -32768 or max(values) > 32767):  # gain > 1 : écrêter
        values = array("i", (max(-32768, min(32767, x)) for x in values))
    return array("h", values).tobytes()


def fade_out(pcm: bytes, samples: int) -> bytes:
    """Fondu de sortie sur les `samples` derniers échantillons (petit : pur Python)."""
    samples = min(samples, len(pcm) // 2)
    if samples <= 0:
        return pcm
    tail = array("h")
    tail.frombytes(pcm[len(pcm) - 2 * samples:])
    for i in range(samples):
        tail[i] = int(tail[i] * (samples - i) / samples)
    return pcm[:len(pcm) - 2 * samples] + tail.tobytes()


def fade_in(pcm: bytes, samples: int) -> bytes:
    samples = min(samples, len(pcm) // 2)
    if samples <= 0:
        return pcm
    head = array("h")
    head.frombytes(pcm[:2 * samples])
    for i in range(samples):
        head[i] = int(head[i] * i / samples)
    return head.tobytes() + pcm[2 * samples:]


@dataclass
class Performance:
    """Un son prêt à jouer : PCM 16 bits mono, sa durée, et des événements
    (temps, valeur) que l'interface utilise pour surligner ce qui joue
    (audio_player.Playback). Les apps les fabriquent (leur performance.py)."""

    pcm: bytes
    sample_rate: int
    duration: float
    events: list[tuple[float, object]] = field(default_factory=list)
    # Son « touché » (une note, un accord) : le son suivant ne le coupe pas, il
    # continue de sonner, sauf sur les cordes que le suivant rejoue. Une suite
    # (lick, gamme, morceau) s'éteint, elle, quand on joue autre chose.
    one_shot: bool = False
    strings: frozenset[int] = frozenset()   # cordes jouées (n° dans l'accordage)


def arpeggio(synth: "GuitarSynth", midis, step: float = 0.18, seconds: float = 1.6,
             gain: float = 0.55) -> Performance:
    """Des notes jouées l'une après l'autre (essai d'un instrument, réglages)."""
    sr = synth.sample_rate
    midis = list(midis)
    total = step * max(0, len(midis) - 1) + seconds + 0.3
    mixer = Mixer(sr, total)
    for i, midi in enumerate(midis):
        mixer.add(synth.played(midi, gain, seconds), i * step)
    return Performance(mixer.to_bytes(), sr, total, [])


class Mixer:
    """Somme de sons placés dans le temps, chacun avec son volume.

    Sans audioop (Python 3.13 et plus, donc l'app Android en Python 3.14), la
    somme se fait en nombres à virgule, volume compris, en une passe par son et
    sans boucle Python par échantillon ; l'écrêtage n'a lieu qu'à la fin."""

    def __init__(self, sample_rate: int, seconds: float) -> None:
        self.sample_rate = sample_rate
        self.length = max(1, int(seconds * sample_rate))
        if audioop:
            self.buffer = bytearray(2 * self.length)
        else:
            self.acc = array("d", bytes(8 * self.length))

    def add(self, pcm: bytes, at_seconds: float, gain: float = 1.0) -> None:
        start = int(round(at_seconds * self.sample_rate))
        if start >= self.length or not pcm:
            return
        if start < 0:
            pcm = pcm[-2 * start:]
            start = 0
        count = min(len(pcm) // 2, self.length - start)
        if count <= 0:
            return
        if audioop:
            a, b = 2 * start, 2 * (start + count)
            chunk = pcm[:2 * count] if gain == 1.0 else audioop.mul(pcm[:2 * count], 2, gain)
            self.buffer[a:b] = audioop.add(bytes(self.buffer[a:b]), chunk, 2)
        else:
            src = array("h")
            src.frombytes(pcm[:2 * count])
            end = start + count
            scaled = src if gain == 1.0 else map(mul, src, repeat(gain))
            self.acc[start:end] = array("d", map(add, self.acc[start:end], scaled))

    def to_bytes(self) -> bytes:
        if audioop:
            return bytes(self.buffer)
        values = array("i", map(int, self.acc))
        if values and (min(values) < -32768 or max(values) > 32767):
            values = array("i", (max(-32768, min(32767, x)) for x in values))
        return array("h", values).tobytes()


# --- Le synthétiseur ---------------------------------------------------------------------

class GuitarSynth:
    """Fournit le son de chaque note (calculé une fois, puis en cache)."""

    def __init__(self, sample_rate: int = 44100, cache_dir: Path | None = None,
                 voice: str = DEFAULT_VOICE) -> None:
        self.sample_rate = sample_rate
        self.voice = voice if voice in VOICES else DEFAULT_VOICE
        self.cache_dir = (Path(cache_dir) / f"{CACHE_VERSION}_{self.voice}_{sample_rate}"
                          if cache_dir else None)
        self._notes: dict[int, bytes] = {}
        self._variants: dict[tuple, bytes] = {}
        self._lock = threading.Lock()
        self._chuck: bytes | None = None

    # Note complète (laisse sonner) -----------------------------------------------------
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
            if pcm is None:  # pas d'enregistrement : corde synthétisée
                seconds = max(1.3, min(3.0, 3.6 - 0.035 * (midi - 40)))
                pcm = pluck(midi_freq(midi), self.sample_rate, seconds, seed=midi).tobytes()
            self._store(midi, pcm)
        with self._lock:
            self._notes[midi] = pcm
        return pcm

    def _recorded(self, midi: int) -> bytes | None:
        """La note enregistrée la plus proche, transposée si besoin."""
        notes = sample_notes(self.voice)
        if not notes:
            return None
        # la plus proche ; à égalité, celle du dessus (transposer vers le grave
        # sonne plus naturel que vers l'aigu)
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
            tmp = path.with_suffix(f".{threading.get_ident()}.tmp")  # un par fil
            tmp.write_bytes(pcm)
            tmp.replace(path)
        except OSError:
            pass  # le cache disque est un bonus

    def warm_up(self, midis) -> None:
        """Prépare les notes à l'avance (à lancer dans un fil d'arrière-plan)."""
        for midi in midis:
            self.note(midi)

    # Variantes ----------------------------------------------------------------------------
    def _cached(self, key: tuple, make) -> bytes:
        with self._lock:
            pcm = self._variants.get(key)
        if pcm is None:
            pcm = make()
            with self._lock:
                if len(self._variants) > 600:
                    self._variants.clear()
                self._variants[key] = pcm
        return pcm

    def detuned(self, midi: int, cents: float) -> bytes:
        """La note, plus haute (cents > 0) ou plus basse de `cents` centièmes
        de demi-ton : l'enregistrement est lu un peu plus vite ou plus lentement."""
        c = round(cents, 1)
        if not c:
            return self.note(midi)
        return self._cached(("cents", midi, c), lambda: resample(
            self.note(midi), self.sample_rate * 2.0 ** (c / 1200.0), self.sample_rate))

    def played(self, midi: int, gain: float, seconds: float | None = None,
               skip: float = 0.0, muted: bool = False, cents: float = 0.0) -> bytes:
        """Note jouée : volume, durée (étouffée en fin), attaque sautée (legato),
        désaccord en cents (mode « Fausse note »)."""
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
        """Palm mute : son sourd et court."""
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
        """« Chuck » : les six cordes frappées mais étouffées par la paume. On
        garde l'attaque de chaque corde à vide (le bruit du médiator et le tout
        début de la note), qu'on éteint très vite et qu'on assourdit."""
        if not sample_notes(self.voice):
            return None
        sr = self.sample_rate
        length = int(0.06 * sr)
        mix = [0.0] * length
        for k, midi in enumerate((40, 45, 50, 55, 59, 64)):
            src = array("h")
            src.frombytes(self.note(midi)[: 2 * length])
            delay = int(k * 0.0025 * sr)  # le geste balaie les cordes
            low = 0.0
            for i, x in enumerate(src[: length - delay]):
                low += 0.35 * (x - low)
                mix[i + delay] += low * math.exp(-i / (0.009 * sr))
        rnd = random.Random(5)
        hiss = 0.0
        for i in range(length):  # un peu de frottement sur les cordes
            hiss += 0.3 * (rnd.uniform(-1.0, 1.0) - hiss)
            mix[i] += 2500.0 * hiss * math.exp(-i / (0.006 * sr))
        return _to_int16(mix).tobytes()
