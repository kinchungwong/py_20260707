#!/usr/bin/env python3
"""
SPIKE: real-time gate envelope -- sustain while a key is held, click-free release
       on key-up, computed per-block in a streaming audio callback

Question asked
--------------
The FIRST spike that makes sound from the interactive path. The batch synth
(piano_chord_major_minor) rendered a FIXED 1 s buffer with a built-in envelope.
An instrument can't do that: a note must start when a key goes down, sustain for
*however long* it's held, and stop when the key comes up -- and the note-on/off
arrive asynchronously, mid-stream, via the topology-A EventQueue. So:
  * Can we run an attack/sustain/release envelope PER BLOCK inside the streaming
    callback, carrying state across ~383-frame blocks and crossing stage
    boundaries that fall in the middle of a block?
  * Is the release CLICK-FREE when the key-up lands at an arbitrary sample -- i.e.
    does the release ramp from the CURRENT level (wherever the envelope is) down
    to zero, never jumping?
  * Does the phase-continuous oscillator (from outputstream_callback) stay
    click-free across block seams while the envelope modulates it?

Scope (deliberately narrow): ONE monophonic voice, last-note priority; a pure
sine so the envelope is what's under test. NOT in scope, deferred by the plan:
polyphony / voice allocation / stealing (-> polyphony_voices), the rich
inharmonic-partial timbre + per-partial decay (-> the synth-module task; it's a
drop-in multiply on the oscillator here), and sample-accurate event placement
within a block (-> input_to_sound_latency). Events apply at block start, so onset
jitter is <= one block (~8.7 ms), the bound already established by event_queue.

What this does
--------------
Reuses the real committed path: a producer pushes `NoteEvent`s onto the
`EventQueue`; the audio callback drains it non-blocking each block (topology A),
applies note-on/off to the single `Voice`, and renders `frames` samples of
`sine x envelope`. The `Envelope` is a small state machine
IDLE -> ATTACK -> SUSTAIN -> RELEASE -> IDLE; note-off starts the release from the
current level (click-free); note-on re-attacks from the current level (click-free
retrigger). ~6 ms attack, ~20 ms release (the anti-click times from the recipe).

`--selftest` drives the callback deterministically with a scripted timeline
(silence -> note-on -> hold -> note-off -> release), asserts the envelope shape and
that neither the envelope nor the audio has a discontinuity, and writes a preview
PNG. Default (no flag) plays a scripted C-E-G-C for real through the audio device.

Finding
-------
- YES to a per-block ASR state machine. Carrying just `(stage, level)` across
  blocks and letting `render()` split a block into per-stage segments handles a
  stage boundary landing anywhere inside a ~383-frame block. IDLE renders exact
  silence (audio literally 0.0), SUSTAIN a flat 1.0, ATTACK/RELEASE linear ramps.
- Click-free release is about ramping from the CURRENT level, not from 1.0. With
  a 6 ms attack / 20 ms release: the max envelope sample-to-sample step was
  0.00377 (= one attack step, 1/265) -- i.e. the envelope has NO jump, just its
  ramp slope. The max AUDIO step was 0.00745, which is exactly AMP*(2*pi*f/SR),
  the sine's OWN slope at full sustain -- so neither the envelope nor the block
  seams inject any discontinuity. (A per-block phase reset would have spiked this
  to ~2*AMP = 0.4; a hard note-off gate to ~AMP*level. Neither happened.)
- Phase continuity across block seams comes for free from carrying a phase
  accumulator (the outputstream_callback lesson); the audio-step bound above is
  measured across ALL seams, so it doubles as the seam-continuity proof.
- Monophonic last-note priority is enough to exercise the envelope: note-on
  retriggers by re-attacking from the current level (click-free even mid-release);
  note-off releases only if it matches the active note (an older held key's
  note-off is ignored). Real voice allocation/stealing is the next spike.
- Events apply at the top of the block (right after the non-blocking drain), so
  onset/release jitter is <= one block (~8.7 ms) -- the bound event_queue already
  established. Sample-accurate placement within a block is possible (the callback
  gets a DAC-time arg) but deferred to input_to_sound_latency.
- This is the first spike where the topology-A EventQueue actually feeds sound:
  the callback drains it each block and renders -- validated in situ, no surprises.
- Piano realism is a clean layering step, NOT redone here: replace the flat
  SUSTAIN with the recipe's per-partial exponential decay and swap the sine for
  the inharmonic-partial stack -- both multiply onto this same envelope/voice.
  That convergence belongs with the "promote synth_note to a module" task.
- RT note: `render()` allocates a few small NumPy arrays per block (empty/arange/
  sin). Fine at this scale; if it ever shows up, preallocate a scratch buffer
  sized to the max block and write in place.

Run
---
    python claude/spikes/realtime_envelope_release.py             # play C-E-G-C for real
    python claude/spikes/realtime_envelope_release.py --selftest  # headless asserts + PNG
"""

