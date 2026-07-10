"""MouseGlissando unit tests -- the single-mouse-note drag state machine promoted
from the playable_instrument / input_integration spikes. Pure logic: no pygame, no
synth, no events. It turns hit-test results (a MIDI int, or None) into
("press"/"release", midi) transitions the app routes through the InputRouter.
"""

from __future__ import annotations

import os
import subprocess
import sys

from pypiano_2607.mouse import MouseGlissando

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")


def test_press_on_a_key_starts_one_note():
    g = MouseGlissando()
    assert g.press(60) == [("press", 60)]
    assert g.down is True
    assert g.note == 60


def test_drag_to_new_key_is_glissando():
    g = MouseGlissando()
    g.press(60)
    assert g.motion(62) == [("release", 60), ("press", 62)]
    assert g.note == 62


def test_drag_to_same_key_is_noop():
    g = MouseGlissando()
    g.press(60)
    assert g.motion(60) == []
    assert g.note == 60


def test_motion_without_button_down_is_silent():
    g = MouseGlissando()
    assert g.motion(60) == []            # bare hover, no button -> nothing
    assert g.down is False
    assert g.note is None


def test_margin_click_then_drag_onto_key():
    g = MouseGlissando()
    assert g.press(None) == []           # click in the margin: arms, no note yet
    assert g.down is True
    assert g.note is None
    assert g.motion(64) == [("press", 64)]   # drag onto a key -> press
    assert g.note == 64


def test_release_ends_the_note_and_disarms():
    g = MouseGlissando()
    g.press(67)
    assert g.release() == [("release", 67)]
    assert g.down is False
    assert g.note is None


def test_release_with_no_note_is_noop():
    g = MouseGlissando()
    g.press(None)                        # armed, no note under cursor
    assert g.release() == []
    assert g.down is False
    assert g.note is None


def test_drag_off_keyboard_then_back():
    g = MouseGlissando()
    g.press(60)
    assert g.motion(None) == [("release", 60)]   # drag onto empty space -> note-off
    assert g.note is None
    assert g.motion(65) == [("press", 65)]       # still down: back onto a key -> press
    assert g.note == 65


def test_mouse_import_is_pygame_free():
    # A clean subprocess: importing the glissando must not drag in pygame.
    code = (
        "import sys, pypiano_2607.mouse; "
        "assert 'pygame' not in sys.modules, 'mouse imported pygame eagerly'"
    )
    env = dict(os.environ, PYTHONPATH=_SRC)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
