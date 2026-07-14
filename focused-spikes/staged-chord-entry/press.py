"""Short-vs-long key-press classifier -- a small, reusable input primitive.

pygame has no press-duration concept: a press is one KEYDOWN + one KEYUP (no auto-repeat
unless set_repeat is on). This tracks the down-time per keycode and, on release, classifies
the hold as 'short' or 'long' against a threshold. Timestamps are passed IN (the clock is
injected by the caller) so it is deterministic and headless-testable -- no wall-clock inside.

Liftable to focused-spikes/shared/ when the melody spike reuses the same idiom (short =
audition, long = commit). Stdlib only.
"""
from __future__ import annotations


class PressTimer:
    """Classify completed key presses by hold duration. Feed KEYDOWN/KEYUP with a timestamp;
    key_up() returns 'short' or 'long' (or None if the matching down wasn't seen)."""

    def __init__(self, threshold_s: float = 0.20):
        self.threshold_s = threshold_s
        self._down: dict[int, float] = {}          # keycode -> down timestamp (seconds)

    def key_down(self, keycode: int, t: float) -> None:
        self._down[keycode] = t

    def key_up(self, keycode: int, t: float) -> str | None:
        """'long' if held >= threshold, else 'short'; None if no matching key_down is
        tracked (e.g. focus changed mid-press and cancel() ran)."""
        t0 = self._down.pop(keycode, None)
        if t0 is None:
            return None
        return "long" if (t - t0) >= self.threshold_s else "short"

    def cancel(self, keycode: int | None = None) -> None:
        """Drop tracking for one key, or all keys (e.g. on focus loss / mode toggle)."""
        if keycode is None:
            self._down.clear()
        else:
            self._down.pop(keycode, None)