from __future__ import annotations

import argparse
import time
from enum import Enum

import numpy as np

# Reuse the committed topology-A queue and the canonical event vocabulary.
from event_queue import EventQueue, SR, BLOCK_FRAMES, NoteEvent, NoteKind, Source

TWO_PI = 2.0 * np.pi
AMP = 0.2               # gentle output level
ATTACK_MS = 6.0         # linear attack ramp (anti-click, from the synth recipe)
RELEASE_MS = 20.0       # linear release fade (anti-click, from the synth recipe)


def midi_to_freq(midi: int) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def note_event(kind: NoteKind, midi: int) -> NoteEvent:
    return NoteEvent(kind, midi, Source.KEYBOARD, time.perf_counter())


class EnvStage(Enum):
    IDLE = "idle"
    ATTACK = "attack"
    SUSTAIN = "sustain"
    RELEASE = "release"


class Envelope:
    """Linear attack/sustain/release GATE envelope, advanced per block.

    Key property: both transitions ramp from the CURRENT level, so an event
    landing at any sample never produces a jump:
      * note_off -> RELEASE from the current level down to 0 over ~RELEASE_MS.
      * note_on  -> ATTACK from the current level up to 1 (click-free retrigger).
    render() may cross a stage boundary in the middle of a block; it processes the
    block in per-stage segments until `frames` samples are produced.
    """

    def __init__(self):
        self.stage = EnvStage.IDLE
        self.level = 0.0
        self.attack_samples = max(1, round(ATTACK_MS / 1000.0 * SR))
        self.release_samples = max(1, round(RELEASE_MS / 1000.0 * SR))
        self.attack_step = 1.0 / self.attack_samples      # gain per sample, ramping up
        self.release_step = 1.0 / self.release_samples    # placeholder; set on note_off

    def note_on(self) -> None:
        self.stage = EnvStage.ATTACK          # from current level -> click-free retrigger

    def note_off(self) -> None:
        if self.stage in (EnvStage.ATTACK, EnvStage.SUSTAIN):
            if self.level <= 0.0:
                self.stage = EnvStage.IDLE
            else:
                # Ramp from the current level to 0 over release_samples, so the
                # release always spans ~RELEASE_MS regardless of where it starts.
                self.release_step = self.level / self.release_samples
                self.stage = EnvStage.RELEASE

    def render(self, frames: int) -> np.ndarray:
        gain = np.empty(frames, dtype=np.float64)
        pos = 0
        while pos < frames:
            if self.stage is EnvStage.IDLE:
                gain[pos:] = 0.0
                self.level = 0.0
                pos = frames
            elif self.stage is EnvStage.SUSTAIN:
                gain[pos:] = 1.0
                self.level = 1.0
                pos = frames
            elif self.stage is EnvStage.ATTACK:
                step = self.attack_step
                n_to_full = max(1, int(np.ceil((1.0 - self.level) / step)))
                seg = min(frames - pos, n_to_full)
                ramp = self.level + step * np.arange(1, seg + 1)
                np.clip(ramp, 0.0, 1.0, out=ramp)
                gain[pos:pos + seg] = ramp
                self.level = float(ramp[-1])
                pos += seg
                if self.level >= 1.0 - 1e-12:
                    self.level = 1.0
                    self.stage = EnvStage.SUSTAIN
            else:  # RELEASE
                step = self.release_step
                n_to_zero = max(1, int(np.ceil(self.level / step)))
                seg = min(frames - pos, n_to_zero)
                ramp = self.level - step * np.arange(1, seg + 1)
                np.clip(ramp, 0.0, None, out=ramp)
                gain[pos:pos + seg] = ramp
                self.level = float(ramp[-1])
                pos += seg
                if self.level <= 1e-12:
                    self.level = 0.0
                    self.stage = EnvStage.IDLE
        return gain


