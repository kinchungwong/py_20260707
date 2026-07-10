"""pypiano_2607 -- interactive piano synthesis (promoted from the spikes).

The full public API: pitch conversions, the note-event vocabulary, the
GUI -> audio hand-off queue, and the audio layer (envelope, voices, PolySynth).
"""

from __future__ import annotations

from .pitch import midi_to_freq, cents_to_hz
from .events import NoteEvent, NoteKind, Source
from .queue import EventQueue
from .audio import Envelope, EnvStage, Voice, SineVoice, PianoVoice, PolySynth

__all__ = [
    "midi_to_freq",
    "cents_to_hz",
    "NoteEvent",
    "NoteKind",
    "Source",
    "EventQueue",
    "Envelope",
    "EnvStage",
    "Voice",
    "SineVoice",
    "PianoVoice",
    "PolySynth",
]
