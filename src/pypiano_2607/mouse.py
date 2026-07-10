"""The mouse-glissando drag state machine: one mouse-driven note at a time.

Promoted from the ``playable_instrument`` / ``input_integration`` spikes' ``_mouse_to``
+ ``m_down``/``m_note`` glue, deferred out of the input layer. Kept pygame-free AND
events-free (stdlib only): the caller feeds hit-test results (a MIDI note int, or
``None`` for "no key under the cursor") and gets back a list of transitions --
``("release", old)`` / ``("press", new)`` -- to route through the ``InputRouter`` with
``Source.MOUSE``. Dragging across keys becomes a glissando: release the old note,
press the new one. Routing through the one router keeps mouse + keyboard reconciled.
"""

from __future__ import annotations


class MouseGlissando:
    """Tracks the single note driven by a held mouse button.

    A left-button drag sounds one note at a time; dragging across keys releases the
    old note and presses the new one (a glissando). The button must be down for
    motion to sound anything -- a bare hover is silent. This class owns only the drag
    state and emits *intent* (``("press"/"release", midi)`` tuples); the caller routes
    each through the ``InputRouter`` so overlapping mouse + keyboard still reconcile.
    """

    def __init__(self):
        self.down: bool = False          # is the (left) mouse button held?
        self.note: int | None = None     # the midi the mouse currently sounds, or None

    def press(self, midi: int | None) -> list[tuple[str, int]]:
        """Left button down over ``midi`` (or ``None`` in the surrounding margin).
        Arms the drag and starts the note under the cursor (if any)."""
        self.down = True
        return self._move_to(midi)

    def motion(self, midi: int | None) -> list[tuple[str, int]]:
        """Cursor moved over ``midi`` (or ``None``). Only sounds while the button is
        down; returns ``[]`` on a bare hover."""
        if not self.down:
            return []
        return self._move_to(midi)

    def release(self) -> list[tuple[str, int]]:
        """Left button up. Ends the current note (if any) and disarms the drag."""
        self.down = False
        return self._move_to(None)

    def _move_to(self, new: int | None) -> list[tuple[str, int]]:
        """Move the single mouse note to ``new`` (or ``None``): release the old, press
        the new -- but only on an actual change."""
        if new == self.note:
            return []
        out: list[tuple[str, int]] = []
        if self.note is not None:
            out.append(("release", self.note))
        if new is not None:
            out.append(("press", new))
        self.note = new
        return out
