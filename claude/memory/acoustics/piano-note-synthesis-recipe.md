# Piano note synthesis — working recipe (first spike)

A minimal additive-synthesis recipe that reliably produces a *piano-ish* (not
organ-ish) tone in NumPy, validated by the first spike
(`../../spikes/piano_chord_major_minor.py`). Reuse this as the starting point when
the synth is promoted into a real module. **Now realized as a streaming, per-block,
polyphonic voice** in [[streaming-piano-voice]] (this recipe folded into the
real-time path — affordable: ~26% of the block deadline at 16 voices).

## The recipe

Per note, sum `k = 1..N` partials of `sin`, then apply an amplitude envelope:

- **Inharmonic partial frequencies** (stiff-string model):
  `f_k = k * f0 * sqrt(1 + B * k^2)`, with **B ≈ 4e-4** for octave-4 notes.
  This detuning of upper partials is the single biggest contributor to the
  "piano, not organ" character.
- **Amplitude roll-off:** `a_k = 1 / k^1.2`.
- **Per-partial exponential decay, higher partials die sooner:**
  `tau_k = tau0 / (1 + 0.25*(k-1))`, with **tau0 ≈ 1.6 s**.
- **Randomized initial phase per partial** (`U(0, 2π)`) — avoids a synthetic
  all-in-phase attack transient.
- **Anti-click envelope:** ~6 ms linear attack ramp, ~20 ms release fade.
- **N ≈ 16 partials** is plenty for octave-4; guard each with
  `if f_k >= sr/2: break` to prevent aliasing above Nyquist.

## Gotchas worth remembering

- **Normalize the final mix, not per note.** Randomized phase makes the summed
  peak amplitude non-deterministic, so per-note headroom math can't be trusted.
- **No scipy in the venv.** Write WAVs with the stdlib `wave` module
  (int16, little-endian) — don't reach for `scipy.io.wavfile`.
- Reproducibility: seed one `np.random.default_rng(seed)` per chord and thread it
  through all its notes, so a chord is repeatable while notes still differ.

## Env facts (as of the first spike, 2026-07-07)

- `sounddevice` 0.5.5, `numpy` 2.5.1, Python 3.13; a live `default`/`pipewire`
  ALSA output device is present. Playback: `sd.play(mono_float, SR); sd.wait()`.

See the source spike `../../spikes/piano_chord_major_minor.py` for the exact,
runnable code.
