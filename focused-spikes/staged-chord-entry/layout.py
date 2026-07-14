"""Keyboard layout for the staged-chord-entry spike: a 3-octave display plus a movable
input window mapping the computer keyboard onto it.

Feature 1 (from the 2026-07-11 human eval): the physical keyboard's low key count and poor
simultaneity cap how much of a piano you can reach. So the spike shows THREE octaves and
maps the computer keys to a slidable ~1.4-octave *window* over them:

  * home row  a s d f g h j k l ; '   -> the white keys, starting at the MIDDLE octave
    (a..j == C4..B4 exactly), reaching up through C5 D5 E5 F5;
  * upper row w e   t y u     o p     -> the matching black keys (E-F and B-C gaps, as on
    a real piano; 'r'/'i' stay unmapped);
  * q and \\  slide the whole window down / up by one semitone. The slide RE-AIMS future
    input only -- already-held/committed notes keep their pitch (the pinned decision).

Only the library's Key dataclass + note_name are reused; its build_keys() is hard-wired to
two octaves, so the 3-octave geometry is rebuilt here (same pattern, N_OCTAVES = 3). The
spike does not edit src/.
"""
from __future__ import annotations

import pygame

from pypiano_2607.gui import Key, note_name

# --- 3-octave geometry (mirrors pypiano_2607.gui.keyboard, widened to 3 octaves) --------
N_OCTAVES = 3
START_MIDI = 48                              # C3 -- so the middle octave is C4..B4
WHITE_PER_OCTAVE = 7
N_WHITE = N_OCTAVES * WHITE_PER_OCTAVE        # 21
WHITE_W, WHITE_H = 60, 260                    # same key size as the library widget
BLACK_W, BLACK_H = int(WHITE_W * 0.6), int(WHITE_H * 0.6)
WIDTH, HEIGHT = N_WHITE * WHITE_W, WHITE_H     # 1260 x 260
_WHITE_STEPS = (0, 2, 4, 5, 7, 9, 11)          # semitones of the white keys within an octave
_BLACK_AFTER = (0, 1, 3, 4, 5)                 # a black key sits right of these octave white-indices
MIN_MIDI = START_MIDI
MAX_MIDI = START_MIDI + 12 * N_OCTAVES - 1     # B5 = 83


