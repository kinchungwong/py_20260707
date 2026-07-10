"""Tuning: how a MIDI note maps to a frequency (Hz).

The library resolves pitch->Hz at the ``InputRouter`` edge, upstream of the (unchanged)
synth. 12-TET is the default (``pitch.midi_to_freq``); this module adds JUST INTONATION
as an alternative -- a 5-limit 12-tone just scale relative to a chosen tonic. A "tuning"
is any callable ``midi: int -> freq: float``; ``InputRouter(tuning=...)`` takes one, so a
tuning slots in at that edge without touching the synth.

Scope: Just Intonation ONLY. Other microtonal systems (non-12 EDO, arbitrary scales) are
deliberately out of scope here -- they need co-designed UI + mechanics and should begin
as spikes. [[chords-as-cents-above-root]]
"""

from __future__ import annotations

from typing import Callable

from .pitch import midi_to_freq

# 5-limit just intonation: the frequency ratio of each chromatic degree above the tonic
# (index = semitones above the tonic, mod 12). Pure 3/2 fifths and 5/4 major thirds --
# the classic "just" 12-tone scale. Octaves are a pure 2/1.
JI_5LIMIT_RATIOS = (
    1 / 1, 16 / 15, 9 / 8, 6 / 5, 5 / 4, 4 / 3,
    45 / 32, 3 / 2, 8 / 5, 5 / 3, 9 / 5, 15 / 8,
)

# Note name -> pitch class (0..11); upper-cased on lookup. A sharp may be written '#' OR
# 's' (F# == Fs), a flat as 'b' (F# == Gb). The 's' and flat spellings are SHELL-SAFE --
# '#' is the shell's comment character (it works unquoted mid-word, but breaks at a word
# boundary and in Makefiles), so every sharp has a '#'-free spelling.
_NAME_TO_PC = {
    "C": 0, "C#": 1, "CS": 1, "DB": 1, "D": 2, "D#": 3, "DS": 3, "EB": 3, "E": 4,
    "F": 5, "F#": 6, "FS": 6, "GB": 6, "G": 7, "G#": 8, "GS": 8, "AB": 8, "A": 9,
    "A#": 10, "AS": 10, "BB": 10, "B": 11,
}


def tonic_to_midi(name: str) -> int:
    """A tonic note name -> a MIDI number in octave 4 (C4=60). Accepts a sharp as '#' OR
    's' (``F#`` == ``Fs``) and a flat as 'b' (``F#`` == ``Gb``); case- and
    whitespace-insensitive. Only the pitch class matters to ``just_tuning`` (the octave
    cancels out). The 's' and flat spellings avoid the shell's '#' comment character."""
    pc = _NAME_TO_PC.get(name.strip().upper())
    if pc is None:
        raise ValueError(
            f"unknown tonic {name!r}; use a note name C..B with an optional sharp "
            "('#' or 's') or flat ('b') -- e.g. C, A, F#, Fs, Gb, Bb"
        )
    return 60 + pc


def just_tuning(tonic: int = 60) -> Callable[[int], float]:
    """Build a ``midi -> Hz`` tuning for the 5-limit just scale with ``tonic`` (a MIDI
    note, default C4=60) as 1/1. The tonic is anchored to its 12-TET frequency, so it and
    every octave of it match equal temperament exactly; all other notes are just-tuned
    around it, and octaves are pure 2/1. Pass to ``InputRouter(tuning=...)``.
    """
    ref = midi_to_freq(tonic)

    def tuning(midi: int) -> float:
        octave, degree = divmod(midi - tonic, 12)   # divmod floors -> degree in 0..11
        return ref * (2.0 ** octave) * JI_5LIMIT_RATIOS[degree]

    return tuning
