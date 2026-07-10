# Real-time gate envelope in a streaming callback (click-free via ramp-from-current-level)

How a note sustains while a key is held and releases without a click when the
key-up arrives asynchronously mid-stream. From the `realtime_envelope_release`
spike (`../../spikes/realtime_envelope_release.py`) — the first spike that turns
the interactive event path into sound. Replaces the batch synth's fixed-1 s
render (`[[piano-note-synthesis-recipe]]`) with a live gate.

## The state machine (per block)

`IDLE → ATTACK → SUSTAIN → RELEASE → IDLE`, carrying just `(stage, level)` across
blocks. The block renderer splits a `frames`-length block into per-stage segments,
so a stage boundary landing **inside** a ~383-frame block is handled — usually one
stage per block, occasionally two. IDLE renders exact `0.0`; SUSTAIN a flat `1.0`;
ATTACK/RELEASE are linear ramps.

## The click-free rule: ramp from the CURRENT level, never from a fixed value

- **note-off → RELEASE from the current level** down to 0 (over ~RELEASE_MS,
  scaling the step so the fade always spans the same time). Releasing "from 1.0"
  would jump the level up first = a click.
- **note-on → ATTACK from the current level** up to 1.0 → click-free *retrigger*
  even mid-release.

Measured (6 ms attack / 20 ms release, sine at C4): max envelope sample step
`0.00377` = exactly one attack ramp step (no jump); max **audio** sample step
`0.00745` = exactly `AMP·(2π·f/SR)`, the sine's *own* slope at full sustain — so
neither the envelope nor the block seams inject any discontinuity. A per-block
phase reset would have spiked this to ~`2·AMP`; a hard note-off gate to ~`AMP·level`.

## Why phase continuity is free

Carrying a phase accumulator across blocks (the `[[blocksize]]` /
outputstream_callback lesson) keeps the oscillator continuous at seams; the
audio-step bound above is measured across *all* seams, so it doubles as the
seam-continuity proof. Retuning `freq` mid-note (mono retrigger) changes the
increment, not the phase — no click.

## Scope decisions (this spike)

- **Monophonic, last-note priority.** One voice: note-on retriggers + retunes it;
  note-off releases only if it matches the active note (an older held key's
  note-off is ignored). This deliberately dodges voice allocation/stealing →
  that's `polyphony_voices` next.
- **Block-granular events.** Events apply at the top of the block, right after the
  non-blocking `[[event-queue]]` drain, so onset/release jitter is ≤ one block
  (~8.7 ms) — the bound event_queue already set. Sample-accurate placement (the
  callback gets a DAC-time arg) is deferred to `input_to_sound_latency`.
- **Pure sine, flat sustain** to isolate the envelope. Piano realism layers on
  cleanly and was NOT redone here: swap the flat SUSTAIN for the recipe's
  per-partial exponential decay, and the sine for the inharmonic-partial stack —
  both just *multiply* onto this same voice. That convergence belongs with the
  "promote `synth_note` into a module" synthesis task.

## Gotchas

- RT discipline: the per-block renderer allocates a few small NumPy arrays
  (`empty`/`arange`/`sin`). Fine at this scale; if it ever surfaces as an xrun,
  preallocate a scratch buffer sized to the max block and write in place.
- Anti-click times **6 ms attack / 20 ms release** (from `[[piano-note-synthesis-recipe]]`)
  were confirmed click-free streaming, not just in batch.

## Related

- Timbre/decay to layer on top: [[piano-note-synthesis-recipe]].
- The event source it consumes: [[event-queue]] (topology-A drain, in the audio
  callback) fed from [[note-event-reconciliation]].
- Block cadence / phase-accumulator lesson: [[blocksize]].
