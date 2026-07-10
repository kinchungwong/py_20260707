"""Pitch conversions -- the ONLY pitch knowledge in the library.

Pure functions, no numpy, no SR. The synth NEVER converts MIDI: callers turn a
pitch into Hz here and hand the synth a frequency. ``midi_to_freq`` is the
standard 12-TET map; ``cents_to_hz`` is the microtonal, beyond-12-TET move
(frequency as a continuous cents offset above a root).
"""

from __future__ import annotations


def midi_to_freq(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def cents_to_hz(root_hz: float, cents: float) -> float:
    return root_hz * 2.0 ** (cents / 1200.0)
