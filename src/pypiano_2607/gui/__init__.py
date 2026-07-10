"""GUI input layer: the piano-keyboard widget + the QWERTY->MIDI map.

Both submodules import with no pygame (pygame is imported lazily inside the widget's
draw/build functions, and ``qwerty`` takes pygame as an argument), so importing this
package stays headless.
"""

from __future__ import annotations

from .keyboard import (
    Key,
    build_keys,
    offset_keys,
    hit_test,
    note_name,
    render_full,
    redraw_key,
    WIDTH,
    HEIGHT,
    N_WHITE,
)
from .qwerty import WHITE_QWERTY, BLACK_QWERTY, key_to_midi

# Window geometry: the keyboard inset into a margin (promoted from the input_integration
# spike). The app opens a WIN_W x WIN_H window and offsets the keys by MARGIN so that a
# mouse drag onto empty space (-> note-off) stays reachable inside the window.
MARGIN = 24
WIN_W, WIN_H = WIDTH + 2 * MARGIN, HEIGHT + 2 * MARGIN

__all__ = [
    "Key",
    "build_keys",
    "offset_keys",
    "hit_test",
    "note_name",
    "render_full",
    "redraw_key",
    "WIDTH",
    "HEIGHT",
    "N_WHITE",
    "MARGIN",
    "WIN_W",
    "WIN_H",
    "WHITE_QWERTY",
    "BLACK_QWERTY",
    "key_to_midi",
]
