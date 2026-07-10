"""Voice assertions, ported from the realtime_envelope_release and piano_voice
spike _selftests.

Covered:
  * SineVoice  -- IDLE-exact-silence, the AMP-MOVE (pure timbre peaks ~1.0 with NO
    master AMP baked in), exactly one FFT partial, and click-free/phase-continuous
    audio when driven through PolySynth (whose mix stage re-applies AMP).
  * PianoVoice -- inharmonic richness (>=4 partials), natural per-partial decay of a
    held note, click-free fresh onset with no clip, and no hard clip under stealing.
  * A machine-dependent 16-voice render-cost check (marked ``perf``).

Both voices are driven exactly like the spikes (piano_voice._render_one / _drive):
through a PolySynth so AMP + the tanh limiter are in the path. Because of THE
AMP-MOVE the voices render pure timbre (no AMP); AMP is re-applied once at the
PolySynth mix stage, so ``sum(AMP*x_i) == AMP*sum(x_i)`` and the audio is identical.

RNG note: PianoVoice's per-partial phases are UNSEEDED, so every assertion is
phase-independent (FFT magnitudes, per-block peak decay, |out| bounds) -- never an
exact sample value.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from pypiano_2607 import (
    SineVoice, PianoVoice, PolySynth, EventQueue, NoteEvent, NoteKind, Source,
    midi_to_freq,
)
from pypiano_2607.config import (
    SR, BLOCK_FRAMES, BLOCK_PERIOD, AMP, TWO_PI, N_PARTIALS, INHARMONICITY,
)


# --- local helpers (mirroring the spikes' _drive / _render_one / _harmonic_strengths) ---

def _on(midi: int) -> NoteEvent:
    """CONVENTION: MIDI number IS the sounder_id; ON carries freq=midi_to_freq(midi)."""
    return NoteEvent(NoteKind.ON, midi, midi_to_freq(midi), Source.KEYBOARD, time.perf_counter())


def _off(midi: int) -> NoteEvent:
    """OFF: same sounder_id, freq=None (never passed to a voice)."""
    return NoteEvent(NoteKind.OFF, midi, None, Source.KEYBOARD, time.perf_counter())


def _drive(synth: PolySynth, n: int, sink: list | None = None) -> None:
    """Run n headless callback blocks, optionally collecting channel-0 output."""
    for _ in range(n):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)
        if sink is not None:
            sink.append(out[:, 0].copy())


def _render_one_linear(voice_factory, midi: int, n_samples: int) -> np.ndarray:
    """A single sustained voice's LINEAR output (AMP*sum, limit=False -> no tanh),
    the clean-FFT path from the AMP-MOVE note; like piano_voice._render_one but
    taking the un-limited mix so the FFT is undistorted."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=1, voice_factory=voice_factory)
    q.push(_on(midi))
    for ev in q.drain():                    # apply the queued note-on
        synth.handle(ev)
    chunks = []
    total = 0
    while total < n_samples:
        chunks.append(synth.render(BLOCK_FRAMES, limit=False))
        total += BLOCK_FRAMES
    return np.concatenate(chunks)[:n_samples].astype(np.float64)


def _harmonic_strengths(sig: np.ndarray, f0: float) -> np.ndarray:
    """Magnitude at each inharmonic partial frequency, normalized to the fundamental."""
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


def _measure_cost(voice_factory, frames: int, max_voices: int = 16, k: int = 200) -> float:
    """Mean seconds per callback with `max_voices` voices sounding (piano_voice._measure_cost)."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=max_voices, voice_factory=voice_factory)
    for n in range(max_voices):
        q.push(_on(45 + n))
    for _ in range(4):                      # warm up + drain the note-ons
        out = np.zeros((frames, 1), dtype=np.float32)
        synth.callback(out, frames, None, None)
    assert synth.active_count() == max_voices
    t0 = time.perf_counter()
    for _ in range(k):
        out = np.zeros((frames, 1), dtype=np.float32)
        synth.callback(out, frames, None, None)
    return (time.perf_counter() - t0) / k


# --- SineVoice ----------------------------------------------------------------

def test_sinevoice_idle_is_exact_silence():
    """A never-triggered SineVoice renders literal 0.0 (IDLE gate => exact zero)."""
    v = SineVoice(midi_to_freq(60))
    a = np.concatenate([v.render(BLOCK_FRAMES) for _ in range(3)])
    assert np.all(a == 0.0), "idle voice not exactly silent"


def test_sinevoice_amp_move_pure_timbre_peaks_near_one():
    """THE AMP-MOVE: the voice renders pure timbre WITHOUT the master AMP, so a
    sustained sine peaks near 1.0 (the spike voice would have peaked near AMP=0.2)."""
    v = SineVoice()
    v.note_on(midi_to_freq(60))
    for _ in range(40):                     # attack -> flat sustain
        a = v.render(BLOCK_FRAMES)
    peak = float(np.abs(a).max())
    assert 0.98 <= peak <= 1.0, f"sustained pure-timbre sine should peak ~1.0, got {peak}"


def test_sinevoice_single_fft_partial():
    """A SineVoice has exactly ONE audible partial (the fundamental)."""
    f0 = midi_to_freq(60)
    sig = _render_one_linear(SineVoice, 60, 16384)
    hs = _harmonic_strengths(sig, f0)
    sine_partials = int(np.sum(hs >= 0.1))
    assert sine_partials == 1, f"sine voice should be one partial: {sine_partials}"


def test_sinevoice_click_free_through_polysynth():
    """Driven through PolySynth (IDLE -> attack -> sustain -> release), the output is
    exactly silent while IDLE, never clips, and has no sample-to-sample jump beyond
    the tone's own slope + one envelope step. AMP is re-applied at the mix, so the
    bound carries AMP (matching the spike); tanh only ever shrinks a step."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=1, voice_factory=SineVoice)
    audio: list[np.ndarray] = []

    _drive(synth, 2, audio)                 # IDLE -> exact silence
    pre_end = 2 * BLOCK_FRAMES
    q.push(_on(60))
    _drive(synth, 40, audio)                # ATTACK -> SUSTAIN
    q.push(_off(60))
    _drive(synth, 6, audio)                 # RELEASE -> IDLE
    a = np.concatenate(audio).astype(np.float64)

    assert np.all(a[:pre_end] == 0.0), "idle audio not silent"
    assert float(np.abs(a).max()) <= 1.0, "sine output clipped"

    env = synth.voices[0].env
    inc = TWO_PI * midi_to_freq(60) / SR
    audio_bound = AMP * (inc + env.attack_step) * 1.5
    max_step = float(np.abs(np.diff(a)).max())
    assert max_step <= audio_bound, f"audio discontinuity: {max_step} > bound {audio_bound}"


