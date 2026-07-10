"""Piano-keyboard widget tests (SDL dummy), ported from the piano_keyboard spike
geometry + the kbd_input spike's press/redraw selftest. Covers: 14 white + 10
black keys, note_name, black-first hit-test, whole-keyboard and dirty-rect repaint
(the black-over-white overlay wrinkle), and offset_keys.

pygame is imported LAZILY by the widget, so it is only pulled in when a build/draw
function runs -- the SDL env vars below make that headless.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from pypiano_2607.gui import keyboard as kb
from pypiano_2607.gui.keyboard import (
    N_OCTAVES, WHITE_PER_OCTAVE, N_WHITE, WHITE_W, WHITE_H, WIDTH, HEIGHT,
    BLACK_W, BLACK_H, BLACK_AFTER, WHITE_MIDIS,
    Key, note_name, build_keys, offset_keys, hit_test, render_full, redraw_key,
)


@pytest.fixture(scope="module")
def pygame_display():
    import pygame
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    yield pygame, screen
    pygame.quit()


# --- geometry constants -------------------------------------------------------

def test_geometry_constants():
    assert N_OCTAVES == 2
    assert WHITE_PER_OCTAVE == 7
    assert N_WHITE == 14
    assert WHITE_W == 60 and WHITE_H == 260
    assert WIDTH == N_WHITE * WHITE_W == 840
    assert HEIGHT == WHITE_H == 260
    assert BLACK_W == int(WHITE_W * 0.6) and BLACK_H == int(WHITE_H * 0.6)
    assert BLACK_AFTER == (0, 1, 3, 4, 5)
    assert len(WHITE_MIDIS) == N_WHITE
    assert WHITE_MIDIS[0] == 60 and WHITE_MIDIS[-1] == 83


# --- note_name ----------------------------------------------------------------

def test_note_name():
    assert note_name(60) == "C4"
    assert note_name(61) == "C#4"
    assert note_name(66) == "F#4"
    assert note_name(69) == "A4"
    assert note_name(72) == "C5"
    assert note_name(83) == "B5"


# --- build_keys ---------------------------------------------------------------

def test_build_keys_counts(pygame_display):
    white, black = build_keys()
    assert len(white) == 14
    assert len(black) == 10                       # 5 black per octave * 2 octaves


def test_build_keys_midis(pygame_display):
    white, black = build_keys()
    assert [k.midi for k in white] == WHITE_MIDIS
    # black keys are the sharp above their natural (no E#/B#): C# D# F# G# A#
    assert [k.midi for k in black] == [61, 63, 66, 68, 70, 73, 75, 78, 80, 82]
    assert all(k.is_black for k in black)
    assert all(not k.is_black for k in white)


def test_key_is_dataclass(pygame_display):
    white, _ = build_keys()
    k = white[0]
    assert isinstance(k, Key)
    assert k.midi == 60 and k.is_black is False


# --- hit_test: black-first ----------------------------------------------------

def test_hit_test_white(pygame_display):
    white, black = build_keys()
    # center of the first white key, but low enough to miss the overlapping black
    assert hit_test((WHITE_W // 2, WHITE_H - 10), white, black) == 60


def test_hit_test_black_takes_priority(pygame_display):
    white, black = build_keys()
    # C#4 rect sits centered on the C4/D4 boundary near the top; a point inside it
    # must resolve to the black key even though it overlaps the white region.
    csharp = black[0]
    center = (csharp.rect.centerx, csharp.rect.centery)
    assert hit_test(center, white, black) == 61


def test_hit_test_miss(pygame_display):
    white, black = build_keys()
    assert hit_test((WIDTH + 100, HEIGHT + 100), white, black) is None


# --- offset_keys --------------------------------------------------------------

def test_offset_keys_shifts_and_hit_test_follows(pygame_display):
    white, black = build_keys()
    x0, y0 = white[0].rect.x, white[0].rect.y
    offset_keys(white + black, 24, 24)
    assert white[0].rect.x == x0 + 24 and white[0].rect.y == y0 + 24
    # the origin (0,0) now misses the shifted keyboard
    assert hit_test((0, 0), white, black) is None
    # the shifted first-white center still hits C4
    assert hit_test((24 + WHITE_W // 2, 24 + WHITE_H - 10), white, black) == 60


# --- render + dirty-rect repaint (ported from kbd_input selftest) -------------

def test_render_full_and_press_release_cycle(pygame_display):
    pygame, screen = pygame_display
    white, black = build_keys()
    held: set[int] = set()
    render_full(screen, white, black, held)

    # Play a=C4(60), e=D#4(63), g=G4(67), j=B4(71) -- the spike's chord shape.
    for midi in (60, 63, 67, 71):
        held.add(midi)
        dirty = redraw_key(screen, midi, white, black, held)
        assert dirty is not None
    assert held == {60, 63, 67, 71}

    # a lit white key must show its PRESSED color at a low point (below the black)
    lit_c4 = screen.get_at((WHITE_W // 2, WHITE_H - 10))[:3]
    assert tuple(lit_c4) == kb.WHITE_PRESSED

    # release e -> D#4 no longer held
    held.discard(63)
    redraw_key(screen, 63, white, black, held)
    assert held == {60, 67, 71}

    for midi in (60, 67, 71):
        held.discard(midi)
        redraw_key(screen, midi, white, black, held)
    assert held == set()


def test_redraw_key_returns_none_for_unknown_midi(pygame_display):
    pygame, screen = pygame_display
    white, black = build_keys()
    assert redraw_key(screen, 999, white, black, set()) is None


def test_redraw_white_reoverlays_black(pygame_display):
    """Repainting a white key must re-overlay the black key sitting on it, or the
    fresh white paint erases the black. C4(60) is overlapped by C#4(61)."""
    pygame, screen = pygame_display
    white, black = build_keys()
    render_full(screen, white, black, set())
    csharp = next(b for b in black if b.midi == 61)
    # repaint the white C4 with nothing held; the C#4 pixels must remain black.
    redraw_key(screen, 60, white, black, held=set())
    px = screen.get_at((csharp.rect.centerx, csharp.rect.centery))[:3]
    assert tuple(px) == kb.BLACK_KEY