def build_keyboard():
    """Build the 3-octave keyboard at the origin -> (white_keys, black_keys) of library Keys.
    Inset it below the HUD with pypiano_2607.gui.offset_keys, exactly as with build_keys()."""
    white_midis = [START_MIDI + 12 * o + s for o in range(N_OCTAVES) for s in _WHITE_STEPS]
    white_keys = [
        Key(white_midis[i], pygame.Rect(i * WHITE_W, 0, WHITE_W - 1, WHITE_H), False)
        for i in range(N_WHITE)
    ]
    black_keys = []
    for o in range(N_OCTAVES):
        for off in _BLACK_AFTER:
            wi = o * WHITE_PER_OCTAVE + off
            bx = (wi + 1) * WHITE_W
            black_keys.append(Key(white_midis[wi] + 1,
                                  pygame.Rect(bx - BLACK_W // 2, 0, BLACK_W, BLACK_H), True))
    return white_keys, black_keys


# --- the movable input window -----------------------------------------------------------
ANCHOR_MIDI = 60                              # 'a' targets C4 at offset 0 (top of the middle octave)

# physical key -> semitones above the anchor. Home row = the white naturals; upper row = the
# black keys that sit between them; k l ; ' and o p extend the reach up into the next octave.
_WHITE_LAYOUT = [("a", 0), ("s", 2), ("d", 4), ("f", 5), ("g", 7), ("h", 9), ("j", 11),
                 ("k", 12), ("l", 14), (";", 16), ("'", 17)]
_BLACK_LAYOUT = [("w", 1), ("e", 3), ("t", 6), ("y", 8), ("u", 10), ("o", 13), ("p", 15)]
_LAYOUT = _WHITE_LAYOUT + _BLACK_LAYOUT
_SPAN_LO = min(s for _, s in _LAYOUT)          # 0
_SPAN_HI = max(s for _, s in _LAYOUT)          # 17


class InputWindow:
    """Maps computer-key codes to MIDI notes through a slidable offset. shift() moves the
    window; resolve() answers 'what pitch does this key target right now'. The clamp keeps
    the whole window inside the 3-octave display."""

    def __init__(self):
        self._semitone = {pygame.key.key_code(ch): s for ch, s in _LAYOUT}
        self.offset = 0
        self._off_min = MIN_MIDI - (ANCHOR_MIDI + _SPAN_LO)     # -12
        self._off_max = MAX_MIDI - (ANCHOR_MIDI + _SPAN_HI)     # +6

    def resolve(self, keycode) -> int | None:
        """MIDI this key targets at the current offset, or None if it isn't a note key."""
        s = self._semitone.get(keycode)
        return None if s is None else ANCHOR_MIDI + s + self.offset

    def shift(self, delta: int) -> bool:
        """Slide by delta semitones (clamped to keep the window on-screen). Returns True iff
        the offset actually moved."""
        new = max(self._off_min, min(self._off_max, self.offset + delta))
        moved = new != self.offset
        self.offset = new
        return moved

    @property
    def span(self) -> tuple[int, int]:
        """(lowest, highest) MIDI currently reachable by the mapped keys."""
        return (ANCHOR_MIDI + _SPAN_LO + self.offset, ANCHOR_MIDI + _SPAN_HI + self.offset)

    def bound_midis(self) -> set[int]:
        """The set of MIDI notes a mapped key currently targets (for the window indicator)."""
        return {ANCHOR_MIDI + s + self.offset for s in self._semitone.values()}

    def labels(self) -> dict[int, tuple[str, str]]:
        """midi -> (KEYCHAR, note_name) for every currently-bound key, for the painter."""
        return {ANCHOR_MIDI + s + self.offset: (ch.upper(), note_name(ANCHOR_MIDI + s + self.offset))
                for ch, s in _LAYOUT}


# --- row-delimited key zones ------------------------------------------------------------
# Zones organize the computer keyboard BY ROW, each delimited by a leftmost/rightmost key
# (e.g. "bottom row, z..m"). v1 uses a single launcher zone; the structure lives here so
# future zones (and eventual reconfiguration) are data, not a rewrite. Rows are the letter
# portion of a QWERTY board, left-to-right.
_ROWS = {
    "number": list("1234567890-="),
    "upper":  list("qwertyuiop"),
    "home":   list("asdfghjkl;'"),
    "bottom": list("zxcvbnm,./"),
}


def _row_span(row: str, left: str, right: str) -> list[str]:
    """The contiguous run of key chars in `row` from `left` to `right`, inclusive."""
    keys = _ROWS[row]
    i, j = keys.index(left), keys.index(right)
    if i > j:
        i, j = j, i
    return keys[i:j + 1]


class KeyZone:
    """A contiguous run of keys within ONE physical keyboard row, delimited by its leftmost
    and rightmost key char and tagged with a role. Resolves computer keycodes to 0-based slot
    indices within the zone. (v1 has one launcher zone; the model generalizes.)"""

    def __init__(self, row: str, left: str, right: str, role: str):
        self.row, self.role = row, role
        self.chars = _row_span(row, left, right)
        self.keycodes = [pygame.key.key_code(c) for c in self.chars]
        self._slot = {kc: i for i, kc in enumerate(self.keycodes)}

    def slot_of(self, keycode) -> int | None:
        """0-based slot index of this keycode within the zone, or None if outside it."""
        return self._slot.get(keycode)

    def char(self, slot: int) -> str:
        """Upper-case key char for a slot index (for labels/hints)."""
        return self.chars[slot].upper()

    def __len__(self) -> int:
        return len(self.keycodes)


def default_launcher_zone() -> KeyZone:
    """The default launcher zone: the bottom row from z to m inclusive (7 slots)."""
    return KeyZone("bottom", "z", "m", "launcher")
