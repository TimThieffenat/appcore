"""Calcul des positions d'accords jouables et de leurs doigtés (partagé par les apps du socle).

Sans dépendance à Qt. Fonctionne avec n'importe quel accordage.

Règles utilisées pour qu'une position soit jouable :
- la note la plus grave est la tonique de l'accord (position fondamentale) ;
- les cordes jouées forment un bloc continu (pas de corde étouffée au milieu) ;
- au moins 4 cordes jouées ;
- toutes les notes de l'accord sont présentes (la quinte juste peut manquer
  dans les accords de 4 sons ou plus) ;
- les doigts tiennent dans 4 cases (écart maximum de 3 cases) ;
- 4 doigts maximum, avec barré de l'index ou petit barré d'un autre doigt.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product

from appcore import music_theory as mt

MAX_SPAN = 3  # écart maximal entre la case la plus basse et la plus haute
MAX_FRET_WITH_OPEN = 3  # cordes à vide seulement avec des cases basses

STANDARD_TUNING = (4, 9, 2, 7, 11, 4)  # E A D G B E

# Formes d'accords ouverts « de référence » (accordage standard), favorisées
# pour que le bas du manche affiche les doigtés que tout le monde apprend.
STANDARD_SHAPES = {
    ("C", "Major"): "x32010", ("C", "7 (dominant)"): "x32310",
    ("C", "Major 7"): "x32000", ("C", "add9"): "x32030",
    ("D", "Major"): "xx0232", ("D", "Minor"): "xx0231",
    ("D", "7 (dominant)"): "xx0212", ("D", "Minor 7"): "xx0211",
    ("D", "Major 7"): "xx0222", ("D", "Sus2"): "xx0230", ("D", "Sus4"): "xx0233",
    ("E", "Major"): "022100", ("E", "Minor"): "022000",
    ("E", "7 (dominant)"): "020100", ("E", "Minor 7"): "022030",
    ("E", "Major 7"): "021100", ("E", "Sus4"): "022200",
    ("F", "Major 7"): "xx3210",
    ("G", "Major"): "320003", ("G", "7 (dominant)"): "320001",
    ("G", "Major 7"): "320002", ("G", "6"): "320000",
    ("A", "Major"): "x02220", ("A", "Minor"): "x02210",
    ("A", "7 (dominant)"): "x02020", ("A", "Minor 7"): "x02010",
    ("A", "Major 7"): "x02120", ("A", "Sus2"): "x02200", ("A", "Sus4"): "x02230",
    ("B", "7 (dominant)"): "x21202",
}
STANDARD_BONUS = 12.0

# Formes barrées classiques, déplaçables le long du manche (accordage
# standard). Décalages de case par corde, depuis la case de la tonique sur
# la corde grave de la forme ; None = corde étouffée.
MOVABLE_SHAPES = {
    # forme de mi, forme de la, forme de ré, forme de do
    "Major": [(0, 2, 2, 1, 0, 0), (None, 0, 2, 2, 2, 0),
               (None, None, 0, 2, 3, 2), (None, 0, -1, -3, -2, -3)],
    "Minor": [(0, 2, 2, 0, 0, 0), (None, 0, 2, 2, 1, 0),
               (None, None, 0, 2, 3, 1)],
    "7 (dominant)": [(0, 2, 0, 1, 0, 0), (None, 0, 2, 0, 2, 0),
                                  (None, None, 0, 2, 1, 2)],
    "Minor 7": [(0, 2, 0, 0, 0, 0), (None, 0, 2, 0, 1, 0),
                 (None, None, 0, 2, 1, 1)],
    "Major 7": [(None, 0, 2, 1, 2, 0), (None, None, 0, 2, 2, 2)],
    "Sus4": [(0, 2, 2, 2, 0, 0), (None, 0, 2, 2, 3, 0)],
    "Sus2": [(None, 0, 2, 2, 0, 0)],
    "9": [(None, 0, -1, 0, 0, 0)],
    "Minor 9": [(None, 0, -2, 0, 0, 0)],
    "Half-diminished (m7♭5)": [(None, 0, 1, 0, 1, None)],
    "Diminished 7": [(None, 0, 1, -1, 1, None)],
}
MOVABLE_BONUS = 8.0


def _parse_shape(shape: str) -> tuple[int, ...]:
    return tuple(-1 if c == "x" else int(c) for c in shape)


def standard_offset(tuning: tuple[int, ...]) -> int | None:
    """De combien de demi-tons l'accordage est l'accordage standard monté
    (capo, ou accordage standard transposé comme « Half step down ») ; None
    sinon. Les formes de référence s'appliquent alors telles quelles."""
    if len(tuning) != len(STANDARD_TUNING):
        return None
    for shift in range(12):
        if all((t - shift) % 12 == s for t, s in zip(tuning, STANDARD_TUNING)):
            return shift
    return None


