# Polyphony: a fixed voice pool, summed and soft-limited in the callback

How multiple held keys become simultaneous notes. From the `polyphony_voices`
spike (`../../spikes/polyphony_voices.py`), which builds a pool of the
[[realtime-gate-envelope]] `Voice`s and sums them inside the topology-A audio
callback. Committed pool size: **16**.

## Allocation — three cases, in priority order

On note-on, pick a voice:

1. **the voice already on this note** (still sounding) → retrigger it;
2. else **any IDLE voice**;
3. else **steal** (pool full).

A voice frees *itself*: when its envelope render returns to IDLE, clear its note
tag. A note-off routes to the voice holding that note and only if it's
ATTACK/SUSTAIN. No per-block object allocation on the audio thread — the pool is
allocated once.

## Steal the QUIETEST voice

One line — `min(voices, key=lambda v: v.env.level)`. Because a **releasing** voice
has the lowest envelope level, it gets stolen before any held voice: you lose the
least-audible thing first, with **no note-age bookkeeping**.

**Stealing is click-free for free.** It reuses the envelope's ramp-from-current-level
retrigger plus the carried phase accumulator (see [[realtime-gate-envelope]]): the
stolen voice just retunes + re-attacks. Only the **pitch** jumps (expected for a
steal); there is no amplitude or phase discontinuity. Verified with 5 notes
overflowing a 4-voice pool — max output sample step 0.053, well under the click
bound 0.139.

## Headroom / limiting — `tanh` on the summed mix

Sum the active voices, then `np.tanh(mix)`:

- near-transparent for a few voices (AMP is small, so `tanh(x) ≈ x`);
- **saturating → never hard-clips** (measured peak 0.66 on a stacked cluster;
  `|out| < 1` always);
- `tanh` slope ≤ 1, so the limiter itself can't inject a click.

Trade-off: it adds mild harmonic distortion when driven hard. A look-ahead /
proper limiter is a later refinement, not needed yet.

## "How many voices before underruns?"

16 voices render in **~246 µs/block — ~2.8 % of the 8.68 ms block deadline**
(~15 µs/voice). The naive extrapolation is *hundreds* of voices, but that's
pure compute: real underruns also depend on Python/GC jitter and the whole audio
path. So **16 is comfortable**; the true ceiling is a question for
`input_to_sound_latency` on the real device. Confirmed independence with an FFT —
three simultaneous notes = three clean peaks (C4/E4/G4), not a blend.

## Gotchas

- FFT the **pre-limiter** sum when checking voice independence — `tanh` on the
  post-mix adds intermodulation peaks that muddy the test.
- RT note: `render()` allocates a mix buffer + per-voice arrays per block. Fine at
  16; if it bites, preallocate the mix and a scratch buffer (same hedge as
  [[realtime-gate-envelope]]).

## Related

- The per-voice oscillator + envelope this pools: [[realtime-gate-envelope]].
- Event source drained in the callback: [[event-queue]] ← [[note-event-reconciliation]].
- Timbre to layer per voice later: [[piano-note-synthesis-recipe]].
- Next: `input_to_sound_latency` (real-device latency + the honest voice ceiling).
