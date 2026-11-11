"""Basic music theory: notes, degrees, scales, chords, arpeggios.

No dependency on Qt here, so the module can be tested and reused
elsewhere.

Principle: each scale / chord is described by its list of degrees
("1", "b3", "5"...). From the root and the degrees, we compute:
- the pitch class of each note (0 = C, 1 = C#/Db, ... 11 = B)
- its correctly spelled name (B♭ in F major, not A♯)
"""

from __future__ import annotations

from dataclasses import dataclass

from appcore import i18n
from appcore.i18n import tr

LETTERS = "CDEFGAB"
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SOLFEGE = {"C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}
# Spelling specific to some languages (Ré in French; Dó, Ré, Fá, Lá in Portuguese)
SOLFEGE_SPELLING = {"fr": {"D": "Ré"}, "pt": {"C": "Dó", "D": "Ré", "F": "Fá", "A": "Lá"}}

# Note-name notation: internal key -> displayed label (see notation_label)
NOTATIONS = {"letters": "Letters (C D E)", "solfege": "Solfège (Do Re Mi)"}


def solfege(letter: str) -> str:
    """Solfège note name, written as in the app's language."""
    return SOLFEGE_SPELLING.get(i18n.language(), {}).get(letter, SOLFEGE[letter])


def notation_label(key: str) -> str:
    if key == "solfege":
        return tr("Solfège ({notes})", notes=" ".join(solfege(x) for x in "CDE"))
    return tr("Letters (C D E)")

# Semitones of each degree in the major scale (reference of the degrees).
MAJOR_STEPS = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}

# Roots offered (black keys under both their names, so that note
# spelling is right: G♯ minor and A♭ major, for example).
ROOTS = [
    "C", "C#", "Db", "D", "D#", "Eb", "E", "F",
    "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
]

SCALES = {
    "Major (Ionian)": ["1", "2", "3", "4", "5", "6", "7"],
    "Natural minor (Aeolian)": ["1", "2", "b3", "4", "5", "b6", "b7"],
    "Harmonic minor": ["1", "2", "b3", "4", "5", "b6", "7"],
    "Melodic minor": ["1", "2", "b3", "4", "5", "6", "7"],
    "Major pentatonic": ["1", "2", "3", "5", "6"],
    "Minor pentatonic": ["1", "b3", "4", "5", "b7"],
    "Minor blues": ["1", "b3", "4", "b5", "5", "b7"],
    "Major blues": ["1", "2", "b3", "3", "5", "6"],
    "Dorian": ["1", "2", "b3", "4", "5", "6", "b7"],
    "Phrygian": ["1", "b2", "b3", "4", "5", "b6", "b7"],
    "Lydian": ["1", "2", "3", "#4", "5", "6", "7"],
    "Mixolydian": ["1", "2", "3", "4", "5", "6", "b7"],
    "Locrian": ["1", "b2", "b3", "4", "b5", "b6", "b7"],
    "Phrygian dominant": ["1", "b2", "3", "4", "5", "b6", "b7"],
}

# Displayed name -> (chord symbol suffix, degrees)
CHORDS = {
    "Major": ("", ["1", "3", "5"]),
    "Minor": ("m", ["1", "b3", "5"]),
    "Diminished": ("dim", ["1", "b3", "b5"]),
    "Augmented": ("aug", ["1", "3", "#5"]),
    "Sus2": ("sus2", ["1", "2", "5"]),
    "Sus4": ("sus4", ["1", "4", "5"]),
    "6": ("6", ["1", "3", "5", "6"]),
    "Minor 6": ("m6", ["1", "b3", "5", "6"]),
    "7 (dominant)": ("7", ["1", "3", "5", "b7"]),
    "Major 7": ("maj7", ["1", "3", "5", "7"]),
    "Minor 7": ("m7", ["1", "b3", "5", "b7"]),
    "Half-diminished (m7♭5)": ("m7♭5", ["1", "b3", "b5", "b7"]),
    "Diminished 7": ("dim7", ["1", "b3", "b5", "bb7"]),
    "Minor-major 7": ("m(maj7)", ["1", "b3", "5", "7"]),
    "7sus4": ("7sus4", ["1", "4", "5", "b7"]),
    "add9": ("add9", ["1", "3", "5", "9"]),
    "9": ("9", ["1", "3", "5", "b7", "9"]),
    "Major 9": ("maj9", ["1", "3", "5", "7", "9"]),
    "Minor 9": ("m9", ["1", "b3", "5", "b7", "9"]),
}

MODES = ["Scale", "Chord"]  # an arpeggio = the chord's notes: same display

# Tunings: string names from lowest to highest.
TUNINGS = {
    "Standard (E A D G B E)": ["E", "A", "D", "G", "B", "E"],
    "Drop D (D A D G B E)": ["D", "A", "D", "G", "B", "E"],
    "Half step down (E♭)": ["Eb", "Ab", "Db", "Gb", "Bb", "Eb"],
    "DADGAD": ["D", "A", "D", "G", "A", "D"],
    "Open G (D G D G B D)": ["D", "G", "D", "G", "B", "D"],
    "Open D (D A D F# A D)": ["D", "A", "D", "F#", "A", "D"],
}

