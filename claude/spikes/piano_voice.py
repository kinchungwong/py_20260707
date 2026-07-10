#!/usr/bin/env python3
"""
SPIKE: bring the batch synth's piano timbre into the STREAMING voice -- inharmonic
       partials + per-partial decay + phase randomization, per block, drop-in to
       PolySynth

Question asked
--------------
`piano_chord_major_minor.synth_note` makes a convincingly piano-ish tone (16
inharmonic partials, `1/k^1.2` roll-off, per-partial exponential decay, randomized
phase) -- but as ONE fixed buffer. The streaming `Voice` (realtime_envelope_release)
is a single flat sine. Can we fold that timbre into the streaming, per-block,
polyphonic path -- and can we AFFORD it (16 partials x 16 voices per audio block,
against the ~2.15 ms deadline of `latency='low'` ~95-frame blocks)?

What this does
--------------
`PianoVoice` implements the same interface as `Voice` (`note_on(freq)`,
`note_off()`, `render(frames)`, `.env`), so it drops straight into `PolySynth` via
its new `voice_factory`. Internals:
  * K inharmonic partials `f_k = k*f0*sqrt(1+B*k^2)`, amplitudes `1/k^1.2`
    (normalized to sum 1), computed at note-on (Nyquist-guarded), vectorized as a
    `(K, frames)` block -- one `sin` and one `exp` per voice per block.
  * Per-partial exponential decay `exp(-t/tau_k)` from a per-voice sample `age`, so
    a HELD note DECAYS naturally (piano) instead of flat-sustaining (organ).
  * Randomized per-partial phase at note-on.
  * The SAME gate `Envelope` (6 ms attack / 20 ms release) multiplies on top, for
    click-free onset and click-free key-release.

Trade-off surfaced (not hidden): note-on re-inits phase + age, so a voice STEAL is
no longer phase-continuous like the pure-sine voice -- it injects a small artifact
scaled by the stolen voice's gate level. We steal the QUIETEST voice, so it's small
(measured below); a crossfade-steal is the clean fix (deferred, as in polyphony_voices).

Finding
-------
- YES, the batch timbre folds cleanly into the streaming voice, and it's
  AFFORDABLE. `PianoVoice` is a drop-in for `Voice` (via `PolySynth`'s new
  `voice_factory`); no other code changed.
- Richness confirmed: a PianoVoice shows ~5 audible partials (>=10% of the
  fundamental within the window; more exist but roll off / decay), vs exactly 1
  for the sine. The FFT (see PNG) is the inharmonic partial series of the recipe.
- The biggest audible change is the per-partial exponential decay: a HELD note now
  DECAYS naturally (peak ~0.11 -> ~0.03 over 1.5 s) instead of flat-sustaining.
  That's the organ->piano difference, and it's the point.
- COST (the real question): 16 PianoVoices render in ~2240 us/383-block = ~26% of
  the 8.68 ms deadline (vs ~242 us / 2.8% for 16 sine voices -- ~9x). At
  `latency='low'` (~95-frame, 2.15 ms deadline) it's ~846 us = ~39%. So full
  16-voice piano polyphony fits with ~60% headroom even in the low-latency case.
  Vectorizing the partials into one `(K, frames)` block (one `sin` + one `exp` per
  voice) is what keeps it cheap; a per-partial Python loop would not.
- Click-free onset/key-release still hold (the gate attacks from 0 and releases to
  0; the partials sit inside the gate). Single fresh notes are clean.
- Steal is the honest regression: note-on re-inits phase + age, so a steal is not
  phase-continuous -- measured max step ~0.125 (vs ~0.05 for the pure-sine pool).
  It's a small artifact, not a hard click (no clip), because we steal the QUIETEST
  voice so it's scaled by a low gate level. Crossfade-steal remains the clean fix
  (deferred, as flagged in polyphony_voices).
- Not addressed (noted): a held-but-fully-decayed note still holds its voice slot
  (gate is SUSTAIN though it's silent) -- a voice-reclaim-below-threshold refinement.
- Verdict: worth promoting `PianoVoice` into the real path (playable_instrument via
  `voice_factory=PianoVoice`). Left as a follow-up so a human can A/B the sound
  first.

Run
---
    python claude/spikes/piano_voice.py             # play a rich chord + arpeggio for real
    python claude/spikes/piano_voice.py --selftest  # headless: richness/click/cost asserts + PNG
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from event_queue import EventQueue, SR, BLOCK_FRAMES, BLOCK_PERIOD, NoteKind, Source
from realtime_envelope_release import Envelope, EnvStage, Voice, midi_to_freq, note_event, AMP, TWO_PI
from polyphony_voices import PolySynth

N_PARTIALS = 16
INHARMONICITY = 4.0e-4      # B in f_k = k*f0*sqrt(1 + B*k^2)  (stiff-string model)
ROLLOFF = 1.2               # partial amplitude ~ 1/k^ROLLOFF
TAU0 = 1.6                  # fundamental decay time constant (s)
TAU_DECAY = 0.25            # higher partials die sooner: tau_k = TAU0 / (1 + TAU_DECAY*(k-1))


class PianoVoice:
    """Streaming additive piano voice: inharmonic partials with per-partial decay,
    times the gate Envelope. Same interface as `Voice`, so `PolySynth` can use it."""

    def __init__(self):
        self.freq = 0.0
        self.env = Envelope()
        self.last_gain: np.ndarray | None = None
        self._rng = np.random.default_rng()
        k = np.arange(1, N_PARTIALS + 1)
        self._taus = TAU0 / (1.0 + TAU_DECAY * (k - 1))      # (K,) fixed
        self._k = k
        self._incs = np.zeros(N_PARTIALS)                    # per-partial phase increment
        self._amps = np.zeros(N_PARTIALS)                    # per-partial amplitude
        self._phase = np.zeros(N_PARTIALS)
        self._age = 0                                        # samples since note-on

    def note_on(self, freq: float) -> None:
        self.freq = freq
        k = self._k
        f_k = k * freq * np.sqrt(1.0 + INHARMONICITY * k * k)
        alive = f_k < SR / 2.0                               # Nyquist guard
        amps = np.where(alive, 1.0 / (k ** ROLLOFF), 0.0)
        s = amps.sum()
        self._amps = amps / s if s > 0 else amps             # normalize -> per-voice peak ~ AMP
        self._incs = np.where(alive, TWO_PI * f_k / SR, 0.0)
        self._phase = self._rng.uniform(0.0, TWO_PI, N_PARTIALS)   # fresh random phases
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
        t = (self._age + idx) / SR
        decay = np.exp(-t[None, :] / self._taus[:, None])    # (K, frames)
        self._age += frames
        tone = (self._amps[:, None] * decay * waves).sum(axis=0)   # (frames,)
        gain = self.env.render(frames)
        self.last_gain = gain
        return (AMP * tone * gain).astype(np.float32)


# --- helpers ------------------------------------------------------------------

def _drive(synth, n, sink=None):
    for _ in range(n):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)
        if sink is not None:
            sink.append(out[:, 0].copy())


def _harmonic_strengths(sig, f0):
    """Magnitude at each partial frequency, normalized to the fundamental."""
    w = np.hanning(len(sig))
    mag = np.abs(np.fft.rfft(sig * w))
    freqs = np.fft.rfftfreq(len(sig), 1.0 / SR)
    out = []
    for k in range(1, N_PARTIALS + 1):
        f_k = k * f0 * np.sqrt(1.0 + INHARMONICITY * k * k)
        if f_k >= SR / 2.0:
            break
        out.append(float(mag[np.argmin(np.abs(freqs - f_k))]))
    out = np.array(out)
    return out / out[0] if out[0] > 0 else out


def _render_one(voice_factory, midi, n_samples, limit=False):
    """Render a single sustained voice's linear output (no limiter)."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=1, voice_factory=voice_factory)
    q.push(note_event(NoteKind.ON, midi))
    chunks = []
    total = 0
    while total < n_samples:
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)      # first call drains the note-on
        chunks.append(out[:, 0].copy())
        total += BLOCK_FRAMES
    return np.concatenate(chunks)[:n_samples].astype(np.float64)