@dataclass(frozen=True)
class Barre:
    fret: int
    first: int   # corde de début (index, 0 = corde la plus grave)
    last: int    # corde de fin
    finger: int


@dataclass(frozen=True)
class Voicing:
    frets: tuple[int, ...]    # par corde, grave -> aigu ; -1 étouffée, 0 à vide
    fingers: tuple[int, ...]  # 0 = aucun doigt
    barres: tuple[Barre, ...]
    score: float             # qualité de la position (plus haut = mieux)
    standard: bool = False   # forme d'accord ouvert de référence
    movable: bool = False    # forme barrée classique (forme de mi, de la...)

    @property
    def rank(self) -> float:
        """Score + bonus des formes classiques (pour le bas du manche)."""
        return self.score + (STANDARD_BONUS if self.standard else 0.0) \
            + (MOVABLE_BONUS if self.movable else 0.0)

    @property
    def rank_without_open(self) -> float:
        """Score + bonus des formes barrées seulement (plus haut sur le manche)."""
        return self.score + (MOVABLE_BONUS if self.movable else 0.0)

    @property
    def position(self) -> int:
        """0 pour un accord ouvert, sinon la case la plus basse jouée."""
        if any(f == 0 for f in self.frets):
            return 0
        return min(f for f in self.frets if f > 0)

    @property
    def base_fret(self) -> int:
        """Première case affichée dans un diagramme de 5 cases."""
        fretted = [f for f in self.frets if f > 0]
        if not fretted or max(fretted) <= 5:
            return 1
        return min(fretted)


# --- Doigtés -------------------------------------------------------------------

def _assign(notes: list[tuple[int, int]], first: int, last: int,
            base_fret: int) -> tuple[dict[int, int], list[Barre]] | None:
    """Donne un doigt à chaque note (corde, case), du plus grave au plus aigu.

    Le doigt idéal suit la case (index sur base_fret, majeur une case plus
    haut...). Si les doigts manquent, les notes de la case la plus haute sur
    des cordes voisines sont jouées en petit barré par un seul doigt.
    """
    if not notes:
        return {}, []
    groups = [[n] for n in sorted(notes, key=lambda n: (n[1], n[0]))]
    mini = None
    if len(groups) > last - first + 1:
        top = max(f for _, f in notes)
        strings = sorted(s for s, f in notes if f == top)
        # plus longue suite de cordes voisines sur la case la plus haute
        runs, run = [], [strings[0]]
        for s in strings[1:]:
            if s == run[-1] + 1:
                run.append(s)
            else:
                runs.append(run)
                run = [s]
        runs.append(run)
        best = max(runs, key=len)
        if len(best) < 2:
            return None
        others = [n for n in notes if not (n[1] == top and n[0] in best)]
        groups = [[n] for n in sorted(others, key=lambda n: (n[1], n[0]))]
        groups.append([(s, top) for s in best])
        mini = (top, best[0], best[-1])
        if len(groups) > last - first + 1:
            return None

    fingers: dict[int, int] = {}
    previous = first - 1
    for index, group in enumerate(groups):
        fret = group[0][1]
        remaining = len(groups) - index - 1
        ideal = 1 + (fret - base_fret)
        finger = max(previous + 1, min(ideal, last - remaining))
        if finger > last:
            return None
        for string, _ in group:
            fingers[string] = finger
        previous = finger

    barres = []
    if mini:
        fret, lo, hi = mini
        barres.append(Barre(fret, lo, hi, fingers[lo]))
    return fingers, barres


