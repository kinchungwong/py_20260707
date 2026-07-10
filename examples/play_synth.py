#!/usr/bin/env python3
"""
Ear-test the PROMOTED synth core (src/pypiano_2607) through a real audio device.

This is a demo/ear-test harness, not part of the library. It drives the promoted
`PolySynth` (with `PianoVoice` by default) exactly the way the app will: push
`NoteEvent`s onto the `EventQueue`; the sounddevice callback drains + renders. It
mirrors the piano_voice / polyphony_voices spikes' `_play`, but over the real
package instead of the throwaway spike modules.

The DSP is bit-exact to the already-ear-tested `piano_voice` spike (the promotion's
only numeric change, the AMP-move, is a proven identity), so this is confirmation of
the packaging, not a new sound.

Run (from the repo root):
    .venv/bin/python examples/play_synth.py                 # play a piano chord + arpeggio
    .venv/bin/python examples/play_synth.py --voice sine    # ... with the plain sine voice
    .venv/bin/python examples/play_synth.py --selftest       # headless: render + assert, no device

`--selftest` opens NO device (drives the callback by hand and asserts sound), so it
runs in CI / headless. Everything else needs a real output device.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Make the src-layout package importable without an install (venv policy: no pip).
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pypiano_2607 import (  # noqa: E402
    EventQueue, NoteEvent, NoteKind, Source, PolySynth, PianoVoice, SineVoice,
    midi_to_freq,
)
from pypiano_2607.config import SR, BLOCK_FRAMES  # noqa: E402


def _event(kind: NoteKind, midi: int) -> NoteEvent:
    """Build a note event using the pitch-slot convention: sounder_id == the MIDI
    note, freq == midi_to_freq(midi) on ON (None on OFF)."""
    freq = midi_to_freq(midi) if kind is NoteKind.ON else None
    return NoteEvent(kind, midi, freq, Source.KEYBOARD, time.perf_counter())


def _make_synth(voice: str):
    q = EventQueue()
    factory = PianoVoice if voice == "piano" else SineVoice
    return q, PolySynth(q, voice_factory=factory)


def _play(voice: str) -> None:
    import sounddevice as sd

    q, synth = _make_synth(voice)
    print(f"playing ({voice} voice): held C-major triad (decays), then an "
          "overlapping arpeggio ... Ctrl-C to stop early.")
    # latency='low' is the committed lever (device output ~35 -> ~9 ms).
    with sd.OutputStream(samplerate=SR, channels=1, dtype="float32",
                         callback=synth.callback, latency="low"):
        for m in (60, 64, 67):                       # C4 E4 G4
            q.push(_event(NoteKind.ON, m))
        time.sleep(1.6)
        for m in (60, 64, 67):
            q.push(_event(NoteKind.OFF, m))
        time.sleep(0.4)
        for m in (60, 64, 67, 72, 76, 79, 84):       # overlapping arpeggio
            q.push(_event(NoteKind.ON, m))
            time.sleep(0.22)
        time.sleep(1.2)
        for m in (60, 64, 67, 72, 76, 79, 84):
            q.push(_event(NoteKind.OFF, m))
        time.sleep(0.6)
    if synth.status_flags:
        print(f"note: {synth.status_flags} callback status flags (possible underruns).")
    print("done.")


def _selftest(voice: str) -> None:
    """Headless: drive the callback by hand (no device) and assert the wired path
    makes sound and frees its voices — the same technique the audio spikes use."""
    import numpy as np

    q, synth = _make_synth(voice)
    frames = BLOCK_FRAMES

    def drive(n: int) -> float:
        peak = 0.0
        for _ in range(n):
            out = np.zeros((frames, 1), dtype=np.float32)
            synth.callback(out, frames, None, None)
            peak = max(peak, float(np.abs(out[:, 0]).max()))
        return peak

    for m in (60, 64, 67):
        q.push(_event(NoteKind.ON, m))
    peak = drive(20)
    assert synth.active_count() == 3, synth.active_count()
    assert peak > 0.0, "the wired path produced no sound"
    assert peak <= 1.0, f"hard clip: {peak}"

    for m in (60, 64, 67):
        q.push(_event(NoteKind.OFF, m))
    drive(40)
    assert synth.active_count() == 0, "voices not freed after release"

    print(f"selftest OK ({voice}): C-E-G triad -> 3 voices sounding (peak {peak:.3f}), "
          "released -> 0. No device opened.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", choices=("piano", "sine"), default="piano",
                    help="timbre (default: piano)")
    ap.add_argument("--selftest", action="store_true",
                    help="headless: render + assert, open no device")
    args = ap.parse_args()
    if args.selftest:
        _selftest(args.voice)
    else:
        _play(args.voice)


if __name__ == "__main__":
    main()
