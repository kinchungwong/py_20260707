"""Parametrized-constructor and non-default-``sr`` coverage for the voices + Envelope.

The promotion added parametrized constructors (``n_partials`` / ``inharmonicity`` /
``rolloff`` / ``tau0``) and a non-default ``sr`` to every audio object; the original
spike selftests only exercised the defaults. These tests close that surface.

CONVENTION (matching test_voice.py): a sounder_id is a MIDI int and the frequency is
``midi_to_freq(that int)``. Voices are driven headlessly by rendering blocks directly.

RNG note: PianoVoice's per-partial phases are UNSEEDED, so every assertion here is
phase-independent -- FFT magnitudes, array shapes, per-partial increment/amplitude
values, decay ratios, dtypes -- never an exact sample value.
"""

from __future__ import annotations

import numpy as np

from pypiano_2607 import Voice, SineVoice, PianoVoice, Envelope, midi_to_freq
from pypiano_2607.config import SR, N_PARTIALS, INHARMONICITY, ATTACK_MS, TWO_PI


BLK = 383  # a headless render block (BLOCK_FRAMES); a voice honors any frame count


# --- local helpers ------------------------------------------------------------

def _render_voice(voice, n_samples: int, freq: float) -> np.ndarray:
    """Note-on ``voice`` at ``freq`` and render ``n_samples`` of pure timbre in blocks."""
    voice.note_on(freq)
    chunks, total = [], 0
    while total < n_samples:
        chunks.append(voice.render(BLK))
        total += BLK
    return np.concatenate(chunks)[:n_samples].astype(np.float64)


def _partial_count(sig: np.ndarray, f0: float, *, inharmonicity: float = INHARMONICITY,
                   n_partials: int = N_PARTIALS, sr: int = SR, thr: float = 0.1) -> int:
    """How many inharmonic partial slots carry >= ``thr`` of the fundamental's magnitude."""
    w = np.hanning(len(sig))
    mag = np.abs(np.fft.rfft(sig * w))
    freqs = np.fft.rfftfreq(len(sig), 1.0 / sr)
    vals = []
    for k in range(1, n_partials + 1):
        f_k = k * f0 * np.sqrt(1.0 + inharmonicity * k * k)
        if f_k >= sr / 2.0:
            break
        vals.append(float(mag[np.argmin(np.abs(freqs - f_k))]))
    vals = np.array(vals)
    return int(np.sum((vals / vals[0]) >= thr)) if len(vals) and vals[0] > 0 else 0


def _block_peaks(voice, freq: float, n_blocks: int) -> list[float]:
    """Per-block output peak of a sustained note (for measuring natural decay)."""
    voice.note_on(freq)
    return [float(np.abs(voice.render(BLK)).max()) for _ in range(n_blocks)]


# --- PianoVoice parametrized constructor --------------------------------------

def test_n_partials_sizes_partial_arrays_and_thins_the_spectrum():
    """n_partials=4 sizes every per-partial array to 4 and renders <= ~4 FFT partials,
    strictly fewer than the default (N_PARTIALS=16) voice."""
    v = PianoVoice(n_partials=4)
    v.note_on(midi_to_freq(60))
    assert v._amps.shape == (4,)
    assert len(v._k) == 4 and len(v._taus) == 4
    assert v._incs.shape == (4,) and v._phase.shape == (4,)

    f0 = midi_to_freq(60)
    n4 = _partial_count(_render_voice(PianoVoice(n_partials=4), 16384, f0), f0)
    default = _partial_count(_render_voice(PianoVoice(), 16384, f0), f0)
    assert n4 <= 4, f"n_partials=4 voice showed {n4} partials"
    assert default > n4, f"default voice ({default}) should be richer than n_partials=4 ({n4})"


def test_inharmonicity_zero_is_exactly_harmonic():
    """inharmonicity=0 makes f_k == k*f0 exactly; the default B spreads partials sharp,
    so the k=8 partial sits strictly higher with the default than with B=0."""
    f0 = midi_to_freq(60)
    harmonic = PianoVoice(inharmonicity=0.0)
    harmonic.note_on(f0)
    default = PianoVoice()
    default.note_on(f0)

    k = np.arange(1, N_PARTIALS + 1)
    expected = TWO_PI * k * f0 / SR                 # f_k == k*f0 when B == 0
    assert np.allclose(harmonic._incs, expected), "B=0 partials are not exactly harmonic"
    assert default._incs[7] > harmonic._incs[7], "default inharmonicity did not sharpen k=8"


