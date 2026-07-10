# Streaming piano voice: the batch recipe folded into the per-block voice

The batch [[piano-note-synthesis-recipe]] (inharmonic partials + per-partial decay
+ phase randomization) works as a real-time, polyphonic, streaming voice. Proven by
the `piano_voice` spike (`../../spikes/piano_voice.py`). `PianoVoice` is a drop-in
for the sine [[realtime-gate-envelope]] `Voice` via `PolySynth`'s `voice_factory`.

## What changed vs the sine Voice

- **K inharmonic partials** `f_k = k·f0·√(1+B·k²)` (B=4e-4), amplitudes `1/k^1.2`
  normalized to sum 1, Nyquist-guarded — computed once at note-on.
- **Per-partial exponential decay** `exp(-t/tau_k)` from a per-voice sample `age`
  (`tau_k = 1.6/(1+0.25(k-1))`). This is the big audible change: a **held note now
  DECAYS naturally (piano)** instead of flat-sustaining (organ). Peak ~0.11 → ~0.03
  over 1.5 s in the spike.
- **Randomized per-partial phase** at note-on.
- The gate `Envelope` (6 ms attack / 20 ms release) still multiplies on top for
  click-free onset and key-release; the partials sit *inside* the gate.

## Make it cheap: vectorize partials as one `(K, frames)` block

One `sin` and one `exp` over a `(K, frames)` array per voice per block — NOT a
per-partial Python loop. That's what keeps the cost sane.

**Cost (16 voices):** ~2240 µs/383-block ≈ **26%** of the 8.68 ms deadline
(vs ~242 µs / 2.8% for sine — ~9×). At `latency='low'` (~95-frame, 2.15 ms
deadline): ~846 µs ≈ **39%**. So full 16-voice piano polyphony fits with ~60%
headroom even in the low-latency config (see [[latency]]).

## The honest trade-off: steal is no longer phase-continuous

The sine voice kept phase across a steal → click-free. `PianoVoice.note_on`
re-inits phase + `age`, so a steal injects a small artifact — measured max step
~0.125 (vs ~0.05 for the sine pool). NOT a hard clip: it's scaled by the stolen
voice's gate level, and [[polyphony-voice-pool]] steals the QUIETEST voice, so
it's small. **Crossfade-steal** is the clean fix (still deferred).

## Not addressed (refinements)

- A held-but-fully-decayed note still holds its voice slot (gate is SUSTAIN though
  silent) — a "reclaim voices below an amplitude threshold" refinement.
- `PianoVoice.note_on` allocates a few arrays + calls the RNG on the audio thread;
  fine at this scale, preallocate if it ever bites.

## Status

- **Now the default voice in `playable_instrument`** (`--voice piano|sine` A/Bs it
  against the plain sine), wired via `PolySynth(voice_factory=PianoVoice)`.
- The `Voice`/`PianoVoice` interface (`note_on(freq)`, `note_off()`, `render`,
  `.env`) is the seam to build the real synth module on.

## Related

- Batch source recipe: [[piano-note-synthesis-recipe]]; the gate + oscillator it
  extends: [[realtime-gate-envelope]]; the pool that sums them: [[polyphony-voice-pool]].
- Where it plugs into the app: [[signal-chain]].
