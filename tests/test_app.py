"""End-to-end app-layer tests: PianoApp wires keyboard + mouse -> InputRouter ->
EventQueue -> PolySynth, driven headless. Synthetic PyGame events go through the SAME
dispatch() the live loop uses, and the audio callback is driven by hand (no device),
asserting the wired chain reconciles and sounds -- the acceptance behaviors the frozen
playable_instrument spike's --selftest proved, now as deterministic pytest.

SDL dummy drivers are set at module top, BEFORE pygame is imported (PianoApp.__init__
imports + inits pygame), so this runs headless in CI.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import subprocess
import sys

import numpy as np
import pytest

from pypiano_2607.app import PianoApp
from pypiano_2607.events import Source
from pypiano_2607.config import BLOCK_FRAMES

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")


@pytest.fixture
def app():
    """A fresh PianoApp per test (piano voice), closed afterwards so repeated pygame
    set_mode calls don't accumulate display state across tests."""
    a = PianoApp(voice="piano")
    try:
        yield a
    finally:
        a.close()


def _drive(a, n):
    peak = 0.0
    for _ in range(n):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        a.synth.callback(out, BLOCK_FRAMES, None, None)
        peak = max(peak, float(np.abs(out[:, 0]).max()))
    return peak


def _kd(a, ch):
    a.dispatch(a.pygame.event.Event(a.pygame.KEYDOWN, key=a.pygame.key.key_code(ch)))


def _ku(a, ch):
    a.dispatch(a.pygame.event.Event(a.pygame.KEYUP, key=a.pygame.key.key_code(ch)))


def _md(a, pt):
    a.dispatch(a.pygame.event.Event(a.pygame.MOUSEBUTTONDOWN, pos=pt, button=1))


def _mu(a, pt):
    a.dispatch(a.pygame.event.Event(a.pygame.MOUSEBUTTONUP, pos=pt, button=1))


def _mm(a, pt):
    a.dispatch(a.pygame.event.Event(a.pygame.MOUSEMOTION, pos=pt))


def _center(a, midi):
    for k in a.wk + a.bk:
        if k.midi == midi:
            return k.rect.center
    raise KeyError(midi)


def test_keyboard_and_mouse_chord_sounds_two_voices(app):
    _kd(app, "a")                         # C4 via keyboard
    _md(app, _center(app, 67))            # G4 via mouse
    assert app.router.held == {60, 67}
    peak = _drive(app, 20)
    assert app.synth.active_count() == 2
    assert {s for s in app.synth.voice_sounder if s is not None} == {60, 67}
    assert peak > 0.0

    _ku(app, "a")
    _mu(app, _center(app, 67))
    assert app.router.held == set()
    _drive(app, 40)
    assert app.synth.active_count() == 0


def test_focus_loss_is_all_notes_off(app):
    _kd(app, "a")
    _drive(app, 3)
    assert app.synth.active_count() == 1
    app.dispatch(app.pygame.event.Event(app.pygame.WINDOWFOCUSLOST))
    _drive(app, 40)
    assert app.synth.active_count() == 0
    assert app.router.held == set()


def test_same_note_from_both_sources_reconciles_to_one_voice(app):
    _kd(app, "a")                         # C4 keyboard
    _md(app, _center(app, 60))            # C4 mouse -> reconciled, no doubled voice
    assert app.router.held == {60}
    assert app.router.sources(60) == {Source.KEYBOARD, Source.MOUSE}
    _drive(app, 5)
    assert app.synth.active_count() == 1

    _ku(app, "a")                         # keyboard releases, mouse still holds it
    _drive(app, 2)
    assert app.synth.active_count() == 1

    _mu(app, _center(app, 60))            # last holder releases -> note-off
    _drive(app, 40)
    assert app.synth.active_count() == 0


def test_mouse_drag_glissandos(app):
    _md(app, _center(app, 60))            # press C4
    assert app.router.held == {60}
    _mm(app, _center(app, 64))            # drag to E4 -> release C4, press E4
    assert app.router.held == {64}
    _drive(app, 5)
    assert app.synth.active_count() == 1
    _mu(app, _center(app, 64))
    _drive(app, 40)
    assert app.synth.active_count() == 0


def test_focus_loss_resets_an_active_mouse_drag(app):
    # A mouse drag is active when focus is lost: all_notes_off() must reset the
    # glissando too (mirrors the spike's m_down/m_note reset), or a later MOUSEMOTION
    # would mint a phantom note with no button click.
    _md(app, _center(app, 60))            # press + hold C4 with the mouse
    _drive(app, 3)
    assert app.synth.active_count() == 1
    app.dispatch(app.pygame.event.Event(app.pygame.WINDOWFOCUSLOST))
    assert app.glissando.down is False and app.glissando.note is None
    _drive(app, 40)
    assert app.synth.active_count() == 0
    # a subsequent drag-motion must NOT sound a phantom note (button is no longer down)
    _mm(app, _center(app, 64))
    assert app.router.held == set()
    _drive(app, 5)
    assert app.synth.active_count() == 0


def test_hover_without_button_is_silent(app):
    _mm(app, _center(app, 60))            # mouse move, no button held
    assert app.router.held == set()
    _drive(app, 3)
    assert app.synth.active_count() == 0


def test_escape_and_quit_stop_the_loop(app):
    pg = app.pygame
    assert app.dispatch(pg.event.Event(pg.KEYDOWN, key=pg.K_ESCAPE)) is False
    assert app.dispatch(pg.event.Event(pg.QUIT)) is False
    # a mapped note key does NOT stop the loop
    assert app.dispatch(pg.event.Event(pg.KEYDOWN, key=pg.key.key_code("a"))) is True


def test_sine_voice_constructs_and_sounds():
    a = PianoApp(voice="sine")
    try:
        _kd(a, "a")
        peak = _drive(a, 20)
        assert a.synth.active_count() == 1
        assert peak > 0.0
    finally:
        a.close()


def test_ji_tuning_flows_through_and_survives_focus_loss():
    from pypiano_2607.tuning import just_tuning
    from pypiano_2607.pitch import midi_to_freq
    a = PianoApp(voice="sine", tuning=just_tuning(60))    # 5-limit JI, tonic C4
    try:
        ev = a.router.press(67, Source.KEYBOARD)          # G4 -> just fifth, not 12-TET
        assert ev.freq == pytest.approx(midi_to_freq(60) * 3 / 2)
        # 67 is held; focus loss pushes an all-notes-off AND recreates the router --
        # which must KEEP the JI tuning, not silently fall back to 12-TET.
        a.dispatch(a.pygame.event.Event(a.pygame.WINDOWFOCUSLOST))
        assert a.router.held == set()
        ev2 = a.router.press(67, Source.KEYBOARD)
        assert ev2.freq == pytest.approx(midi_to_freq(60) * 3 / 2)
    finally:
        a.close()


def test_app_import_is_pygame_and_sounddevice_free():
    # Importing the app module must not eagerly import pygame or sounddevice (both are
    # imported lazily inside methods). Checked in a clean subprocess.
    code = (
        "import sys, pypiano_2607.app; "
        "assert 'pygame' not in sys.modules, 'app imported pygame eagerly'; "
        "assert 'sounddevice' not in sys.modules, 'app imported sounddevice eagerly'"
    )
    env = dict(os.environ, PYTHONPATH=_SRC)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