class Voice:
    """A phase-continuous sine oscillator times its Envelope. Phase accumulates
    across blocks (from the outputstream_callback lesson) so there is no seam
    click; retuning `freq` mid-note just changes the increment, not the phase."""

    def __init__(self, freq: float = 0.0):
        self.freq = freq
        self.phase = 0.0
        self.env = Envelope()
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
        inc = TWO_PI * self.freq / SR
        phases = self.phase + inc * np.arange(1, frames + 1)
        wave = np.sin(phases)
        self.phase = float(phases[-1] % TWO_PI)
        gain = self.env.render(frames)
        self.last_gain = gain
        return (AMP * wave * gain).astype(np.float32)


class MonoSynth:
    """One voice, last-note priority. Drains the EventQueue at the top of every
    block (topology A: the audio callback owns the drain) and turns note-on/off
    into envelope gate + retune. A note-off for a note that isn't the active one
    (an older held key, under monophonic priority) is ignored -- true polyphony
    is the next spike."""

    def __init__(self, queue: EventQueue):
        self.queue = queue
        self.voice = Voice(0.0)
        self.active_midi: int | None = None
        self.status_flags = 0        # count of non-empty callback status (underruns etc.)

    def handle(self, ev: NoteEvent) -> None:
        if ev.kind is NoteKind.ON:
            self.active_midi = ev.midi
            self.voice.freq = midi_to_freq(ev.midi)
            self.voice.env.note_on()
        elif ev.kind is NoteKind.OFF:
            if ev.midi == self.active_midi:
                self.voice.env.note_off()
                self.active_midi = None

    def callback(self, outdata, frames: int, time_info, status) -> None:
        if status:
            self.status_flags += 1
        for ev in self.queue.drain():       # non-blocking drain, proven cheap
            self.handle(ev)
        outdata[:, 0] = self.voice.render(frames)


# --- headless self-test: drive the callback with a scripted timeline ----------

