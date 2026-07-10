"""The canonical note-event vocabulary crossing the GUI -> audio thread boundary.

This is exactly the stream that ``EventQueue`` carries and ``PolySynth`` consumes.
Each event carries the frequency to sound (Hz) -- the library never converts MIDI;
callers resolve pitch to Hz via ``pitch`` before emitting.

(The multi-source reconciliation ``InputRouter`` from the input_integration spike is
deliberately NOT promoted here yet -- deferred.)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Source(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"


class NoteKind(Enum):
    ON = "on"
    OFF = "off"


@dataclass(frozen=True)
class NoteEvent:
    kind: NoteKind       # note-on or note-off
    sounder_id: int      # opaque identity of the ACOUSTIC OBJECT this event addresses
                         # (think a guitar/violin STRING or a key resonator) -- NOT a
                         # keyboard key, NOT a pitch. Two events sharing a sounder_id act
                         # on the SAME sounding object: on->off stops it; a 2nd on
                         # retriggers it.
    freq: float | None   # Hz on note-ON; None on note-OFF
    source: Source       # the source that caused this audible transition
    t: float             # time.perf_counter() when emitted
