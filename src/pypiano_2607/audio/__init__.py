"""Audio synthesis layer: envelope, pluggable voices, and the polyphonic synth."""

from __future__ import annotations

from .envelope import Envelope, EnvStage
from .voice import Voice, SineVoice, PianoVoice
from .polysynth import PolySynth

__all__ = [
    "Envelope",
    "EnvStage",
    "Voice",
    "SineVoice",
    "PianoVoice",
    "PolySynth",
]
