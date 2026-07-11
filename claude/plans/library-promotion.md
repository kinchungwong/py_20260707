# Plan — Promote the spike signal chain into `src/pypiano_2607/`

**Status: Done** — increments 1–4 complete, committed (`2be5011`), human-tested on real
hardware (2026-07-09 → 2026-07-10). Kept as a record per [`README.md`](README.md); the build
detail lives in git history and the retrospectives, the durable facts in
[`../memory/`](../memory/README.md). Collapsed 2026-07-10 from the full working plan.

Traces to [vision](../vision/README.md): low input-to-sound latency (topology A +
`latency='low'`) and a sound model that generalizes beyond 12-TET (the frequency-based pitch
API is the enabler).

## What this plan did

Turned the frozen interactive-instrument spikes ([`../spikes/`](../spikes/README.md)) into a
maintained, pytest-tested package `src/pypiano_2607/` — a **rewrite, not a copy**: the spikes
grew as a linear import chain where each module became the accidental home for whatever
constant it needed first, and MIDI was baked into the synth. The library re-homed those
constants and adopted a frequency-based, microtonal-ready event API. Four increments, all
shipped:

1. **Synth core** — `config` / `pitch` / `events` / `queue` / `audio` into `src/`. As-built
   plus the three structural decisions: [[synth-core-library]].
2. **Input layer** — `InputRouter` (multi-source reconciliation + the pitch→Hz mint),
   `gui/keyboard`, `gui/qwerty`. [[note-event-reconciliation]]
3. **The app** — `PianoApp` + `MouseGlissando`: the full live chain
   PyGame → `InputRouter` → `EventQueue` → `PolySynth` → `sounddevice(latency='low')`.
   [[signal-chain]]
4. **Just Intonation, as an option** — a pluggable `tuning` (midi→Hz) at the `InputRouter`
   edge; 5-limit JI opt-in, 12-TET default (`--tuning ji --tonic`).

Collapsed completion index: [`../tasks/done.md`](../tasks/done.md).

## Decisions that still govern

These outlived the plan — each detailed in memory, summarized here so this file stands alone:

- **Frequency in, MIDI out of the synth.** `NoteEvent(kind, sounder_id, freq|None, source,
  t)`; MIDI/cents→Hz resolves upstream (`pitch.py` / `InputRouter`) — the synth never sees
  MIDI. This split is what keeps it microtonal-ready. [[synth-core-library]]
- **`sounder_id` = the acoustic object** (a *string*, not a key, not a pitch) — the opaque
  identity `PolySynth` routes on for allocation, retrigger, and note-off. [[sounder-id]]
- **The AMP-move** — voice = pure timbre, `PolySynth` = master gain + `tanh` limit. Bit-exact
  to the spikes (`Σ AMP·vᵢ = AMP·Σ vᵢ`; verified maxdiff 0.0). [[synth-core-library]]
- **Topology A** — the audio callback owns the queue drain; no worker thread
  ([topology B](../speculations/audio-consumer-worker-thread.md) stays parked).
- **`latency='low'`** on the real OutputStream; the synth core stays device-free / headless.
- **JI-only scope (human decision).** Anything else microtonal — non-12-EDO, arbitrary
  ratios, isomorphic layouts — begins as a **new spike**
  ([`../../focused-spikes/`](../../focused-spikes/README.md)), never a library increment.
  [[chords-as-cents-above-root]]
- **Standing constraints:** `.venv/bin/python` only, no agent pip-installs
  ([policy](../policy/locating_python_environment.md)); the legacy spikes stay frozen; the
  input policy forbids `pygame.event.set_grab` (focus-loss ⇒ all-notes-off).

## As-built

The canonical module map and end-to-end path live in memory — [[synth-core-library]] (the
package) and [[signal-chain]] (the signal chain). Two test nets: `.venv/bin/python -m pytest`
(137 default; +`slow`/`perf`) for the package, and `tools/run_spike_tests.py` for the frozen
spikes. Runnable demo (not library code): `examples/play_app.py` — `--voice piano|sine`,
`--tuning 12tet|ji`, `--tonic`.

**Not carried forward:** the batch track (`synth_note` / `synth_chord`, stdlib-`wave` I/O,
the FFT-plot spikes) and `MonoSynth` were deliberately not promoted — `PianoVoice` is the
canonical timbre, `PolySynth` supersedes `MonoSynth`.
