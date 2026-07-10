"""QWERTY -> MIDI layout for computer-keyboard input.

Promoted verbatim from the kbd_input spike: home row = white keys of the lower
octave (a..k = C4..C5); row above = the black keys (w e t y u = C#4 D#4 F#4 G#4 A#4).
Gaps (no black at E-F, B-C) match the physical keyboard -- 'r' and 'i' are
intentionally unmapped.

The maps are plain ``(char, midi)`` lists, so this module imports with no pygame.
``key_to_midi(pygame)`` takes pygame as an argument (rather than importing it) so
the module stays import-time pygame-free -- resolving each char to its key code only
when a caller that already has pygame passes it in.
"""

from __future__ import annotations

# --- QWERTY -> MIDI layout ---------------------------------------------------
# Home row = white keys of the lower octave (a..k = C4..C5); row above = the
# black keys (w e t y u = C#4 D#4 F#4 G#4 A#4). Gaps (no black at E-F, B-C) match
# the physical keyboard -- 'r' and 'i' are intentionally unmapped.
WHITE_QWERTY = [("a", 60), ("s", 62), ("d", 64), ("f", 65),
                ("g", 67), ("h", 69), ("j", 71), ("k", 72)]
BLACK_QWERTY = [("w", 61), ("e", 63), ("t", 66), ("y", 68), ("u", 70)]


def key_to_midi(pygame) -> dict[int, int]:
    """Build {pygame key code -> MIDI note} from the QWERTY map. pygame passed in so this
    module stays import-time pygame-free."""
    return {pygame.key.key_code(ch): m for ch, m in WHITE_QWERTY + BLACK_QWERTY}