def fingering(frets: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[Barre, ...]] | None:
    """Trouve un doigté pour une position, ou None si injouable."""
    fretted = [(s, f) for s, f in enumerate(frets) if f > 0]
    count = len(frets)
    if not fretted:
        return (0,) * count, ()
    low = min(f for _, f in fretted)

    def pack(result):
        fingers, barres = result
        return tuple(fingers.get(s, 0) for s in range(count)), tuple(barres)

    at_low = [s for s, f in fretted if f == low]

    # 1) Sans barré de l'index (sauf deux cordes voisines sur la case la
    #    plus basse avec 3 doigts ou plus : l'index les barre, comme dans Dm7)
    simple = _assign(fretted, 1, 4, low)
    two_adjacent = len(at_low) == 2 and at_low[1] - at_low[0] == 1
    if simple is not None and len(fretted) <= 4:
        if not (two_adjacent and len(set(simple[0].values())) >= 3):
            return pack(simple)

    # 2) Barré de l'index sur la case la plus basse
    if len(at_low) >= 2:
        lo, hi = min(at_low), max(at_low)
        # toutes les cordes sous le barré doivent être frettées (pas à vide)
        if all(frets[s] >= low for s in range(lo, hi + 1)):
            rest = [(s, f) for s, f in fretted if f > low]
            sub = _assign(rest, 2, 4, low)
            if sub is not None:
                fingers, barres = sub
                for s in at_low:
                    fingers[s] = 1
                return pack((fingers, [Barre(low, lo, hi, 1)] + barres))

    return pack(simple) if simple is not None else None


# --- Recherche des positions ---------------------------------------------------

def _score(frets, fingers, barres, missing_fifth: bool) -> float:
    sounding = [f for f in frets if f >= 0]
    fretted = [f for f in frets if f > 0]
    span = max(fretted) - min(fretted) if fretted else 0
    opens = sum(1 for f in frets if f == 0)
    used = len({f for f in fingers if f})
    score = 3.0 * len(sounding) - 3.0 * span - 1.5 * used
    if any(b.finger == 1 for b in barres):
        score -= 2.0
    for b in barres:
        if b.finger == 4 and b.last - b.first >= 2:
            score -= 3.0  # petit barré de l'auriculaire sur 3 cordes : difficile
        elif b.finger != 1:
            score -= 1.0
    if missing_fifth:
        score -= 6.0
    score += 0.5 * opens  # cordes à vide : son plus ample, plus facile
    # cordes aiguës étouffées : moins agréable à gratter
    top_muted = 0
    for f in reversed(frets):
        if f >= 0:
            break
        top_muted += 1
    score -= 3.0 * top_muted
    return score


@lru_cache(maxsize=512)
def all_voicings(root: str, type_name: str, tuning: tuple[int, ...],
                 max_fret: int = 15) -> tuple[Voicing, ...]:
    """Toutes les positions jouables de l'accord, de la meilleure à la moins bonne."""
    notes = mt.build_notes(root, mt.CHORDS[type_name][1])
    chord_pcs = {n.pc for n in notes}
    root_pc = mt.note_pc(root)
    fifth_pc = next((n.pc for n in notes if n.degree == "5"), None)
    required = set(chord_pcs)
    if len(notes) >= 4 and fifth_pc is not None:
        required.discard(fifth_pc)
    min_strings = min(len(tuning), max(4, len(required)))
    standard_shape = None
    movable: set[tuple[int, ...]] = set()
    shift = standard_offset(tuple(tuning))
    if shift is not None:
        for (name, kind), shape in STANDARD_SHAPES.items():
            if kind == type_name and (mt.note_pc(name) + shift) % 12 == root_pc:
                standard_shape = _parse_shape(shape)
        for offsets in MOVABLE_SHAPES.get(type_name, []):
            root_string = next(s for s, o in enumerate(offsets) if o is not None)
            first = (root_pc - tuning[root_string]) % 12
            for root_fret in (first, first + 12):
                frets = tuple(-1 if o is None else root_fret + o for o in offsets)
                if root_fret >= 1 and min(f for f in frets if f != -1) >= 1:
                    movable.add(frets)

    found: dict[tuple[int, ...], Voicing] = {}
    for start in range(1, max_fret - MAX_SPAN + 1):
        window = range(start, start + MAX_SPAN + 1)
        options = []
        for open_pc in tuning:
            choices = [-1]
            if open_pc in chord_pcs:
                choices.append(0)
            choices += [f for f in window if (open_pc + f) % 12 in chord_pcs]
            options.append(choices)

        for frets in product(*options):
            if frets in found:
                continue
            sounding = [s for s, f in enumerate(frets) if f >= 0]
            if len(sounding) < min_strings:
                continue
            if sounding[-1] - sounding[0] + 1 != len(sounding):
                continue  # corde étouffée au milieu
            bass = sounding[0]
            if (tuning[bass] + frets[bass]) % 12 != root_pc:
                continue
            present = {(tuning[s] + frets[s]) % 12 for s in sounding}
            if not required <= present:
                continue
            fretted = [f for f in frets if f > 0]
            if fretted and max(fretted) - min(fretted) > MAX_SPAN:
                continue
            if fretted and 0 in frets and max(fretted) > MAX_FRET_WITH_OPEN:
                continue  # cordes à vide mélangées à des cases hautes
            result = fingering(frets)
            if result is None:
                continue
            fingers, barres = result
            missing_fifth = fifth_pc is not None and fifth_pc not in present
            found[frets] = Voicing(
                frets, fingers, barres,
                _score(frets, fingers, barres, missing_fifth),
                standard=frets == standard_shape,
                movable=frets in movable,
            )
    return tuple(sorted(found.values(), key=lambda v: -v.rank))


