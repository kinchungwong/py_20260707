"""Just-Intonation tuning tests: the 5-limit ratio table + tonic handling in tuning.py.
Pure math -- no pygame, no synth. 12-TET stays the router default (see test_router.py);
here we pin the JI frequencies themselves.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from pypiano_2607.pitch import midi_to_freq
from pypiano_2607.tuning import just_tuning, tonic_to_midi, JI_5LIMIT_RATIOS

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")


def test_tonic_anchored_to_12tet():
    t = just_tuning(60)                                   # tonic C4
    assert t(60) == pytest.approx(midi_to_freq(60))       # the tonic matches equal temperament


def test_just_fifth_and_third():
    t = just_tuning(60)
    ref = midi_to_freq(60)
    assert t(67) == pytest.approx(ref * 3 / 2)            # G4: pure fifth
    assert t(64) == pytest.approx(ref * 5 / 4)            # E4: pure major third


def test_octaves_are_pure():
    t = just_tuning(60)
    assert t(72) == pytest.approx(2 * t(60))              # C5 = 2 * C4
    assert t(84) == pytest.approx(4 * t(60))              # C6 = 4 * C4


def test_below_tonic_wraps_correctly():
    # tonic A4 (69); C4 (60) is 9 semitones below -> a just minor third above A3.
    t = just_tuning(69)
    assert t(60) == pytest.approx(midi_to_freq(69) * 0.5 * (6 / 5))
    assert t(69) == pytest.approx(midi_to_freq(69))       # the tonic itself


def test_ji_differs_from_12tet():
    t = just_tuning(60)
    # the just major third is audibly flatter than the equal-tempered one (~14 cents).
    assert t(64) < midi_to_freq(64)
    assert abs(t(64) - midi_to_freq(64)) > 1.0            # ~2.6 Hz at E4


def test_all_12_degrees_match_the_ratio_table():
    t = just_tuning(60)
    ref = midi_to_freq(60)
    for degree in range(12):
        assert t(60 + degree) == pytest.approx(ref * JI_5LIMIT_RATIOS[degree])


def test_tonic_octave_does_not_matter():
    # only the pitch class of the tonic matters; the octave cancels out.
    a = just_tuning(60)     # C4
    b = just_tuning(72)     # C5
    for m in range(48, 96):
        assert a(m) == pytest.approx(b(m))


def test_tonic_to_midi_names():
    assert tonic_to_midi("C") == 60
    assert tonic_to_midi("A") == 69
    assert tonic_to_midi("F#") == 66
    assert tonic_to_midi("Gb") == 66            # enharmonic
    assert tonic_to_midi("Bb") == 70
    assert tonic_to_midi("bb") == 70            # case-insensitive
    assert tonic_to_midi(" a ") == 69           # whitespace tolerated


def test_sharp_spellings_are_equivalent():
    # A sharp written '#', 's', or as its enharmonic flat all resolve to the same pitch.
    # The 's' and flat forms are shell-safe (no '#' comment character).
    for sharp, s_form, flat, midi in [
        ("C#", "Cs", "Db", 61), ("D#", "Ds", "Eb", 63), ("F#", "Fs", "Gb", 66),
        ("G#", "Gs", "Ab", 68), ("A#", "As", "Bb", 70),
    ]:
        assert tonic_to_midi(sharp) == midi
        assert tonic_to_midi(s_form) == midi
        assert tonic_to_midi(s_form.lower()) == midi     # case-insensitive
        assert tonic_to_midi(flat) == midi
        # the three spellings tune identically
        assert just_tuning(tonic_to_midi(s_form))(72) == pytest.approx(
            just_tuning(tonic_to_midi(flat))(72)
        )


def test_tonic_to_midi_rejects_garbage():
    with pytest.raises(ValueError):
        tonic_to_midi("H")
    with pytest.raises(ValueError):
        tonic_to_midi("Fsharp")


def test_tuning_import_is_pygame_free():
    code = (
        "import sys, pypiano_2607.tuning; "
        "assert 'pygame' not in sys.modules, 'tuning imported pygame eagerly'"
    )
    env = dict(os.environ, PYTHONPATH=_SRC)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
