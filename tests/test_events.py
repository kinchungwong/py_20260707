"""NoteEvent + enum vocabulary tests for pypiano_2607.events.

The input_integration spike had no dataclass/enum asserts of its own (its
_selftest exercised the deferred InputRouter, which is NOT promoted here). So
these tests pin down the promoted contract directly: a frozen NoteEvent whose
fields carry through, freq that is a float on ON and None on OFF, value equality
+ hashability, and the Source/NoteKind enum members. Events are built with the
project convention: a MIDI number used AS the sounder_id, freq=midi_to_freq(...).
"""

from __future__ import annotations

import dataclasses
import time

import pytest

from pypiano_2607 import NoteEvent, NoteKind, Source
from pypiano_2607.pitch import midi_to_freq


def _on(sounder_id=60, source=Source.KEYBOARD, t=None):
    return NoteEvent(NoteKind.ON, sounder_id, midi_to_freq(sounder_id), source,
                     t if t is not None else time.perf_counter())


def _off(sounder_id=60, source=Source.KEYBOARD, t=None):
    return NoteEvent(NoteKind.OFF, sounder_id, None, source,
                     t if t is not None else time.perf_counter())


# --- enum members -------------------------------------------------------------

def test_source_members():
    assert Source.KEYBOARD.value == "keyboard"
    assert Source.MOUSE.value == "mouse"
    assert set(Source) == {Source.KEYBOARD, Source.MOUSE}


def test_notekind_members():
    assert NoteKind.ON.value == "on"
    assert NoteKind.OFF.value == "off"
    assert set(NoteKind) == {NoteKind.ON, NoteKind.OFF}


# --- field carry-through ------------------------------------------------------

def test_fields_carry_through_on():
    t = time.perf_counter()
    ev = NoteEvent(NoteKind.ON, 60, midi_to_freq(60), Source.KEYBOARD, t)
    assert ev.kind is NoteKind.ON
    assert ev.sounder_id == 60
    assert ev.freq == pytest.approx(261.6255653, rel=1e-9)  # C4
    assert ev.source is Source.KEYBOARD
    assert ev.t == t


def test_fields_carry_through_off():
    t = time.perf_counter()
    ev = NoteEvent(NoteKind.OFF, 67, None, Source.MOUSE, t)
    assert ev.kind is NoteKind.OFF
    assert ev.sounder_id == 67
    assert ev.freq is None
    assert ev.source is Source.MOUSE
    assert ev.t == t


# --- freq is float on ON, None on OFF ----------------------------------------

def test_freq_is_float_on_note_on():
    ev = _on(69)                       # A4 -> 440.0
    assert isinstance(ev.freq, float)
    assert ev.freq == pytest.approx(440.0, rel=1e-12)


def test_freq_is_none_on_note_off():
    ev = _off(69)
    assert ev.freq is None


# --- frozen -------------------------------------------------------------------

def test_frozen_assignment_raises():
    ev = _on(60)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.sounder_id = 61          # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.freq = 123.0             # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.kind = NoteKind.OFF      # type: ignore[misc]


# --- equality + hashability ---------------------------------------------------

def test_same_fields_equal():
    t = 123.456
    a = NoteEvent(NoteKind.ON, 60, midi_to_freq(60), Source.KEYBOARD, t)
    b = NoteEvent(NoteKind.ON, 60, midi_to_freq(60), Source.KEYBOARD, t)
    assert a == b


def test_differing_field_not_equal():
    t = 123.456
    a = NoteEvent(NoteKind.ON, 60, midi_to_freq(60), Source.KEYBOARD, t)
    # different sounder_id/freq (E4), same everything else -> not equal
    b = NoteEvent(NoteKind.ON, 64, midi_to_freq(64), Source.KEYBOARD, t)
    # different source only
    c = NoteEvent(NoteKind.ON, 60, midi_to_freq(60), Source.MOUSE, t)
    # different kind + freq (a matching OFF)
    d = NoteEvent(NoteKind.OFF, 60, None, Source.KEYBOARD, t)
    assert a != b
    assert a != c
    assert a != d


def test_hashable_and_usable_in_set():
    t = 123.456
    a = NoteEvent(NoteKind.ON, 60, midi_to_freq(60), Source.KEYBOARD, t)
    b = NoteEvent(NoteKind.ON, 60, midi_to_freq(60), Source.KEYBOARD, t)
    c = NoteEvent(NoteKind.OFF, 60, None, Source.KEYBOARD, t)
    # equal events collapse in a set; the OFF is distinct
    assert hash(a) == hash(b)
    assert len({a, b, c}) == 2
    d = {a: "sounding"}
    assert d[b] == "sounding"        # b hashes/equals to a as a dict key


# --- same-sounder ON/OFF pair shares identity, differs in freq ----------------

def test_on_off_pair_shares_sounder_id():
    on = _on(72)                       # C5
    off = _off(72)
    assert on.sounder_id == off.sounder_id
    assert on.freq is not None and off.freq is None
    assert on.kind is NoteKind.ON and off.kind is NoteKind.OFF


# --- docstring documents the sounder_id semantics -----------------------------

def test_sounder_id_documented():
    import pypiano_2607.events as events_mod
    import inspect

    src = inspect.getsource(events_mod)
    assert "sounder_id" in src
    # the acoustic-object semantics are documented somewhere in the module.
    assert "ACOUSTIC OBJECT" in src or "acoustic object" in src.lower()