def test_rolloff_larger_means_steeper_partial_falloff():
    """A larger rolloff shrinks the a2/a1 amplitude ratio (steeper 1/k^rolloff falloff).
    The unit-sum normalization scales a1 and a2 by the same factor, so a2/a1 survives it."""
    f0 = midi_to_freq(60)
    lo = PianoVoice(rolloff=0.5)
    lo.note_on(f0)
    hi = PianoVoice(rolloff=2.0)
    hi.note_on(f0)
    ratio_lo = lo._amps[1] / lo._amps[0]
    ratio_hi = hi._amps[1] / hi._amps[0]
    assert ratio_hi < ratio_lo, f"larger rolloff should shrink a2/a1: {ratio_hi} !< {ratio_lo}"


def test_tau0_small_decays_faster():
    """A small tau0 makes a held note die sooner: its late/early block-peak ratio is
    well below the default voice's."""
    f0 = midi_to_freq(60)
    small = _block_peaks(PianoVoice(tau0=0.2), f0, 200)
    default = _block_peaks(PianoVoice(), f0, 200)
    small_ratio = small[-1] / small[10]
    default_ratio = default[-1] / default[10]
    assert small_ratio < default_ratio, \
        f"small tau0 did not decay faster: {small_ratio} !< {default_ratio}"


# --- non-default sample rate --------------------------------------------------

def test_envelope_non_default_sr_scales_attack_samples():
    """attack_samples tracks the constructor sr, not the module default."""
    assert Envelope(sr=8000).attack_samples == max(1, round(ATTACK_MS / 1000.0 * 8000))


def test_sinevoice_non_default_sr_fft_peak_at_freq():
    """A SineVoice at sr=8000 puts its FFT peak at the played frequency, read off the
    rfftfreq axis computed with d = 1/8000 (the voice's own sr, not the default SR)."""
    sr = 8000
    freq = 300.0
    v = SineVoice(sr=sr)
    v.note_on(freq)
    sig = np.concatenate([v.render(512) for _ in range(40)]).astype(np.float64)
    mag = np.abs(np.fft.rfft(sig * np.hanning(len(sig))))
    freqs = np.fft.rfftfreq(len(sig), 1.0 / sr)
    peak = float(freqs[np.argmax(mag)])
    assert abs(peak - freq) < 1.0, f"sr=8000 sine peak at {peak} Hz, expected {freq} Hz"


def test_pianovoice_non_default_sr_nyquist_guard_drops_high_partials():
    """At sr=8000 (Nyquist 4000 Hz), PianoVoice.note_on() zeroes the phase increment of
    every partial at/above Nyquist -- so high partials contribute nothing."""
    sr = 8000
    v = PianoVoice(sr=sr)
    v.note_on(440.0)                               # partials k>=9 land at/above 4000 Hz
    k = v._k
    f_k = k * 440.0 * np.sqrt(1.0 + v._inharmonicity * k * k)
    guarded = f_k >= sr / 2.0
    assert guarded.any(), "expected some partials above Nyquist to exercise the guard"
    assert np.all(v._incs[guarded] == 0.0), "Nyquist-guarded partials must have zero increment"
    assert np.any(v._incs == 0.0)


# --- Voice Protocol conformance + dtype contracts -----------------------------

def test_voice_protocol_is_runtime_checkable():
    """The runtime-checkable Voice Protocol accepts both concrete voices and rejects
    an object that lacks the interface."""
    assert isinstance(SineVoice(), Voice)
    assert isinstance(PianoVoice(), Voice)
    assert not isinstance(object(), Voice)


def test_render_dtype_contracts():
    """Envelope gain is float64; both voices emit float32 (the callback's buffer dtype)."""
    assert Envelope().render(16).dtype == np.float64
    assert SineVoice().render(16).dtype == np.float32
    assert PianoVoice().render(16).dtype == np.float32


def test_pianovoice_idle_is_exact_silence():
    """A never-triggered PianoVoice (IDLE gate, zeroed partials) renders literal 0.0."""
    v = PianoVoice()
    out = np.concatenate([v.render(BLK) for _ in range(3)])
    assert np.all(out == 0.0), "idle piano voice not exactly silent"