# Degree colours depend on the theme: see style.py.


@dataclass(frozen=True)
class NoteInfo:
    pc: int       # pitch class, 0..11 (0 = C)
    degree: str   # "1", "b3", "#11"...
    letter: str   # note letter: "C".."B"
    accidental: int  # -2..2 (flats negative, sharps positive)


def parse_note(name: str) -> tuple[str, int]:
    """'Eb' -> ('E', -1), 'F#' -> ('F', 1)."""
    accidental = sum(-1 if c == "b" else 1 for c in name[1:])
    return name[0], accidental


def note_pc(name: str) -> int:
    letter, accidental = parse_note(name)
    return (NATURAL_PC[letter] + accidental) % 12


def parse_degree(degree: str) -> tuple[int, int]:
    """'b3' -> (-1, 3), '#11' -> (1, 11), 'bb7' -> (-2, 7)."""
    i = 0
    accidental = 0
    while degree[i] in "b#":
        accidental += -1 if degree[i] == "b" else 1
        i += 1
    return accidental, int(degree[i:])


def degree_family(degree: str) -> int:
    """Brings 9, 11, 13 back to 2, 4, 6."""
    _, number = parse_degree(degree)
    return (number - 1) % 7 + 1


def degree_semitones(degree: str) -> int:
    accidental, _ = parse_degree(degree)
    return (MAJOR_STEPS[degree_family(degree)] + accidental) % 12


def build_notes(root: str, degrees: list[str]) -> list[NoteInfo]:
    """Computes the (correctly spelled) notes from the root."""
    root_letter, _ = parse_note(root)
    root_pc = note_pc(root)
    notes = []
    for degree in degrees:
        _, number = parse_degree(degree)
        letter = LETTERS[(LETTERS.index(root_letter) + number - 1) % 7]
        pc = (root_pc + degree_semitones(degree)) % 12
        accidental = (pc - NATURAL_PC[letter] + 6) % 12 - 6
        notes.append(NoteInfo(pc, degree, letter, accidental))
    return notes


def degrees_for(mode: str, type_name: str) -> list[str]:
    if mode == "Scale":
        return SCALES[type_name]
    return CHORDS[type_name][1]


def types_for(mode: str) -> list[str]:
    return list(SCALES) if mode == "Scale" else list(CHORDS)


# --- Display -------------------------------------------------------------

def format_accidental(accidental: int) -> str:
    return "♯" * accidental if accidental > 0 else "♭" * -accidental


def format_note(letter: str, accidental: int, notation: str = "letters") -> str:
    base = solfege(letter) if notation == "solfege" else letter
    return base + format_accidental(accidental)


def format_root(root: str, notation: str = "letters") -> str:
    letter, accidental = parse_note(root)
    return format_note(letter, accidental, notation)


def format_degree(degree: str) -> str:
    return degree.replace("b", "♭").replace("#", "♯")


def chromatic_name(pc: int, notation: str = "letters") -> str:
    """Neutral name of a pitch class: 'C', 'C♯/D♭'..."""
    for letter, natural in NATURAL_PC.items():
        if natural == pc:
            return format_note(letter, 0, notation)
    sharp = next(l for l, n in NATURAL_PC.items() if (n + 1) % 12 == pc)
    flat = next(l for l, n in NATURAL_PC.items() if (n - 1) % 12 == pc)
    return f"{format_note(sharp, 1, notation)}/{format_note(flat, -1, notation)}"


def scale_words(scale_name: str) -> str:
    """Translated scale name, to put in a sentence (no capital, except in
    German)."""
    name = tr(scale_name)
    if i18n.language() != "de":
        name = name[:1].lower() + name[1:]
    return name


def scale_title(root_text: str, scale_name: str) -> str:
    """"A minor pentatonic", "La pentatonique mineure"… (translated scale name,
    no capital except in German, where nouns always take one)."""
    return tr("{root} {scale}", root=root_text, scale=scale_words(scale_name))


def mode_name(mode: str) -> str:
    """"major" / "minor" in a sentence ("A minor"), translated."""
    return tr("major") if mode == "Major" else tr("minor") if mode == "Minor" else tr(mode)


def key_title(root: str, mode: str, notation: str = "letters") -> str:
    """A key's name: "A minor", "La mineur", "a-Moll"…"""
    return tr("{root} {mode}", root=format_root(root, notation), mode=mode_name(mode))


def selection_title(root: str, mode: str, type_name: str, notation: str) -> str:
    root_name = format_root(root, notation)
    if mode == "Scale":
        return scale_title(root_name, type_name)
    symbol = root_name + CHORDS[type_name][0]
    return symbol


def normalize_notation(value) -> str:
    """Also accepts old saved values ("anglaise", "latine")."""
    return "solfege" if value in ("solfege", "latine") else "letters"