# --- PianoVoice ---------------------------------------------------------------

def test_pianovoice_is_richer_than_sine():
    """A PianoVoice has >=4 audible partials (>=10% of the fundamental, incl. 2nd/3rd)
    vs exactly one for the sine."""
    f0 = midi_to_freq(60)
    piano_sig = _render_one_linear(PianoVoice, 60, 16384)
    sine_sig = _render_one_linear(SineVoice, 60, 16384)
    hp = _harmonic_strengths(piano_sig, f0)
    hs = _harmonic_strengths(sine_sig, f0)
    piano_partials = int(np.sum(hp >= 0.1))
    sine_partials = int(np.sum(hs >= 0.1))
    assert piano_partials >= 4, f"piano voice not rich: {piano_partials} partials"
    assert sine_partials == 1, f"sine voice should be one partial: {sine_partials}"
    assert hp[1] >= 0.1 and hp[2] >= 0.1, "missing 2nd/3rd partials"


def test_pianovoice_held_note_decays():
    """A HELD PianoVoice gets quieter over time (piano, not organ): the late-block
    peak is well below the early-block peak."""
    held = _render_one_linear(PianoVoice, 60, int(1.5 * SR))
    early = float(np.abs(held[:BLOCK_FRAMES]).max())
    late = float(np.abs(held[-BLOCK_FRAMES:]).max())
    assert late < 0.6 * early, f"held note did not decay: early {early:.3f} late {late:.3f}"


def test_pianovoice_fresh_note_click_free_no_clip():
    """A fresh PianoVoice note (gated from 0, released to 0) does not clip and has no
    jump beyond the partial-sum slope + one envelope step (AMP applied at the mix)."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=4, voice_factory=PianoVoice)
    audio: list[np.ndarray] = []
    q.push(_on(60))
    _drive(synth, 24, audio)
    q.push(_off(60))
    _drive(synth, 40, audio)
    a1 = np.concatenate(audio).astype(np.float64)

    assert float(np.abs(a1).max()) <= 1.0, "fresh note clipped"
    v = synth.voices[0]
    slope = AMP * float(np.sum(np.abs(v._amps) * np.abs(v._incs)))
    bound = (slope + AMP * v.env.attack_step) * 1.5 + 1e-6
    assert float(np.abs(np.diff(a1)).max()) <= bound, "fresh piano note has a click"


def test_pianovoice_steal_no_clip():
    """Overflowing the pool steals the quietest voice; the phase re-init on a steal
    is a small artifact, never a hard clip (|out| <= 1)."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=4, voice_factory=PianoVoice)
    audio: list[np.ndarray] = []
    for m in (60, 64, 67):
        q.push(_on(m))
    _drive(synth, 20, audio)
    for m in (72, 74, 76, 77, 79):
        q.push(_on(m))
        _drive(synth, 6, audio)
    a2 = np.concatenate(audio).astype(np.float64)
    assert float(np.abs(a2).max()) <= 1.0, "steal caused a hard clip"


@pytest.mark.perf
def test_pianovoice_16_voice_render_cost():
    """Machine-dependent: 16 PianoVoices render well within the 383-frame deadline."""
    piano_383 = _measure_cost(PianoVoice, 383)
    util_383 = piano_383 / BLOCK_PERIOD
    assert util_383 < 0.8, f"16 piano voices took {util_383 * 100:.0f}% of the 383-frame block"
