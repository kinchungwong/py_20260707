"""Extra PolySynth coverage the promotion added: the callback's status path, the
float32 render contract, and the "steal the QUIETEST voice" branch of allocation.

CONVENTION (matching test_polysynth.py): a sounder_id is a MIDI int and the ON
frequency is ``midi_to_freq(that int)``. SineVoice is used where a deterministic
(no-RNG) voice keeps the allocation bookkeeping easy to inspect.
"""

from __future__ import annotations

import time

import numpy as np

from pypiano_2607 import (
    PolySynth, SineVoice, EventQueue, NoteEvent, NoteKind, Source, EnvStage,
    midi_to_freq,
)
from pypiano_2607.config import BLOCK_FRAMES


def _on(midi):
    return NoteEvent(NoteKind.ON, midi, midi_to_freq(midi), Source.KEYBOARD, time.perf_counter())


def _off(midi):
    return NoteEvent(NoteKind.OFF, midi, None, Source.KEYBOARD, time.perf_counter())


def _drive(synth, n_blocks):
    for _ in range(n_blocks):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)


def test_callback_status_increments_flag_only_when_truthy():
    """A truthy PortAudio ``status`` bumps status_flags by one; status=None does not."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=2)
    out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)

    synth.callback(out, BLOCK_FRAMES, None, None)
    assert synth.status_flags == 0                     # None -> no increment
    synth.callback(out, BLOCK_FRAMES, None, "input overflow")
    assert synth.status_flags == 1                     # truthy -> +1
    synth.callback(out, BLOCK_FRAMES, None, None)
    assert synth.status_flags == 1                     # None again -> unchanged


def test_render_returns_float32():
    """render() returns the callback buffer dtype (float32) regardless of activity."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=4)
    assert synth.render(BLOCK_FRAMES).dtype == np.float32


def test_steal_reassigns_the_quietest_releasing_voice():
    """With the pool full, a new note-on steals the QUIETEST voice. A releasing voice
    has the lowest env.level, so it -- not the still-held sustain voice -- is the one
    reassigned to the new sounder."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=2, voice_factory=SineVoice)
    q.push(_on(60))
    q.push(_on(64))
    _drive(synth, 30)                                  # both reach SUSTAIN (level 1.0)

    slot_a = synth.voice_sounder.index(60)
    slot_b = synth.voice_sounder.index(64)
    assert synth.voices[slot_a].env.stage is EnvStage.SUSTAIN
    assert synth.voices[slot_b].env.stage is EnvStage.SUSTAIN

    q.push(_off(60))                                   # release sounder 60 only
    _drive(synth, 1)                                   # partway through its release ramp
    # pre-steal: slot_a is releasing (lower level); slot_b is still held at sustain.
    assert synth.voices[slot_a].env.stage is EnvStage.RELEASE
    assert synth.voices[slot_b].env.stage is EnvStage.SUSTAIN
    assert synth.voices[slot_a].env.level < synth.voices[slot_b].env.level

    q.push(_on(67))                                    # pool full -> steal the quietest
    _drive(synth, 1)
    # the releasing (quietest) voice was reassigned to 67; the held one is untouched.
    assert synth.voice_sounder[slot_a] == 67, "did not steal the quietest (releasing) voice"
    assert synth.voice_sounder[slot_b] == 64, "the held sustain voice was wrongly stolen"
