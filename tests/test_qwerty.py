"""QWERTY->MIDI map tests, ported from the kbd_input spike layout. The (char,midi)
lists import with no pygame; key_to_midi(pygame) resolves them to key codes only
when pygame is passed in (SDL dummy makes that headless).
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from pypiano_2607.gui.qwerty import WHITE_QWERTY, BLACK_QWERTY, key_to_midi


# --- the map is well-formed ---------------------------------------------------

def test_white_qwerty_layout():
    assert WHITE_QWERTY == [("a", 60), ("s", 62), ("d", 64), ("f", 65),
                            ("g", 67), ("h", 69), ("j", 71), ("k", 72)]


def test_black_qwerty_layout():
    assert BLACK_QWERTY == [("w", 61), ("e", 63), ("t", 66), ("y", 68), ("u", 70)]


def test_thirteen_keys_mapped():
    assert len(WHITE_QWERTY) + len(BLACK_QWERTY) == 13


def test_chars_unique_and_midis_unique():
    pairs = WHITE_QWERTY + BLACK_QWERTY
    chars = [c for c, _ in pairs]
    midis = [m for _, m in pairs]
    assert len(set(chars)) == len(chars)          # no char bound twice
    assert len(set(midis)) == len(midis)          # no MIDI bound twice


def test_white_are_naturals_black_are_sharps():
    # naturals: C D E F G A B (pitch class not in the sharp set)
    sharps = {1, 3, 6, 8, 10}
    assert all((m % 12) not in sharps for _, m in WHITE_QWERTY)
    assert all((m % 12) in sharps for _, m in BLACK_QWERTY)


def test_span_is_one_octave_plus_c():
    all_midis = sorted(m for _, m in WHITE_QWERTY + BLACK_QWERTY)
    assert min(all_midis) == 60 and max(all_midis) == 72   # C4..C5


# --- key_to_midi(pygame) resolves to key codes --------------------------------

def test_key_to_midi_maps_key_codes():
    import pygame
    pygame.init()
    try:
        mapping = key_to_midi(pygame)
        assert len(mapping) == 13
        assert mapping[pygame.key.key_code("a")] == 60
        assert mapping[pygame.key.key_code("w")] == 61
        assert mapping[pygame.key.key_code("k")] == 72
        # every mapped value is one of the layout's MIDI notes
        assert set(mapping.values()) == {m for _, m in WHITE_QWERTY + BLACK_QWERTY}
    finally:
        pygame.quit()