def _measure_cost(voice_factory, frames, max_voices=16, k=200):
    q = EventQueue()
    synth = PolySynth(q, max_voices=max_voices, voice_factory=voice_factory)
    for n in range(max_voices):
        q.push(note_event(NoteKind.ON, 45 + n))
    for _ in range(4):
        out = np.zeros((frames, 1), dtype=np.float32)
        synth.callback(out, frames, None, None)
    assert synth.active_count() == max_voices
    t0 = time.perf_counter()
    for _ in range(k):
        out = np.zeros((frames, 1), dtype=np.float32)
        synth.callback(out, frames, None, None)
    return (time.perf_counter() - t0) / k


# --- headless self-test -------------------------------------------------------

def _selftest() -> None:
    piano = PianoVoice
    sine = lambda: Voice(0.0)

    # 1. Richness: a PianoVoice has many partials; a sine voice has ~one.
    f0 = midi_to_freq(60)
    piano_sig = _render_one(piano, 60, 16384)
    sine_sig = _render_one(sine, 60, 16384)
    hp = _harmonic_strengths(piano_sig, f0)
    hs = _harmonic_strengths(sine_sig, f0)
    piano_partials = int(np.sum(hp >= 0.1))
    sine_partials = int(np.sum(hs >= 0.1))
    assert piano_partials >= 4, f"piano voice not rich: {piano_partials} partials"
    assert sine_partials == 1, f"sine voice should be one partial: {sine_partials}"
    assert hp[1] >= 0.1 and hp[2] >= 0.1, "missing 2nd/3rd partials"

    # 2. Natural decay: a HELD PianoVoice gets quieter over time (piano, not organ).
    held = _render_one(piano, 60, int(1.5 * SR))
    early = float(np.abs(held[:BLOCK_FRAMES]).max())
    late = float(np.abs(held[-BLOCK_FRAMES:]).max())
    assert late < 0.6 * early, f"held note did not decay: early {early:.3f} late {late:.3f}"

    # 3. Click-free fresh note (onset gated from 0, release ramped) + no clip.
    q = EventQueue()
    synth = PolySynth(q, max_voices=4, voice_factory=piano)
    audio = []
    q.push(note_event(NoteKind.ON, 60))
    _drive(synth, 24, audio)
    q.push(note_event(NoteKind.OFF, 60))
    _drive(synth, 40, audio)
    a1 = np.concatenate(audio).astype(np.float64)
    assert float(np.abs(a1).max()) <= 1.0
    v = synth.voices[0]
    # bound: worst per-sample slope of the partial sum + one envelope step
    slope = AMP * float(np.sum(np.abs(v._amps) * np.abs(v._incs)))
    assert float(np.abs(np.diff(a1)).max()) <= (slope + AMP * v.env.attack_step) * 1.5 + 1e-6

    # 4. Steal artifact: overflow a 4-voice pool; report the max step, assert no clip.
    q = EventQueue()
    synth = PolySynth(q, max_voices=4, voice_factory=piano)
    audio = []
    for m in (60, 64, 67):
        q.push(note_event(NoteKind.ON, m))
    _drive(synth, 20, audio)
    for m in (72, 74, 76, 77, 79):
        q.push(note_event(NoteKind.ON, m))
        _drive(synth, 6, audio)
    a2 = np.concatenate(audio).astype(np.float64)
    steal_step = float(np.abs(np.diff(a2)).max())
    assert float(np.abs(a2).max()) <= 1.0, "steal caused a hard clip"

    # 5. Cost: PianoVoice vs sine, at the default block and at latency='low' ~95-frame.
    piano_383 = _measure_cost(piano, 383)
    sine_383 = _measure_cost(sine, 383)
    piano_95 = _measure_cost(piano, 95)
    deadline_95 = 95 / SR
    util_383 = piano_383 / BLOCK_PERIOD
    util_95 = piano_95 / deadline_95
    assert util_383 < 0.8, f"16 piano voices took {util_383*100:.0f}% of the 383-frame block"

    out_png = "claude/spikes/piano_voice_preview.png"
    _plot(piano_sig, sine_sig, held, f0, out_png)

    print(f"selftest OK: PianoVoice has {piano_partials} audible partials vs "
          f"{sine_partials} for the sine; held note decays "
          f"(early {early:.3f} -> late {late:.3f}).")
    print(f"  click-free fresh note; steal max step {steal_step:.4f} "
          f"(small -- quietest voice stolen); no clip in either.")
    print(f"  cost @16 voices: piano {piano_383*1e6:.0f} us/383-block "
          f"({util_383*100:.1f}%), sine {sine_383*1e6:.0f} us "
          f"({sine_383/BLOCK_PERIOD*100:.1f}%); "
          f"piano @95-frame {piano_95*1e6:.0f} us ({util_95*100:.1f}% of {deadline_95*1e3:.2f} ms).")
    print(f"  wrote {out_png}")


