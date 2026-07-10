"""PolySynth assertions, ported from the polyphony_voices spike _selftest: FFT
summing, allocation cap + voice-stealing + release-freeing, no-clip, click-free,
and the tanh soft-limiter under a stacked cluster. Plus sounder_id-keyed semantics
(the MIDI->sounder_id rename) and the AMP-MOVE (master gain applied ONCE at the
mix stage). The render-cost test is @perf."""

from __future__ import annotations

import time

import numpy as np
import pytest

from pypiano_2607 import (
    PolySynth, SineVoice, EventQueue, NoteEvent, NoteKind, Source, EnvStage,
    midi_to_freq,
)
from pypiano_2607.config import SR, BLOCK_FRAMES, BLOCK_PERIOD, AMP, MAX_VOICES


def _on(midi):
    return NoteEvent(NoteKind.ON, midi, midi_to_freq(midi), Source.KEYBOARD, time.perf_counter())


def _off(midi):
    return NoteEvent(NoteKind.OFF, midi, None, Source.KEYBOARD, time.perf_counter())


def _dominant_freqs(sig, k):
    w = np.hanning(len(sig))
    mag = np.abs(np.fft.rfft(sig * w))
    freqs = np.fft.rfftfreq(len(sig), 1.0 / SR)
    mag[0] = 0.0
    top = np.argsort(mag)[-k:]
    return sorted(float(freqs[i]) for i in top)


def _drive(synth, n_blocks, sink=None, active=None):
    for _ in range(n_blocks):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)
        if sink is not None:
            sink.append(out[:, 0].copy())
        if active is not None:
            active.append(synth.active_count())


def test_three_notes_three_peaks():
    q = EventQueue()
    synth = PolySynth(q, max_voices=8)
    for m in (60, 64, 67):
        q.push(_on(m))
    _drive(synth, 1)
    assert synth.active_count() == 3
    chunks = []
    while sum(len(c) for c in chunks) < 8192:
        chunks.append(synth.render(BLOCK_FRAMES, limit=False))
    sig = np.concatenate(chunks)[:8192]
    peaks = _dominant_freqs(sig, 6)
    for f in (midi_to_freq(60), midi_to_freq(64), midi_to_freq(67)):
        assert min(abs(p - f) for p in peaks) < 6.0, f"missing peak near {f:.1f}: {peaks}"


def test_alloc_cap_steal_release_no_clip_click_free():
    q = EventQueue()
    synth = PolySynth(q, max_voices=4)
    audio, active = [], []
    for m in (60, 64, 67):
        q.push(_on(m))
    _drive(synth, 24, audio, active)
    pressed = [72, 74, 76, 77, 79]
    for m in pressed:
        q.push(_on(m))
        _drive(synth, 6, audio, active)
    all_notes = [60, 64, 67, *pressed]
    for m in all_notes:
        q.push(_off(m))
    _drive(synth, 40, audio, active)

    assert max(active) == 4, f"pool cap not enforced: peak active {max(active)}"
    assert active[-1] == 0, f"voices not freed after release: {active[-1]}"

    a = np.concatenate(audio).astype(np.float64)
    peak = float(np.abs(a).max())
    assert peak <= 1.0, f"hard clip: peak {peak}"

    e = synth.voices[0].env
    inc_max = 2.0 * np.pi * midi_to_freq(max(all_notes)) / SR
    click_bound = AMP * 4 * (inc_max + e.attack_step) * 1.5
    max_step = float(np.abs(np.diff(a)).max())
    assert max_step <= click_bound, f"click: max step {max_step:.5f} > bound {click_bound:.5f}"


def _sustained_cluster(n_voices):
    """A SineVoice PolySynth with n_voices distinct notes driven to sustain.
    SineVoice has no RNG, so two clusters built this way are bit-identical --
    letting us compare the limited and un-limited render of the SAME state."""
    q = EventQueue()
    synth = PolySynth(q, max_voices=n_voices)
    for m in range(48, 48 + n_voices):        # a dense chromatic stack
        q.push(_on(m))
    _drive(synth, 30)                         # drain + reach flat sustain
    assert synth.active_count() == n_voices
    return synth


