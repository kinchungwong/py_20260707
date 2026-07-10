"""Pluggable audio voices: the pure-timbre generators that PolySynth sums.

Two voices are promoted from the spikes, both implementing the same ``Voice``
interface (``note_on(freq)`` / ``note_off()`` / ``render(frames)`` / ``.env``):

  * ``SineVoice`` -- the phase-continuous sine from realtime_envelope_release.
  * ``PianoVoice`` -- the inharmonic additive piano timbre from piano_voice.

THE AMP-MOVE: both voices now render pure timbre WITHOUT the master ``AMP``
factor (the spikes multiplied AMP in per voice). ``AMP`` is applied ONCE by
``PolySynth`` at the mix stage. Since ``sum(AMP*x_i) == AMP*sum(x_i)`` the audio
output is identical; a voice is now pure timbre, PolySynth owns gain + limiting.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from ..config import (
    SR, TWO_PI, N_PARTIALS, INHARMONICITY, ROLLOFF, TAU0, TAU_DECAY,
)
from .envelope import Envelope, EnvStage


@runtime_checkable
class Voice(Protocol):
    """The pluggable voice interface PolySynth relies on. A voice is a pure-timbre
    oscillator gated by its ``env``; PolySynth applies master gain + limiting."""

    env: Envelope

    def note_on(self, freq: float) -> None: ...
    def note_off(self) -> None: ...
    def render(self, frames: int) -> np.ndarray: ...


class SineVoice:
    """A phase-continuous sine oscillator times its Envelope. Phase accumulates
    across blocks (from the outputstream_callback lesson) so there is no seam
    click; retuning `freq` mid-note just changes the increment, not the phase."""

    def __init__(self, freq: float = 0.0, *, sr: int = SR):
        self.freq = freq
        self.phase = 0.0
        self.sr = sr
        self.env = Envelope(sr=sr)
        self.last_gain: np.ndarray | None = None    # for the selftest to inspect

    def note_on(self, freq: float) -> None:
        """Retune + gate attack. Phase is deliberately NOT reset -> click-free
        retrigger (only the pitch changes). This is the voice interface PolySynth
        calls; a richer voice (partials/decay) implements the same two methods."""
        self.freq = freq
        self.env.note_on()

    def note_off(self) -> None:
        self.env.note_off()

    def render(self, frames: int) -> np.ndarray:
        inc = TWO_PI * self.freq / self.sr
        phases = self.phase + inc * np.arange(1, frames + 1)
        wave = np.sin(phases)
        self.phase = float(phases[-1] % TWO_PI)
        gain = self.env.render(frames)
        self.last_gain = gain
        return (wave * gain).astype(np.float32)


class PianoVoice:
    """Streaming additive piano voice: inharmonic partials with per-partial decay,
    times the gate Envelope. Same interface as `SineVoice`, so `PolySynth` can use it."""

    def __init__(self, *, sr: int = SR, n_partials: int = N_PARTIALS,
                 inharmonicity: float = INHARMONICITY, rolloff: float = ROLLOFF,
                 tau0: float = TAU0, tau_decay: float = TAU_DECAY):
        self.freq = 0.0
        self.sr = sr
        self._n_partials = n_partials
        self._inharmonicity = inharmonicity
        self._rolloff = rolloff
        self.env = Envelope(sr=sr)
        self.last_gain: np.ndarray | None = None
        self._rng = np.random.default_rng()
        k = np.arange(1, n_partials + 1)
        self._taus = tau0 / (1.0 + tau_decay * (k - 1))      # (K,) fixed
        self._k = k
        self._incs = np.zeros(n_partials)                    # per-partial phase increment
        self._amps = np.zeros(n_partials)                    # per-partial amplitude
        self._phase = np.zeros(n_partials)
        self._age = 0                                        # samples since note-on

    def note_on(self, freq: float) -> None:
        self.freq = freq
        k = self._k
        f_k = k * freq * np.sqrt(1.0 + self._inharmonicity * k * k)
        alive = f_k < self.sr / 2.0                          # Nyquist guard
        amps = np.where(alive, 1.0 / (k ** self._rolloff), 0.0)
        s = amps.sum()
        self._amps = amps / s if s > 0 else amps             # normalize partials to unit sum -> pure-timbre voice (master AMP is applied later at the PolySynth mix)
        self._incs = np.where(alive, TWO_PI * f_k / self.sr, 0.0)
        self._phase = self._rng.uniform(0.0, TWO_PI, self._n_partials)   # fresh random phases
        self._age = 0
        self.env.note_on()

    def note_off(self) -> None:
        self.env.note_off()

    def render(self, frames: int) -> np.ndarray:
        idx = np.arange(frames)
        # (K, frames) partial oscillators, phase carried across blocks
        phases = self._phase[:, None] + self._incs[:, None] * (idx[None, :] + 1)
        waves = np.sin(phases)
        self._phase = phases[:, -1] % TWO_PI
        # per-partial exponential decay from onset (age = samples already elapsed)
        t = (self._age + idx) / self.sr
        decay = np.exp(-t[None, :] / self._taus[:, None])    # (K, frames)
        self._age += frames
        tone = (self._amps[:, None] * decay * waves).sum(axis=0)   # (frames,)
        gain = self.env.render(frames)
        self.last_gain = gain
        return (tone * gain).astype(np.float32)
