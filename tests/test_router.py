"""InputRouter reconciliation tests, ported from the input_integration spike's
_test_router plus the promotion contract: press/release now RETURN the canonical
5-field NoteEvent, minting ``sounder_id == midi`` and ``freq == midi_to_freq(midi)``
on ON / ``None`` on OFF. The router is pygame-free, so nothing here touches SDL.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

from pypiano_2607.router import InputRouter
from pypiano_2607.events import NoteEvent, NoteKind, Source
from pypiano_2607.pitch import midi_to_freq


# --- the ported spike assertion: overlapping presses reconcile ----------------

def test_overlapping_presses_reconcile_to_one_on_one_off():
    r = InputRouter()
    on = r.press(60, Source.KEYBOARD)
    assert on.kind is NoteKind.ON and on.source == Source.KEYBOARD
    assert r.press(60, Source.MOUSE) is None            # overlapping press -> reconciled
    assert r.held == {60}
    assert r.release(60, Source.KEYBOARD) is None        # still held by mouse
    off = r.release(60, Source.MOUSE)
    assert off.kind is NoteKind.OFF and off.source == Source.MOUSE
    assert r.held == set()


def test_independent_notes_pass_through():
    r = InputRouter()
    assert r.press(64, Source.KEYBOARD).kind is NoteKind.ON
    assert r.press(67, Source.MOUSE).kind is NoteKind.ON
    assert r.held == {64, 67}
    assert r.release(64, Source.KEYBOARD).kind is NoteKind.OFF
    assert r.release(67, Source.MOUSE).kind is NoteKind.OFF
    assert r.held == set()


def test_release_of_unheld_note_is_noop():
    r = InputRouter()
    assert r.release(99, Source.MOUSE) is None


# --- the promotion contract: 5-field NoteEvent with sounder_id + freq ---------

def test_press_mints_sounder_id_and_freq():
    r = InputRouter()
    ev = r.press(60, Source.KEYBOARD)
    assert isinstance(ev, NoteEvent)
    assert ev.kind is NoteKind.ON
    assert ev.sounder_id == 60                           # sounder_id == the pitch slot (MIDI)
    assert isinstance(ev.freq, float)
    assert ev.freq == pytest.approx(midi_to_freq(60), rel=1e-12)
    assert ev.source is Source.KEYBOARD
    assert isinstance(ev.t, float)


def test_release_freq_is_none():
    r = InputRouter()
    r.press(69, Source.MOUSE)
    ev = r.release(69, Source.MOUSE)
    assert ev.kind is NoteKind.OFF
    assert ev.sounder_id == 69
    assert ev.freq is None
    assert ev.source is Source.MOUSE


def test_on_off_share_sounder_id():
    r = InputRouter()
    on = r.press(72, Source.KEYBOARD)
    off = r.release(72, Source.KEYBOARD)
    assert on.sounder_id == off.sounder_id == 72


# --- held-set + sources view --------------------------------------------------

def test_held_tracks_reconciled_set():
    r = InputRouter()
    r.press(60, Source.KEYBOARD)
    r.press(60, Source.MOUSE)
    assert r.held == {60}
    assert r.sources(60) == {Source.KEYBOARD, Source.MOUSE}
    r.release(60, Source.KEYBOARD)
    assert r.held == {60}                                # still held by mouse
    assert r.sources(60) == {Source.MOUSE}
    r.release(60, Source.MOUSE)
    assert r.held == set()
    assert r.sources(60) == set()


def test_held_and_sources_return_copies():
    r = InputRouter()
    r.press(60, Source.KEYBOARD)
    held = r.held
    held.add(999)                                        # mutating the view must not leak back
    assert r.held == {60}
    srcs = r.sources(60)
    srcs.add(Source.MOUSE)
    assert r.sources(60) == {Source.KEYBOARD}


def test_double_press_same_source_reconciles():
    r = InputRouter()
    assert r.press(64, Source.KEYBOARD).kind is NoteKind.ON
    assert r.press(64, Source.KEYBOARD) is None          # same source again -> no new event
    # a single release from that source ends it (the set collapses to empty)
    assert r.release(64, Source.KEYBOARD).kind is NoteKind.OFF
    assert r.held == set()


# --- the module stays pygame-free (checked in a fresh process) ----------------

def test_router_import_is_pygame_free():
    # A subprocess with a clean sys.modules: importing the router must NOT drag
    # in pygame (it imports only from the package + stdlib). Done out-of-process
    # because other tests in this session legitimately import pygame.
    code = (
        "import sys, pypiano_2607.router; "
        "assert 'pygame' not in sys.modules, 'router imported pygame eagerly'"
    )
    env = dict(os.environ, PYTHONPATH=_SRC)
    r = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