def test_tanh_limits_stacked_cluster():
    # A full 16-voice cluster sums to a linear mix that OVERDRIVES (> 1.0); the
    # tanh soft-limiter must keep the callback output within [-1, 1] with no hard
    # clip, and it IS exactly that limiter: out == tanh(linear mix).
    n = MAX_VOICES
    lin = _sustained_cluster(n).render(BLOCK_FRAMES, limit=False).astype(np.float64)
    lim = _sustained_cluster(n).render(BLOCK_FRAMES, limit=True).astype(np.float64)

    assert float(np.abs(lin).max()) > 1.0, "cluster did not overdrive -> nothing to limit"
    assert float(np.abs(lim).max()) <= 1.0, "tanh limiter let the mix hard-clip"
    # the two clusters are identical state (no RNG), so the limited output is
    # exactly the tanh of the linear mix (float32 rounding aside).
    assert np.allclose(lim, np.tanh(lin), atol=1e-5), "limiter is not tanh(mix)"


def test_same_sounder_id_retriggers_one_voice():
    # Two ONs with the SAME sounder_id must reuse the SAME voice slot (retrigger),
    # not allocate a second -> only one active voice.
    q = EventQueue()
    synth = PolySynth(q, max_voices=8)
    q.push(_on(60))
    _drive(synth, 2)
    assert synth.active_count() == 1
    q.push(_on(60))            # same sounder_id -> retrigger, still one voice
    _drive(synth, 2)
    assert synth.active_count() == 1


def test_note_off_keyed_on_sounder_id():
    q = EventQueue()
    synth = PolySynth(q, max_voices=8)
    q.push(_on(60))
    q.push(_on(64))
    _drive(synth, 2)
    assert synth.active_count() == 2
    q.push(_off(60))          # release only the sounder 60 voice
    _drive(synth, 1)
    # sounder 60 now releasing/idle; sounder 64 still ATTACK/SUSTAIN
    stages = {s: synth.voices[i].env.stage
              for i, s in enumerate(synth.voice_sounder) if s is not None}
    assert stages.get(64) in (EnvStage.ATTACK, EnvStage.SUSTAIN)


def test_off_freq_none_never_reaches_voice():
    # ev.freq is None on OFF; handle() must not pass it to a voice (no crash, and
    # the held frequency is untouched).
    q = EventQueue()
    synth = PolySynth(q, max_voices=4)
    q.push(_on(69))           # A4 = 440 Hz
    _drive(synth, 2)
    i = synth.voice_sounder.index(69)
    assert synth.voices[i].freq == midi_to_freq(69)
    q.push(_off(69))
    _drive(synth, 1)
    assert synth.voices[i].freq == midi_to_freq(69)   # unchanged, None never applied


def test_amp_move_applied_once_at_mix():
    # AMP-MOVE identity: a single sustained SineVoice renders pure timbre (peak ~1.0),
    # but the PolySynth linear mix scales it by AMP exactly once (peak ~AMP).
    q = EventQueue()
    synth = PolySynth(q, max_voices=1)
    q.push(_on(60))
    for ev in q.drain():
        synth.handle(ev)
    for _ in range(40):
        mix = synth.render(BLOCK_FRAMES, limit=False)     # linear: AMP * sum(voice)
    voice_peak = float(np.abs(synth.voices[0].render(BLOCK_FRAMES)).max())
    mix_peak = float(np.abs(mix).max())
    assert 0.98 <= voice_peak <= 1.0
    assert abs(mix_peak - AMP * voice_peak) < 1e-3


def test_custom_amp_scales_mix():
    q = EventQueue()
    synth = PolySynth(q, max_voices=1, amp=0.5)
    q.push(_on(60))
    for ev in q.drain():
        synth.handle(ev)
    for _ in range(40):
        mix = synth.render(BLOCK_FRAMES, limit=False)
    assert abs(float(np.abs(mix).max()) - 0.5) < 1e-2


@pytest.mark.perf
def test_render_cost_under_deadline():
    q = EventQueue()
    synth = PolySynth(q, max_voices=MAX_VOICES)
    for n in range(MAX_VOICES):
        q.push(_on(45 + n))
    _drive(synth, 4)
    assert synth.active_count() == MAX_VOICES
    k = 200
    t0 = time.perf_counter()
    for _ in range(k):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)
    cost = (time.perf_counter() - t0) / k
    assert cost / BLOCK_PERIOD < 0.5, \
        f"{MAX_VOICES} voices took {cost / BLOCK_PERIOD * 100:.1f}% of the block period"