def _selftest() -> None:
    q = EventQueue()
    synth = MonoSynth(q)
    frames = BLOCK_FRAMES
    n_pre, n_hold, n_rel = 2, 40, 6     # blocks: silence, held (~350 ms), release (~52 ms)
    blocks: list[tuple[np.ndarray, np.ndarray]] = []

    def step(n: int) -> None:
        for _ in range(n):
            out = np.zeros((frames, 1), dtype=np.float32)
            synth.callback(out, frames, None, None)
            blocks.append((out[:, 0].copy(), synth.voice.last_gain.copy()))

    step(n_pre)                              # IDLE -> exact silence
    q.push(note_event(NoteKind.ON, 60))      # C4
    step(n_hold)                             # ATTACK -> SUSTAIN
    q.push(note_event(NoteKind.OFF, 60))
    step(n_rel)                              # RELEASE -> IDLE

    audio = np.concatenate([b[0] for b in blocks]).astype(np.float64)
    env = np.concatenate([b[1] for b in blocks])

    e = synth.voice.env
    pre_end = n_pre * frames
    off_idx = pre_end + n_hold * frames

    # 1. IDLE is exactly silent (no idle hum, no stray phase).
    assert np.all(env[:pre_end] == 0.0), "idle envelope not zero"
    assert np.all(audio[:pre_end] == 0.0), "idle audio not silent"

    # 2. Attack rises from ~0, monotonically, to full.
    assert env[pre_end] < 0.02, f"onset not near zero: {env[pre_end]}"
    attack = env[pre_end:pre_end + e.attack_samples + 2]
    assert np.all(np.diff(attack) >= -1e-12), "attack not monotonic non-decreasing"
    assert env[:off_idx].max() >= 0.999, "attack never reached full level"

    # 3. Sustain is a flat plateau at exactly 1.0 while held.
    plateau = env[pre_end + e.attack_samples + 5:off_idx]
    assert plateau.min() == 1.0 and plateau.max() == 1.0, "sustain not flat at 1.0"

    # 4. Release ramps down monotonically, reaches 0 within release_samples, stays 0.
    release = env[off_idx:off_idx + e.release_samples + 2]
    assert np.all(np.diff(release) <= 1e-12), "release not monotonic non-increasing"
    assert np.all(env[off_idx + e.release_samples + 5:] == 0.0), "not silent after release"

    # 5. Click-free (envelope): no jump larger than a single ramp step.
    max_env_step = float(np.abs(np.diff(env)).max())
    assert max_env_step <= e.attack_step * 1.001, \
        f"envelope discontinuity: {max_env_step} > step {e.attack_step}"

    # 6. Click-free (audio): no sample-to-sample jump beyond the tone's own slope
    #    plus one envelope step. This also proves phase continuity across block
    #    seams -- a per-block phase reset would spike this to ~2*AMP.
    inc = TWO_PI * midi_to_freq(60) / SR
    audio_bound = AMP * (inc + e.attack_step) * 1.5
    max_audio_step = float(np.abs(np.diff(audio)).max())
    assert max_audio_step <= audio_bound, \
        f"audio discontinuity: {max_audio_step} > bound {audio_bound}"

    out_png = "claude/spikes/realtime_envelope_release_preview.png"
    _plot(audio, env, pre_end, off_idx, e.release_samples, out_png)

    print(f"selftest OK: attack {ATTACK_MS:.0f} ms -> sustain (flat 1.0) -> release "
          f"{RELEASE_MS:.0f} ms, then exact silence.")
    print(f"  click-free: max envelope step={max_env_step:.5f} (<= {e.attack_step:.5f}); "
          f"max audio step={max_audio_step:.5f} (<= bound {audio_bound:.5f}).")
    print(f"  wrote {out_png}")


def _plot(audio, env, pre_end, off_idx, release_samples, path) -> None:
    import matplotlib
    matplotlib.use("Agg")                    # headless: must precede pyplot import
    import matplotlib.pyplot as plt

    t_ms = np.arange(len(audio)) / SR * 1000.0
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

    ax1.plot(t_ms, env, color="C1", lw=1.2)
    ax1.axvline(pre_end / SR * 1000.0, color="green", ls="--", lw=1, label="note-on")
    ax1.axvline(off_idx / SR * 1000.0, color="red", ls="--", lw=1, label="note-off")
    ax1.set_title("gate envelope: attack -> sustain -> release")
    ax1.set_ylabel("gain")
    ax1.set_ylim(-0.05, 1.05)
    ax1.legend(loc="upper right")

    lo = max(0, off_idx - 120)
    hi = min(len(audio), off_idx + release_samples + 120)
    ax2.plot(t_ms[lo:hi], audio[lo:hi], color="C0", lw=0.8)
    ax2.axvline(off_idx / SR * 1000.0, color="red", ls="--", lw=1, label="note-off")
    ax2.set_title("audio around note-off (smooth, click-free release)")
    ax2.set_xlabel("time (ms)")
    ax2.set_ylabel("amplitude")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# --- real playback: scripted note timeline through the audio device -----------

def _play() -> None:
    import sounddevice as sd

    q = EventQueue()
    synth = MonoSynth(q)
    stream = sd.OutputStream(samplerate=SR, channels=1, dtype="float32",
                             callback=synth.callback)
    melody = [60, 64, 67, 72]                # C4 E4 G4 C5
    print("playing scripted C-E-G-C, each held ~0.6 s "
          "(attack -> sustain -> click-free release) ...")
    with stream:
        for m in melody:
            q.push(note_event(NoteKind.ON, m))
            time.sleep(0.6)
            q.push(note_event(NoteKind.OFF, m))
            time.sleep(0.25)
        time.sleep(0.1)                      # let the final release finish audibly
    if synth.status_flags:
        print(f"note: {synth.status_flags} callback status flags (possible underruns).")
    print("done.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless: scripted timeline + envelope/click-free asserts, save a PNG")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        _play()


if __name__ == "__main__":
    main()
