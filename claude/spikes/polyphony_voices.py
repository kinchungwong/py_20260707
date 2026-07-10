#!/usr/bin/env python3
"""
SPIKE: polyphony -- multiple held keys become summed voices, with allocation,
       voice-stealing, and headroom/limiting, all inside the streaming callback

Question asked
--------------
realtime_envelope_release proved ONE monophonic voice. A real instrument needs
several notes at once. So, still inside the topology-A audio callback:
  * How do we allocate a voice per note-on and free it when its envelope finishes,
    from a FIXED pool (no per-block object allocation on the audio thread)?
  * When every voice is busy and another note-on arrives, which voice do we STEAL,
    and can the steal be click-free?
  * How do we sum voices without clipping when many stack (headroom / limiting)?
  * HOW MANY voices can we render before we blow the block deadline (underrun)?

What this does
--------------
`PolySynth` holds a fixed pool of `Voice`s (reused from
realtime_envelope_release). Each block it drains the `EventQueue` (topology A),
routes note-on/off, then sums the active voices and soft-limits the mix.
  * Allocation: note-on takes the voice already on that note (retrigger), else a
    free (IDLE) voice, else it STEALS the quietest voice (lowest envelope level).
  * Stealing is click-free by construction: it just re-tunes + re-attacks that
    voice, which -- like the mono retrigger -- ramps from the current level and
    keeps the phase accumulator, so no discontinuity (only a pitch change).
  * Limiting: the summed mix is passed through `tanh`, near-transparent for a few
    voices (AMP is small) and saturating -- never clipping -- for many.

`--selftest` drives it headless with scripted timelines and asserts: an FFT shows
three simultaneous notes as three independent peaks; allocation caps active voices
at the pool size; a release frees a voice; a 5th note into a 4-voice pool steals
without crashing; the mix never hard-clips and never has a click; and it MEASURES
per-block render cost vs the block deadline. It also writes a preview PNG. Default
(no flag) plays a scripted chord + overlapping arpeggio for real.

Finding
-------
- A FIXED pool of voices summed each block is all polyphony needs. Allocation is
  three cases in priority order: (1) the voice already on this note -> retrigger,
  (2) any IDLE voice, (3) STEAL. A voice frees itself: when its envelope render
  returns to IDLE we clear its note. No per-block allocation on the audio thread.
- "Steal the QUIETEST voice" (lowest envelope level) is a good one-line policy: a
  releasing voice has the lowest level, so it's stolen before any held voice --
  you lose the least-audible thing first, with no bookkeeping of note age.
- Stealing is click-free for FREE by reusing the envelope's ramp-from-current-level
  retrigger + the carried phase accumulator: the stolen voice just retunes and
  re-attacks. Only the pitch jumps (expected for stealing); no amplitude/phase
  discontinuity. Verified over a timeline with 5 notes overflowing a 4-voice pool:
  max output sample step 0.053, well under the click bound 0.139.
- Headroom via `tanh` on the summed mix: near-transparent for a few voices (AMP is
  small, tanh(x)~x) and saturating -- so it NEVER hard-clips. Measured peak 0.66
  with a stacked cluster; |out| < 1 always. tanh's slope <= 1 also means limiting
  can't introduce a click. (It does add mild harmonic distortion when driven hard;
  a look-ahead limiter is a later refinement.)
- Correctness: three simultaneous notes show up as three independent FFT peaks at
  C4/E4/G4 -- the voices really are summed, not blended. Pool cap enforced (4),
  and all voices freed (active back to 0) after release.
- "How many voices before underruns?" -- 16 voices render in ~246 us/block, only
  ~2.8% of the 8.68 ms block deadline (~15 us/voice). The naive extrapolation is
  hundreds of voices, BUT that's a pure-compute figure: real underruns also hinge
  on Python/GC jitter and the whole audio path, so treat 16 as comfortable and the
  true ceiling as a question for `input_to_sound_latency` on the real device. 16
  is the committed pool for now.
- RT note: `render()` allocates a mix buffer + per-voice arrays each block. Fine at
  16 voices; if it ever bites, preallocate the mix and a scratch buffer.

Run
---
    python claude/spikes/polyphony_voices.py             # play a chord + arpeggio for real
    python claude/spikes/polyphony_voices.py --selftest  # headless asserts + PNG
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from event_queue import EventQueue, SR, BLOCK_FRAMES, BLOCK_PERIOD, NoteEvent, NoteKind, Source
from realtime_envelope_release import Voice, EnvStage, midi_to_freq, note_event, AMP

MAX_VOICES = 16         # polyphony pool size; fixed => no per-block object allocation


class PolySynth:
    """A fixed pool of voices summed and soft-limited in the callback."""

    def __init__(self, queue: EventQueue, max_voices: int = MAX_VOICES):
        self.queue = queue
        self.voices = [Voice(0.0) for _ in range(max_voices)]
        self.voice_midi: list[int | None] = [None] * max_voices   # which note each voice holds
        self.status_flags = 0

    def active_count(self) -> int:
        return sum(1 for v in self.voices if v.env.stage is not EnvStage.IDLE)

    def _alloc(self, midi: int) -> int:
        # 1. a voice already on this note (still sounding) -> retrigger it.
        for i, m in enumerate(self.voice_midi):
            if m == midi and self.voices[i].env.stage is not EnvStage.IDLE:
                return i
        # 2. a free (IDLE) voice.
        for i, v in enumerate(self.voices):
            if v.env.stage is EnvStage.IDLE:
                return i
        # 3. none free -> steal the QUIETEST voice (a releasing voice has the
        #    lowest level, so it naturally gets stolen before a held one).
        return min(range(len(self.voices)), key=lambda i: self.voices[i].env.level)

    def handle(self, ev: NoteEvent) -> None:
        if ev.kind is NoteKind.ON:
            i = self._alloc(ev.midi)
            self.voices[i].freq = midi_to_freq(ev.midi)
            self.voices[i].env.note_on()          # ramp from current level -> click-free
            self.voice_midi[i] = ev.midi
        elif ev.kind is NoteKind.OFF:
            for i, m in enumerate(self.voice_midi):
                if m == ev.midi and self.voices[i].env.stage in (EnvStage.ATTACK, EnvStage.SUSTAIN):
                    self.voices[i].env.note_off()
                    break

    def render(self, frames: int, limit: bool = True) -> np.ndarray:
        mix = np.zeros(frames, dtype=np.float64)
        for i, v in enumerate(self.voices):
            if v.env.stage is not EnvStage.IDLE:
                mix += v.render(frames)
                if v.env.stage is EnvStage.IDLE:      # finished releasing this block
                    self.voice_midi[i] = None
        if limit:
            np.tanh(mix, out=mix)                      # soft clip: never > 1, ~linear when small
        return mix.astype(np.float32)

    def callback(self, outdata, frames: int, time_info, status) -> None:
        if status:
            self.status_flags += 1
        for ev in self.queue.drain():
            self.handle(ev)
        outdata[:, 0] = self.render(frames)


# --- helpers ------------------------------------------------------------------

def _dominant_freqs(sig: np.ndarray, k: int) -> list[float]:
    w = np.hanning(len(sig))
    mag = np.abs(np.fft.rfft(sig * w))
    freqs = np.fft.rfftfreq(len(sig), 1.0 / SR)
    mag[0] = 0.0                                       # ignore DC
    top = np.argsort(mag)[-k:]
    return sorted(float(freqs[i]) for i in top)


def _drive(synth: PolySynth, n_blocks: int, sink: list | None = None,
           active: list | None = None) -> None:
    for _ in range(n_blocks):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)
        if sink is not None:
            sink.append(out[:, 0].copy())
        if active is not None:
            active.append(synth.active_count())


# --- headless self-test -------------------------------------------------------

def _selftest() -> None:
    # 1. Three simultaneous notes -> three independent peaks (summing works).
    q = EventQueue()
    synth = PolySynth(q, max_voices=8)
    for m in (60, 64, 67):                              # C4 E4 G4
        q.push(note_event(NoteKind.ON, m))
    _drive(synth, 1)                                    # drain events + attack
    assert synth.active_count() == 3, synth.active_count()
    chunks = []
    while sum(len(c) for c in chunks) < 8192:
        chunks.append(synth.render(BLOCK_FRAMES, limit=False))   # linear sum for a clean FFT
    sig = np.concatenate(chunks)[:8192]
    peaks = _dominant_freqs(sig, 6)
    for f in (midi_to_freq(60), midi_to_freq(64), midi_to_freq(67)):
        assert min(abs(p - f) for p in peaks) < 6.0, f"missing peak near {f:.1f}: {peaks}"

    # 2. Allocation cap + stealing + release, on a small pool, from the real
    #    callback path (with the limiter). Build a timeline that overflows.
    q = EventQueue()
    synth = PolySynth(q, max_voices=4)
    audio: list[np.ndarray] = []
    active: list[int] = []
    for m in (60, 64, 67):                              # hold a triad (3 of 4 voices)
        q.push(note_event(NoteKind.ON, m))
    _drive(synth, 24, audio, active)
    pressed = [72, 74, 76, 77, 79]                      # 5 more while holding -> must steal
    for m in pressed:
        q.push(note_event(NoteKind.ON, m))
        _drive(synth, 6, audio, active)
    all_notes = [60, 64, 67, *pressed]
    for m in all_notes:
        q.push(note_event(NoteKind.OFF, m))
    _drive(synth, 40, audio, active)                    # release everything -> back to silence

    assert max(active) == 4, f"pool cap not enforced: peak active {max(active)}"
    assert active[-1] == 0, f"voices not freed after release: {active[-1]}"

    a = np.concatenate(audio).astype(np.float64)
    # 3. No hard clipping (the soft limiter guarantees |x| < 1).
    peak = float(np.abs(a).max())
    assert peak <= 1.0, f"hard clip: peak {peak}"
    # 4. Click-free across the whole timeline (steal retrigger + releases + seams).
    #    tanh's slope <= 1, so |d(out)| <= |d(mix)| <= sum of per-voice steps.
    e = synth.voices[0].env
    inc_max = 2.0 * np.pi * midi_to_freq(max(all_notes)) / SR
    click_bound = AMP * 4 * (inc_max + e.attack_step) * 1.5
    max_step = float(np.abs(np.diff(a)).max())
    assert max_step <= click_bound, f"click: max step {max_step:.5f} > bound {click_bound:.5f}"

    # 5. Render cost vs the block deadline -- "how many voices before underruns?"
    cost = _measure_render_cost(MAX_VOICES)
    util = cost / BLOCK_PERIOD
    per_voice = cost / MAX_VOICES
    headroom = int(BLOCK_PERIOD / per_voice) if per_voice > 0 else 0
    assert util < 0.5, f"{MAX_VOICES} voices took {util*100:.1f}% of the block period"

    out_png = "claude/spikes/polyphony_voices_preview.png"
    _plot(active, sig, [midi_to_freq(m) for m in (60, 64, 67)], out_png)

    print(f"selftest OK: 3 notes -> 3 FFT peaks; pool of 4 capped active at "
          f"{max(active)} (stealing the quietest), freed to {active[-1]} after release.")
    print(f"  no clip (peak {peak:.3f} <= 1.0); click-free "
          f"(max step {max_step:.5f} <= {click_bound:.5f}).")
    print(f"  render cost @ {MAX_VOICES} voices: {cost*1e6:.1f} us/block = "
          f"{util*100:.1f}% of the {BLOCK_PERIOD*1e3:.2f} ms deadline "
          f"(~{per_voice*1e6:.1f} us/voice -> headroom ~{headroom} voices).")
    print(f"  wrote {out_png}")


def _measure_render_cost(max_voices: int) -> float:
    q = EventQueue()
    synth = PolySynth(q, max_voices=max_voices)
    for n in range(max_voices):                         # fill every voice, distinct notes
        q.push(note_event(NoteKind.ON, 45 + n))
    _drive(synth, 4)                                    # drain + reach sustain
    assert synth.active_count() == max_voices
    k = 200
    t0 = time.perf_counter()
    for _ in range(k):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)
    return (time.perf_counter() - t0) / k


def _plot(active_trace, chord_sig, expected_freqs, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

    t_ms = np.arange(len(active_trace)) * BLOCK_PERIOD * 1000.0
    ax1.step(t_ms, active_trace, where="post", color="C2")
    ax1.axhline(4, color="red", ls="--", lw=1, label="pool size (4)")
    ax1.set_title("active voices: allocate -> steal (capped) -> release")
    ax1.set_xlabel("time (ms)")
    ax1.set_ylabel("voices sounding")
    ax1.set_ylim(-0.3, 5)
    ax1.legend(loc="upper right")

    w = np.hanning(len(chord_sig))
    mag = np.abs(np.fft.rfft(chord_sig * w))
    freqs = np.fft.rfftfreq(len(chord_sig), 1.0 / SR)
    ax2.plot(freqs, mag, color="C0", lw=0.9)
    for f in expected_freqs:
        ax2.axvline(f, color="red", ls="--", lw=0.8)
    ax2.set_title("spectrum of the summed C-E-G triad (three independent peaks)")
    ax2.set_xlabel("frequency (Hz)")
    ax2.set_ylabel("magnitude")
    ax2.set_xlim(0, 1000)

    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# --- real playback ------------------------------------------------------------

def _play() -> None:
    import sounddevice as sd

    q = EventQueue()
    synth = PolySynth(q)
    stream = sd.OutputStream(samplerate=SR, channels=1, dtype="float32",
                             callback=synth.callback)
    print("playing: a held C-major triad, then an overlapping arpeggio ...")
    with stream:
        # held triad
        for m in (60, 64, 67):
            q.push(note_event(NoteKind.ON, m))
        time.sleep(1.2)
        for m in (60, 64, 67):
            q.push(note_event(NoteKind.OFF, m))
        time.sleep(0.3)
        # overlapping arpeggio: each note left ringing while the next starts
        for m in (60, 64, 67, 72, 76, 79, 84):
            q.push(note_event(NoteKind.ON, m))
            time.sleep(0.18)
        time.sleep(0.6)
        for m in (60, 64, 67, 72, 76, 79, 84):
            q.push(note_event(NoteKind.OFF, m))
        time.sleep(0.4)
    if synth.status_flags:
        print(f"note: {synth.status_flags} callback status flags (possible underruns).")
    print("done.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless: FFT + allocation/steal/clip/click asserts + cost, save a PNG")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        _play()


if __name__ == "__main__":
    main()