def _plot(piano_sig, sine_sig, held, f0, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

    for sig, color, label in ((sine_sig, "C1", "sine Voice"), (piano_sig, "C0", "PianoVoice")):
        w = np.hanning(len(sig))
        mag = np.abs(np.fft.rfft(sig * w))
        freqs = np.fft.rfftfreq(len(sig), 1.0 / SR)
        ax1.plot(freqs, mag, color=color, lw=0.9, label=label)
    ax1.set_title("timbre: PianoVoice has inharmonic overtones; the sine has one peak")
    ax1.set_xlabel("frequency (Hz)")
    ax1.set_ylabel("magnitude")
    ax1.set_xlim(0, 4000)
    ax1.legend(loc="upper right")

    peaks = np.array([np.abs(held[i:i + BLOCK_FRAMES]).max()
                      for i in range(0, len(held) - BLOCK_FRAMES, BLOCK_FRAMES)])
    t_ms = np.arange(len(peaks)) * BLOCK_FRAMES / SR
    ax2.plot(t_ms, peaks, color="C0")
    ax2.set_title("held note decays naturally (piano, not organ) — per-block peak")
    ax2.set_xlabel("time (s)")
    ax2.set_ylabel("peak amplitude")

    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# --- real playback ------------------------------------------------------------

def _play() -> None:
    import sounddevice as sd

    q = EventQueue()
    synth = PolySynth(q, voice_factory=PianoVoice)
    print("playing (rich PianoVoice): held C-major triad, then an overlapping arpeggio ...")
    with sd.OutputStream(samplerate=SR, channels=1, dtype="float32",
                         callback=synth.callback, latency="low"):
        for m in (60, 64, 67):
            q.push(note_event(NoteKind.ON, m))
        time.sleep(1.6)
        for m in (60, 64, 67):
            q.push(note_event(NoteKind.OFF, m))
        time.sleep(0.4)
        for m in (60, 64, 67, 72, 76, 79, 84):
            q.push(note_event(NoteKind.ON, m))
            time.sleep(0.22)
        time.sleep(1.2)
        for m in (60, 64, 67, 72, 76, 79, 84):
            q.push(note_event(NoteKind.OFF, m))
        time.sleep(0.5)
    if synth.status_flags:
        print(f"note: {synth.status_flags} callback status flags (possible underruns).")
    print("done.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless: richness/decay/click/cost asserts + PNG, no device")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        _play()


if __name__ == "__main__":
    main()
