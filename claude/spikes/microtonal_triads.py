#!/usr/bin/env python3
"""
SPIKE: Microtonal triads -- major / minor / augmented / diminished / neutral

Question asked
--------------
The first spike (`piano_chord_major_minor.py`) proved major vs. minor by moving
one note between two 12-TET pitches. Can the same synth express the *other*
triad qualities -- augmented, diminished, and especially the **neutral** triad,
whose third lives *between* the minor and major third and does not exist in
12-TET at all?

Key idea (the microtonal move)
------------------------------
Stop describing chords as MIDI integers. Describe each triad as a set of
**intervals in cents above the root**, then `f = root * 2**(cents/1200)`. Cents
are continuous, so the neutral third (350 cents) is no harder to name than the
major third (400). This is the first real step toward the project's
beyond-12-TET vision -- the frequency source is now pluggable, not note-numbered.

    quality       third   fifth      = built from
    major          400     700       major 3rd + minor 3rd
    minor          300     700       minor 3rd + major 3rd
    augmented      400     800       major 3rd + major 3rd
    diminished     300     600       minor 3rd + minor 3rd
    neutral        350     700       neutral 3rd (halfway) + neutral 3rd

What you'll hear
----------------
1. "Third ladder": minor -> neutral -> major, with the perfect fifth held fixed.
   The third rises through the microtonal middle -- this is the money demo.
2. The five qualities in turn: major, minor, augmented, diminished, neutral.

Reuses the piano synth from the first spike (see
`../memory/acoustics/piano-note-synthesis-recipe.md`). Plays through sounddevice AND writes
one .wav per quality plus the full sequence.

Finding
-------
- Yes -- describing triads as cents-above-root generalizes cleanly. The same
  piano synth renders all five qualities with no changes to `synth_note`; only
  the chord-definition layer moved from MIDI ints to cents.
- Verified numerically (FFT, first 0.5 s), root C4 = 261.6 Hz:
    major  third 330 / fifth 392    minor  311 / 392
    aug    330 / 416                 dim    311 / 370
    neutral 320 / 392  <- the third sits *exactly between* min(311) and maj(330).
  No NaNs.
- The neutral third at 350 cents is the proof point: a pitch that has no 12-TET
  name falls out of the cents formula as easily as any other. This is the
  pluggable-frequency-source step the vision needs.
- Gotchas:
    * 350 cents is the equal-tempered "halfway" neutral third; the *just*
      undecimal neutral third is 11/9 ~= 347.4 cents. Close, but if we later
      want just-intonation color, cents should come from ratios, not a fixed
      grid -- worth a future spike.
    * Nothing new re: aliasing/normalization -- inherited from the first spike's
      synth, which held up unchanged for higher roots/fifths.

Run
---
    python claude/spikes/microtonal_triads.py            # play + write wav
    python claude/spikes/microtonal_triads.py --no-play  # write wav only
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

# Reuse the validated piano synth from the first spike (same directory).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from piano_chord_major_minor import (  # noqa: E402
    SR, synth_note, silence, normalize, write_wav, midi_to_hz,
)

ROOT_HZ = midi_to_hz(60)  # C4

# Each triad as (third, fifth) intervals in CENTS above the root.
CHORDS: dict[str, list[float]] = {
    "major":      [0, 400, 700],
    "minor":      [0, 300, 700],
    "augmented":  [0, 400, 800],
    "diminished": [0, 300, 600],
    "neutral":    [0, 350, 700],
}


def cents_to_hz(root_hz: float, cents: float) -> float:
    return root_hz * 2.0 ** (cents / 1200.0)


def synth_triad(cents: list[float], dur: float, *, root_hz: float = ROOT_HZ,
                seed: int = 1) -> np.ndarray:
    """Build a triad from cent-intervals above the root. Reproducible per seed;
    each note still gets its own randomized partial phases."""
    rng = np.random.default_rng(seed)
    notes = [synth_note(cents_to_hz(root_hz, c), dur, rng=rng) for c in cents]
    length = max(len(n) for n in notes)
    chord = np.zeros(length)
    for n in notes:
        chord[: len(n)] += n
    return chord / len(cents)


def build_sequence() -> dict[str, np.ndarray]:
    dur = 1.0
    gap = silence(0.4)

    quals = {name: synth_triad(cents, dur) for name, cents in CHORDS.items()}

    # 1) Third ladder: minor -> neutral -> major, fifth held at 700 cents.
    ladder = np.concatenate([
        quals["minor"], gap, quals["neutral"], gap, quals["major"], gap,
    ])
    # 2) The five qualities in a fixed order.
    parade = np.concatenate([
        v for name in ("major", "minor", "augmented", "diminished", "neutral")
        for v in (quals[name], gap)
    ])

    pieces = {name: normalize(v) for name, v in quals.items()}
    pieces["sequence"] = normalize(np.concatenate([ladder, silence(0.6), parade]))
    return pieces


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-play", action="store_true",
                    help="only write .wav files, do not open the audio device")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    pieces = build_sequence()

    for name, audio in pieces.items():
        path = os.path.join(here, f"triad_{name}.wav")
        write_wav(path, audio)
        print(f"wrote {os.path.relpath(path, here):26s}  {len(audio)/SR:5.2f}s")

    # Show the actual pitches so the microtonal move is legible in the console.
    print("\nthird / fifth frequencies (Hz), root C4 = %.2f:" % ROOT_HZ)
    for name, cents in CHORDS.items():
        f = [cents_to_hz(ROOT_HZ, c) for c in cents]
        print(f"  {name:11s} {cents!s:16s} -> {f[1]:6.1f} {f[2]:6.1f}")

    if args.no_play:
        print("\n--no-play: skipped audio device")
        return

    import sounddevice as sd
    print("\nplaying: third ladder (min->neutral->maj), then the five qualities ...")
    sd.play(pieces["sequence"], SR)
    sd.wait()
    print("done.")


if __name__ == "__main__":
    main()
