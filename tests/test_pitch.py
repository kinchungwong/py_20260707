"""Tests for pypiano_2607.pitch -- the library's only pitch knowledge.

These functions are pure and deterministic (no numpy, no SR), so the assertions
are exact where the arithmetic is exact (powers of two, x**0) and tolerance-based
only for the irrational tempered/microtonal ratios.
"""

from __future__ import annotations

import math

import pytest

from pypiano_2607.pitch import cents_to_hz, midi_to_freq


# --- midi_to_freq: the 12-TET map ------------------------------------------

def test_a4_is_440_exactly():
    # MIDI 69 == A4 is the anchor of the 12-TET map; 2**0 == 1 exactly.
    assert midi_to_freq(69) == 440.0


def test_octave_is_exact_doubling():
    # 12 semitones up == one octave == exactly twice the frequency.
    assert midi_to_freq(72) == 2.0 * midi_to_freq(60)
    assert midi_to_freq(81) == 2.0 * midi_to_freq(69)  # A5 == 880
    assert midi_to_freq(81) == 880.0


def test_semitone_ratio():
    # One semitone up multiplies frequency by the 12th root of two.
    ratio = midi_to_freq(70) / midi_to_freq(69)
    assert ratio == pytest.approx(2.0 ** (1.0 / 12.0))
    assert ratio == pytest.approx(1.0594630943592953)


def test_c4_matches_reference():
    # C4 (MIDI 60) is the root used throughout the microtonal spike.
    assert midi_to_freq(60) == pytest.approx(261.6255653005986)


def test_accepts_fractional_midi():
    # midi is a float: a quarter-tone (MIDI 60.5) sits between 60 and 61.
    lo, mid, hi = midi_to_freq(60), midi_to_freq(60.5), midi_to_freq(61)
    assert lo < mid < hi
    # Halfway in MIDI == geometric mean in Hz.
    assert mid == pytest.approx(math.sqrt(lo * hi))


# --- cents_to_hz: the microtonal (beyond-12-TET) move ----------------------

def test_1200_cents_is_octave():
    # 1200 cents == one octave == exactly double; 2**1 == 2 exactly.
    for root in (100.0, 261.6255653005986, 440.0):
        assert cents_to_hz(root, 1200.0) == 2.0 * root


def test_zero_cents_is_identity():
    # 0 cents leaves the root untouched; 2**0 == 1 exactly.
    for root in (100.0, 261.6255653005986, 440.0):
        assert cents_to_hz(root, 0.0) == root


def test_negative_cents_descends():
    # -1200 cents == one octave down == exactly half.
    assert cents_to_hz(440.0, -1200.0) == 220.0


def test_perfect_fifth_ratio():
    # 700 cents is the 12-TET perfect fifth, ~1.4983x above the root.
    assert cents_to_hz(1.0, 700.0) == pytest.approx(1.4983070768766815)


def test_neutral_third_between_minor_and_major():
    # The money demo: the neutral third (350c) has no 12-TET name, yet it lands
    # strictly between the minor (300c) and major (400c) third on the same root.
    root = midi_to_freq(60)  # C4
    minor = cents_to_hz(root, 300.0)
    neutral = cents_to_hz(root, 350.0)
    major = cents_to_hz(root, 400.0)
    assert minor < neutral < major
    # Matches the numbers reported in the microtonal_triads spike finding.
    assert minor == pytest.approx(311.1, abs=0.1)
    assert neutral == pytest.approx(320.2, abs=0.1)
    assert major == pytest.approx(329.6, abs=0.1)


def test_cents_are_additive_in_frequency_ratio():
    # Cents add: stacking 400c then 300c == a single 700c fifth (same root).
    root = 261.6255653005986
    stacked = cents_to_hz(cents_to_hz(root, 400.0), 300.0)
    direct = cents_to_hz(root, 700.0)
    assert stacked == pytest.approx(direct)


# --- the two conversions agree on their shared 12-TET meaning --------------

def test_semitone_equals_100_cents():
    # A 12-TET semitone is 100 cents; both maps must agree on that interval.
    root = midi_to_freq(60)
    from_cents = cents_to_hz(root, 100.0)
    from_midi = midi_to_freq(61)
    assert from_cents == pytest.approx(from_midi)
