"""Lightweight one-shot audition beeps via pygame.mixer -- the staged-entry preview.

Deliberately SELF-CONTAINED: imports only numpy + pygame, NOT pypiano_2607. This is the
"second acoustic authority" the spike knowingly takes on (see status_active.md's
graduation note) -- a throwaway ~0.2s sine reminding the player what a key sounds like the
moment it is staged, decoupled from the real synth's sounder_id / EventQueue model.

Why pygame.mixer and not the library synth (verified before building this spike):
  * Sound.play() returns in ~5us -> non-blocking; never stalls the 60fps loop.
  * a fixed-length buffer AUTO-STOPS at its end -> one-shot, no note-off bookkeeping.
  * overlapping beeps land on separate mixer channels -> a fast C-E-G staging burst
    all sounds.
  * coexists cleanly with the main sounddevice OutputStream (0 xruns steady-state) as
    long as the mixer is initialised at boot, before the stream opens.

The mixer must already be initialised (the app calls pygame.mixer.pre_init(...) before
pygame.init()); if it is not (e.g. a headless run with no audio device), auditions no-op.
"""
from __future__ import annotations

import numpy as np
import pygame


def _hz(midi: int) -> float:
    """12-TET midi -> Hz, inlined so this module needs no library import. The audition is
    a deliberately plain, tuning-agnostic reminder -- committed notes use the real tuning;
    the preview does not need to."""
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


class Audition:
    """Pre-rendered short sine beeps, one per staged-able midi, played fire-and-forget."""

    def __init__(self, midis, *, sr: int, dur_s: float = 0.2, fade_ms: float = 5.0,
                 vol: float = 0.25):
        self.dur_s = dur_s          # one knob: flip to 0.1 later
        self._sr = sr
        self._sounds: dict[int, "pygame.mixer.Sound"] = {}
        if pygame.mixer.get_init() is None:
            return                  # no mixer (headless / no audio) -> silent no-op
        for m in midis:
            self._sounds[m] = self._render(_hz(m), dur_s, fade_ms, vol)

    def _render(self, freq_hz, dur_s, fade_ms, vol):
        n = int(self._sr * dur_s)
        t = np.arange(n) / self._sr
        wave = np.sin(2.0 * np.pi * freq_hz * t) * vol
        f = int(self._sr * fade_ms / 1000.0)
        if f > 0:
            ramp = np.linspace(0.0, 1.0, f)
            wave[:f] *= ramp        # tiny fades so the hard-truncated sine doesn't click
            wave[-f:] *= ramp[::-1]
        return pygame.sndarray.make_sound((wave * 32767).astype(np.int16))

    def play(self, midi: int) -> None:
        snd = self._sounds.get(midi)
        if snd is not None:
            snd.play()              # non-blocking; auto-stops at the buffer's end
