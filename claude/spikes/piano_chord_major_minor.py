#!/usr/bin/env python3
"""
SPIKE: Piano major vs. minor chord synthesis (sounddevice, no PyGame)

Question asked
--------------
Does Claude know how to synthesize a recognizably *piano-like* chord and render
it through ``sounddevice``, such that a human can clearly hear the difference
between a C major (C-E-G) and a C minor (C-Eb-G) triad?

What this does
--------------
Synthesizes each note from scratch (additive synthesis with inharmonic partials,
per-partial exponential decay, and randomized initial phase -- the ingredients
the project README calls for), sums the notes into a chord, and plays:

    C major (1 s)  ->  gap  ->  C minor (1 s)     [the literal ask]
    then an A/B repeat, and finally the moved third alone (E vs Eb),
    so the ear can localize *what* changed.

It plays through sounddevice AND writes .wav files next to this script so the
finding can be re-heard without re-running (see README: "a spike with no
recorded finding is one you'll run twice").

Finding
-------
- Yes -- additive synthesis with inharmonic partials + per-partial exponential
  decay + phase randomization produces a clearly piano-ish, non-organ tone, and
  the major/minor distinction is unambiguous.
- Verified numerically (FFT of the first 0.5 s): both chords share C (~262 Hz)
  and G (~392 Hz); the *only* moved partial is the third -- major peaks at
  ~330 Hz (E4), minor at ~312 Hz (Eb4). No NaNs; peak normalized to 0.9.
- Gotchas:
    * No scipy in the venv -> WAV written with the stdlib ``wave`` module.
    * Randomized initial phase makes summed-note peak amplitude non-deterministic,
      so normalize the *final* mix rather than trusting per-note headroom.
    * 16 partials with B=4e-4 stays under Nyquist for octave-4 notes; the
      ``f_k >= sr/2`` guard is what stops higher partials from aliasing.
- Distilled the working recipe into claude/memory/piano-note-synthesis-recipe.md.

Run
---
    python claude/spikes/piano_chord_major_minor.py           # play + write wav
    python claude/spikes/piano_chord_major_minor.py --no-play  # write wav only
"""

from __future__ import annotations

import argparse
import os
import wave

import numpy as np

SR = 44100  # sample rate, Hz


# --- pitch -------------------------------------------------------------------

def midi_to_hz(midi: int) -> float:
    """12-TET, A4 (MIDI 69) = 440 Hz. Good enough for a spike; the real app
    will generalize beyond 12-TET (see claude/vision)."""
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


# MIDI numbers for the notes we need, octave 4.
C4, EB4, E4, G4 = 60, 63, 64, 67


# --- synthesis ---------------------------------------------------------------

def synth_note(
    freq: float,
    dur: float,
    *,
    sr: int = SR,
    n_partials: int = 16,
    inharmonicity: float = 4.0e-4,
    tau0: float = 1.6,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """One piano-ish note via additive synthesis.

    Ingredients that make it read as "piano" rather than "organ":
      * inharmonic partials  f_n = n*f0*sqrt(1 + B*n^2)  (stiff-string model)
      * amplitude roll-off with partial index (1/n^1.2)
      * per-partial exponential decay, higher partials decaying faster
      * randomized initial phase per partial (avoids a synthetic all-in-phase attack)
      * short attack ramp + short release fade (no clicks at boundaries)
    """
    if rng is None:
        rng = np.random.default_rng()

    n = np.arange(sr and int(round(dur * sr)))
    t = n / sr
    out = np.zeros_like(t)

    for k in range(1, n_partials + 1):
        f_k = k * freq * np.sqrt(1.0 + inharmonicity * k * k)
        if f_k >= sr / 2:  # past Nyquist -> would alias
            break
        amp = 1.0 / (k ** 1.2)
        tau_k = tau0 / (1.0 + 0.25 * (k - 1))  # higher partials die sooner
        phase = rng.uniform(0.0, 2.0 * np.pi)
        out += amp * np.exp(-t / tau_k) * np.sin(2.0 * np.pi * f_k * t + phase)

    # attack ramp (~6 ms) and release fade (~20 ms) to avoid clicks
    a = min(int(0.006 * sr), len(out))
    r = min(int(0.020 * sr), len(out))
    if a:
        out[:a] *= np.linspace(0.0, 1.0, a)
    if r:
        out[-r:] *= np.linspace(1.0, 0.0, r)

    return out


def synth_chord(midis: list[int], dur: float, *, seed: int = 0) -> np.ndarray:
    """Sum notes into a chord. Each note gets its own RNG stream (per-note phase
    randomization) but the whole chord is reproducible for a given seed."""
    rng = np.random.default_rng(seed)
    notes = [synth_note(midi_to_hz(m), dur, rng=rng) for m in midis]
    length = max(len(x) for x in notes)
    chord = np.zeros(length)
    for x in notes:
        chord[: len(x)] += x
    return chord / len(midis)  # keep headroom; normalized globally later


# --- assembly ----------------------------------------------------------------

def silence(dur: float) -> np.ndarray:
    return np.zeros(int(round(dur * SR)))


def normalize(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def build_sequence() -> dict[str, np.ndarray]:
    """Returns individual pieces plus the full demo sequence."""
    major = synth_chord([C4, E4, G4], 1.0, seed=1)   # C - E  - G
    minor = synth_chord([C4, EB4, G4], 1.0, seed=1)  # C - Eb - G

    # The literal ask: major 1 s, minor 1 s. Then an A/B repeat, then the third
    # alone (E vs Eb) so the listener can localize the single moved note.
    e_note = synth_note(midi_to_hz(E4), 1.0, rng=np.random.default_rng(2))
    eb_note = synth_note(midi_to_hz(EB4), 1.0, rng=np.random.default_rng(2))

    gap = silence(0.4)
    sequence = np.concatenate([
        major, gap, minor, gap,          # the ask
        major, gap, minor, gap,          # A/B repeat for the ear
        normalize(e_note, 0.6), gap,     # "the third that moved": E ...
        normalize(eb_note, 0.6),         # ... vs Eb
    ])

    return {
        "major": normalize(major),
        "minor": normalize(minor),
        "sequence": normalize(sequence),
    }


# --- output ------------------------------------------------------------------

def write_wav(path: str, mono: np.ndarray, sr: int = SR) -> None:
    pcm = np.clip(mono, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm16.tobytes())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-play", action="store_true",
                    help="only write .wav files, do not open the audio device")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    pieces = build_sequence()

    for name, audio in pieces.items():
        path = os.path.join(here, f"chord_{name}.wav")
        write_wav(path, audio)
        dur = len(audio) / SR
        rms = float(np.sqrt(np.mean(audio ** 2)))
        print(f"wrote {os.path.relpath(path, here):24s}  {dur:5.2f}s  rms={rms:.3f}")

    if args.no_play:
        print("--no-play: skipped audio device")
        return

    import sounddevice as sd
    print("\nplaying: C major -> C minor (x2), then E vs Eb ...")
    sd.play(pieces["sequence"], SR)
    sd.wait()
    print("done.")


if __name__ == "__main__":
    main()