def spread_voicings(root: str, type_name: str, tuning: tuple[int, ...],
                    count: int = 8) -> list[Voicing]:
    """Les meilleures positions réparties le long du manche, triées par case."""
    candidates = all_voicings(root, type_name, tuning)
    if not candidates:
        return []
    best_score = max(v.score for v in candidates)
    chosen: list[Voicing] = []
    for v in candidates:
        if v.score < best_score - 8 and not (v.standard or v.movable):
            continue
        if v.position > 12:
            continue  # au-delà de la 12e case, ce sont les mêmes une octave plus haut
        if all(abs(v.position - c.position) >= 2 for c in chosen):
            chosen.append(v)
        if len(chosen) == count:
            break
    return sorted(chosen, key=lambda v: v.position)


def best_voicing(root: str, type_name: str, tuning: tuple[int, ...],
                 target: int = 0) -> Voicing | None:
    """La meilleure position proche de la case visée (0 = bas du manche)."""
    candidates = all_voicings(root, type_name, tuning)
    if not candidates:
        return None

    def cost(v: Voicing) -> float:
        distance = abs(v.position - target)
        quality = v.rank if target <= 3 else v.rank_without_open
        return -quality + 1.5 * max(0, distance - 2)

    return min(candidates, key=cost)


def voicing_at(root: str, type_name: str, tuning: tuple[int, ...],
               fret: int) -> Voicing | None:
    """La meilleure position dans la zone de 5 cases qui commence à `fret`.

    Contrairement à `best_voicing`, la zone est respectée : pour jouer une suite
    « vers la 5e case », tous les accords restent entre les cases 4 et 9.
    fret = 0 : accords ouverts (bas du manche).
    """
    if fret <= 0:
        return best_voicing(root, type_name, tuning, 0)
    candidates = all_voicings(root, type_name, tuning, max_fret=min(20, fret + 7))

    def zone(v: Voicing) -> tuple[int, int]:
        fretted = [f for f in v.frets if f > 0]
        return (min(fretted), max(fretted)) if fretted else (0, 0)

    for below, above in ((1, 4), (2, 5), (3, 6)):  # zone, puis un peu plus large
        inside = [v for v in candidates
                  if zone(v)[0] >= fret - below and 0 < zone(v)[1] <= fret + above]
        if inside:
            def cost(v: Voicing) -> float:
                opens = sum(1 for f in v.frets if f == 0)
                return (-v.rank_without_open + 0.6 * abs(zone(v)[0] - fret)
                        + 1.0 * opens)
            return min(inside, key=cost)
    return best_voicing(root, type_name, tuning, fret)


def note_for(tuning: tuple[int, ...], string: int, fret: int) -> int:
    return (tuning[string] + fret) % 12
