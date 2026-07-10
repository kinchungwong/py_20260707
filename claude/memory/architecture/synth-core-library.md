# The promoted synth core: `src/pypiano_2607/` (library-promotion increment 1)

The interactive-instrument spikes' audio path is now a real, tested package —
`src/pypiano_2607/` — built by increment 1 of `../../plans/library-promotion.md`
(2026-07-09). The spikes stay frozen in `../../spikes/`; this is a **rewrite** of
their structure, not a copy, with the DSP math transcribed verbatim.

## Layout (the module boundary)

```
src/pypiano_2607/
  config.py    — single source of truth for every tuning/sizing constant
  pitch.py     — midi_to_freq, cents_to_hz  (the ONLY pitch knowledge)
  events.py    — NoteKind, Source, NoteEvent(kind, sounder_id, freq|None, source, t)
  queue.py     — EventQueue  (topology-A deque; verbatim)   [[event-queue]]
  audio/
    envelope.py  — EnvStage, Envelope                        [[realtime-gate-envelope]]
    voice.py     — Voice (runtime-checkable Protocol) + SineVoice + PianoVoice
    polysynth.py — PolySynth (pool, alloc/steal, gain + tanh) [[polyphony-voice-pool]]
```

Tests live in `tests/` (pytest, 68 tests). The package imports with **no install**
via pyproject `pythonpath=["src"]` — never pip-install (the venv policy,
`../../policy/locating_python_environment.md`). Custom `perf`/`slow` marks keep the
default suite deterministic (`perf` deselected via `addopts`; verified to need no
plugin).

## The three structural decisions (why it's a rewrite, not a copy)

1. **Constants get one home** (`config.py`). `SR` was defined in 3 spikes; env times,
   partial params, and `MAX_VOICES` were scattered. Classes now take the tunables
   they use as **constructor args defaulting to config** (so a test can build
   `PolySynth(max_voices=4)` or a voice at a different `sr`). No global mutable state.
2. **Frequency in, MIDI out of the synth.** `NoteEvent` carries `freq` (Hz) +
   `sounder_id` (identity) — see [[sounder-id]]. `PolySynth` calls
   `voice.note_on(ev.freq)` directly; `midi_to_freq` lives only in `pitch.py`,
   upstream. This is what unblocks microtonal ([[chords-as-cents-above-root]]).
3. **The AMP-move.** Voices render *pure timbre* (no master gain); `PolySynth`
   applies `mix *= amp` **once**, before the `tanh` limiter. Since
   `sum(AMP·xᵢ) == AMP·sum(xᵢ)`, the output is **bit-exact** to the spikes (verified
   maxdiff 0.0). Voice = timbre; PolySynth = gain + limiting. [[streaming-piano-voice]]

## Non-obvious facts

- The `Voice` **Protocol** (runtime-checkable) makes the de-facto interface explicit:
  `note_on(freq)`, `note_off()`, `render(frames)`, `.env`. `PolySynth` inspects
  `voice.env.stage`/`.level` for allocation/stealing, so `.env` is part of the contract.
- `queue.py` is named `queue` but does **not** shadow stdlib `queue` for absolute
  imports (verified `pypiano_2607.queue is not queue`).
- Dtypes: `Envelope.render` → float64 gain; a voice's `render` → float32; the mix
  sums in float64 then casts to float32 at the callback boundary.
- **Dropped** from the library: the batch `synth_note`/`synth_chord`, the stdlib-wave
  I/O, and the FFT-plot spikes (the streaming `PianoVoice` is the canonical timbre);
  and `MonoSynth` (superseded by `PolySynth`). `InputRouter` is **deferred** to the
  input increment.

## Related

- Identity model: [[sounder-id]]. End-to-end pipeline this feeds: [[signal-chain]].
- Source recipes now folded in: [[streaming-piano-voice]], [[realtime-gate-envelope]],
  [[polyphony-voice-pool]], [[event-queue]]. Plan: `../../plans/library-promotion.md`.
