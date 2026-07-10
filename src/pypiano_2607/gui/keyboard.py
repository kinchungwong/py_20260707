#!/usr/bin/env python3
"""
Shared piano-keyboard widget for the interactive-GUI spikes.

NOT a spike itself -- this is the small reusable widget extracted from the
`kbd_input` and `mouse_input` spikes once it became clear that every remaining GUI
spike (input_integration, event_queue, envelope, polyphony, ...) draws the same
two-octave keyboard. Keeping it in one place stops the geometry/drawing from
drifting between copies.

Responsibilities (visual + geometry only -- no input mapping, no sound):
  * geometry of a two-octave keyboard (white keys + overlapping black keys),
  * a `Key` = MIDI note + screen rect + black/white flag,
  * building the keys, and optionally offsetting them into a margin,
  * hit-testing a point to a MIDI note (black keys first -- they sit on top),
  * full render + incremental single-key repaint (handling the black-over-white
    overlay wrinkle).

pygame is imported lazily inside the functions that need it, so this module's
constants and `note_name` import with no display -- handy for headless tests and
for code that only wants the geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- geometry ----------------------------------------------------------------

N_OCTAVES = 2
WHITE_PER_OCTAVE = 7
N_WHITE = N_OCTAVES * WHITE_PER_OCTAVE          # 14
WHITE_W, WHITE_H = 60, 260
WIDTH, HEIGHT = N_WHITE * WHITE_W, WHITE_H
BLACK_W, BLACK_H = int(WHITE_W * 0.6), int(WHITE_H * 0.6)
BLACK_AFTER = (0, 1, 3, 4, 5)                   # a black key sits right of these octave white-indices

# White-key MIDI numbers for two octaves starting at C4 (MIDI 60).
WHITE_MIDIS = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83]

# --- colors ------------------------------------------------------------------

BG = (24, 24, 28)
WHITE_KEY = (238, 238, 234)
WHITE_PRESSED = (120, 180, 235)
BLACK_KEY = (18, 18, 20)
BLACK_PRESSED = (70, 120, 180)
BORDER = (70, 70, 76)

_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(midi: int) -> str:
    """MIDI number -> scientific pitch name, e.g. 60 -> 'C4'."""
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


@dataclass
class Key:
    """One piano key: its MIDI note, its screen rect, and whether it's black."""
    midi: int
    rect: "pygame.Rect"   # forward ref; pygame is imported lazily by callers
    is_black: bool


def build_keys():
    """Build the two-octave keyboard at the origin. Returns (white_keys,
    black_keys), each a list of `Key`. Use `offset_keys` to inset it into a margin."""
    import pygame

    white_keys = [
        Key(WHITE_MIDIS[i], pygame.Rect(i * WHITE_W, 0, WHITE_W - 1, WHITE_H), False)
        for i in range(N_WHITE)
    ]

    black_keys = []
    for octave in range(N_OCTAVES):
        for offset in BLACK_AFTER:
            white_index = octave * WHITE_PER_OCTAVE + offset
            boundary_x = (white_index + 1) * WHITE_W
            rect = pygame.Rect(boundary_x - BLACK_W // 2, 0, BLACK_W, BLACK_H)
            black_keys.append(Key(WHITE_MIDIS[white_index] + 1, rect, True))  # sharp above the natural

    return white_keys, black_keys


def offset_keys(keys, dx, dy):
    """Shift every key's rect by (dx, dy). Pass `white_keys + black_keys` to move
    the whole keyboard (e.g. to inset it inside a margin)."""
    for k in keys:
        k.rect = k.rect.move(dx, dy)


def hit_test(pos, white_keys, black_keys):
    """MIDI note under `pos`, or None. Black keys are tested first: they're drawn
    on top of, and overlap, the white keys."""
    for bk in black_keys:
        if bk.rect.collidepoint(pos):
            return bk.midi
    for wk in white_keys:
        if wk.rect.collidepoint(pos):
            return wk.midi
    return None


# --- drawing -----------------------------------------------------------------

def _draw_black(screen, key, held):
    import pygame
    color = BLACK_PRESSED if key.midi in held else BLACK_KEY
    pygame.draw.rect(screen, color, key.rect)


def _draw_white_base(screen, key, held):
    import pygame
    color = WHITE_PRESSED if key.midi in held else WHITE_KEY
    pygame.draw.rect(screen, color, key.rect)
    pygame.draw.rect(screen, BORDER, key.rect, 1)


def render_full(screen, white_keys, black_keys, held):
    """Repaint the whole keyboard: background, all white keys, then all black keys
    on top. `held` is the set of currently-pressed MIDI notes."""
    screen.fill(BG)
    for wk in white_keys:
        _draw_white_base(screen, wk, held)
    for bk in black_keys:
        _draw_black(screen, bk, held)


def redraw_key(screen, midi, white_keys, black_keys, held):
    """Incrementally repaint just the key for `midi`; return its dirty rect (or
    None). Repainting a white key must re-overlay any black key covering it, or
    the fresh white paint would erase the black that sits on top of it."""
    for bk in black_keys:
        if bk.midi == midi:
            _draw_black(screen, bk, held)
            return bk.rect
    for wk in white_keys:
        if wk.midi == midi:
            _draw_white_base(screen, wk, held)
            for bk in black_keys:
                if wk.rect.colliderect(bk.rect):
                    _draw_black(screen, bk, held)
            return wk.rect
    return None
