"""Multi-source input reconciliation: the GUI-edge that MINTS NoteEvents.

Promoted from the input_integration spike's ``InputRouter`` (the reference-counting
logic is unchanged). The one promotion change: ``press``/``release`` now RETURN the
canonical 5-field ``NoteEvent`` -- so this module is where a raw input press becomes
a semantic, sounding event.

``sounder_id = the note's pitch slot`` (the MIDI number, for now): keyboard-C4 and
mouse-C4 reconcile to ONE sounding object, so overlapping presses collapse to exactly
one note-on and one note-off. Because the router also computes ``freq = tuning(midi)``
at emit time (``tuning`` defaults to 12-TET ``midi_to_freq``; pass a Just-Intonation
tuning from ``tuning.py`` for JI), it is the library's **pitch->Hz resolution point** --
the synth downstream never converts MIDI, and an alternate tuning slots in here, upstream
of the unchanged synth.

pygame-free by construction: this module imports only from the package + stdlib, so
importing it never pulls in pygame.
"""

from __future__ import annotations

import time

from .events import NoteEvent, NoteKind, Source
from .pitch import midi_to_freq


class InputRouter:
    """Reconciles note presses from multiple sources into one deduplicated
    note-on/note-off stream. A note sounds while >= 1 source holds it.

    ``press()`` emits a note-on only on the 0->1 transition; ``release()`` emits a
    note-off only on the 1->0 transition; anything else returns None. On the mint
    (0->1), ``sounder_id = midi`` (the pitch slot) and ``freq = tuning(midi)`` (12-TET
    by default; pass a Just-Intonation ``tuning`` from ``tuning.just_tuning`` for JI);
    on release, ``freq`` is None. Keyboard + mouse on the same note therefore
    reconcile to ONE sounding object -- the router is the pitch->Hz resolution point.
    """

    def __init__(self, tuning=midi_to_freq):
        self._holders: dict[int, set[Source]] = {}   # midi -> sources holding it (never empty)
        self._tuning = tuning                        # midi -> Hz; default 12-TET (see tuning.py for JI)

    @property
    def held(self) -> set[int]:
        return set(self._holders)

    def sources(self, midi: int) -> set[Source]:
        return set(self._holders.get(midi, ()))

    def press(self, midi: int, source: Source) -> NoteEvent | None:
        holders = self._holders.get(midi)
        if holders is None:
            self._holders[midi] = {source}
            return NoteEvent(NoteKind.ON, midi, self._tuning(midi), source, time.perf_counter())
        holders.add(source)          # already sounding -> reconciled, no event
        return None

    def release(self, midi: int, source: Source) -> NoteEvent | None:
        holders = self._holders.get(midi)
        if not holders or source not in holders:
            return None              # this source wasn't holding it
        holders.discard(source)
        if not holders:
            del self._holders[midi]
            return NoteEvent(NoteKind.OFF, midi, None, source, time.perf_counter())
        return None                  # still held by another source -> reconciled
