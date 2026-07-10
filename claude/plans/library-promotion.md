# Plan — Promote the spike signal chain into `src/pypiano_2607/`

**Status: Approved — increment 1 complete** (2026-07-09) · Created 2026-07-09 ·
Increment 1 of a multi-step promotion (input / app / microtonal to follow).

Promote the working interactive-instrument spikes into a real, maintained Python
package with a **pytest** suite — *without modifying the spikes*, which stay frozen
as the reference in [`../spikes/`](../spikes/). This is a **rewrite, not a copy**:
the spikes grew as a linear import chain where each module became the accidental
home for whatever constants it needed first, and MIDI is baked into the synth. The
library re-homes those and adopts a frequency-based, microtonal-ready event API.

Traces to [vision](../vision/README.md): keep input-to-sound latency low (preserve
topology A + `latency='low'`) and let the sound model generalize beyond 12-TET (the
pitch-API change is the enabler). Canonical architecture map: [[signal-chain]].

## Decisions locked (2026-07-09, with the human)

1. **Sequence — synth core first.** Increment 1 is the audio path *from the event
   boundary down to rendered samples*: config, pitch, event vocabulary, queue,
   envelope, voice, polysynth, + its pytest suite. GUI / input / router / app shell
   and the microtonal layout are later increments. (Matches the headline task in
   [`../tasks/current.md`](../tasks/current.md).)

2. **Pitch API — frequency (Hz) + a stable sounder-id.** `NoteEvent` carries `freq`
   (Hz, what the oscillator needs; `None` on note-off) and `sounder_id` (the identity
   the synth routes on). MIDI/cents→Hz conversion moves **upstream** into `pitch.py`
   / the input layer — **the synth never sees MIDI.**
   - **sounder-id semantics (human intent):** a sounder-id identifies an **acoustic
     object that receives events/actions** — *not* a keyboard key and *not* a pitch.
     Think of a guitar or violin **string**: one persistent sound-producing element
     that plays a wide range of pitches over its life. Two events that share a
     sounder-id act on the **same** object (note-on → note-off stop the same object;
     a second note-on retriggers it). The synth treats it as **opaque and hashable**.
     *Who mints sounder-ids* (a pitch-slot so keyboard+mouse on the same note
     reconcile, vs. a fresh id per press, vs. one-per-string) is an **input-layer**
     question, deferred to the input increment.
   - This is the same identity `PolySynth` already routes on for note-off and
     retrigger — it just stops being "the MIDI int." Working name `sounder_id`
     (provisional; trivial to rename — the human delegated the choice).

3. **Layout — `src/pypiano_2607/`.** src-layout package. Tests import it via pytest
   `pythonpath = src` (**no pip install** — respects
   [`../policy/locating_python_environment.md`](../policy/locating_python_environment.md);
   a real editable install stays the human's call, not needed for the suite).

4. **Drop the batch track.** `synth_note` / `synth_chord`, the stdlib-`wave` I/O,
   and the FFT-plot spikes are **not** promoted; `PianoVoice` is the canonical
   timbre. The 2-line `cents_to_hz` primitive *is* still lifted into `pitch.py` as
   the microtonal-ready sibling of `midi_to_freq` — that is the pitch formula, not
   the batch machinery. [[chords-as-cents-above-root]]

## Target structure (increment 1 in **bold**)

```
src/pypiano_2607/
  __init__.py
  config.py      **# SR, BLOCK_FRAMES/PERIOD, AMP, env times, partial params, MAX_VOICES — single source of truth**
  pitch.py       **# midi_to_freq, cents_to_hz  (the only pitch knowledge in the library)**
  events.py      **# NoteKind, Source, NoteEvent(kind, sounder_id, freq|None, source, t)**
  queue.py       **# EventQueue (deque; push / drain)**
  audio/
    __init__.py
    envelope.py  **# EnvStage, Envelope**
    voice.py     **# Voice (Protocol) + SineVoice + PianoVoice**
    polysynth.py **# PolySynth (pool, alloc/steal, master gain + tanh limit)**
  gui/           # LATER: keyboard.py, qwerty.py
  app.py         # LATER: the playable shell (was playable_instrument)
tests/           **# pytest — assertions lifted from the spikes' _selftest blocks**
pyproject.toml   **# package metadata + [tool.pytest.ini_options] pythonpath = ["src"]**
```

Spikes stay untouched; [`../../tools/run_spike_tests.py`](../../tools/run_spike_tests.py)
keeps guarding them and pytest guards the package — **two nets, on purpose.**

## Module-by-module mapping (what moves, what gets rewritten)

- **config.py** ← the scattered constants. Rewrite: de-duplicate `SR` (was defined
  in 3 spikes), pull env times out of `realtime_envelope_release`, partial params
  out of `piano_voice`, `MAX_VOICES` out of `polyphony_voices`, `AMP`/block out of
  their accidental homes in `event_queue`. **Strategy:** module-level constants are
  the source of truth; classes take the tunables they use as **constructor args
  defaulting to these** (so a test can build `PolySynth(max_voices=4)` or a voice at
  a different `SR`). No global mutable state, no config object forced everywhere —
  the current code already parameterizes `max_voices`/`voice_factory`; extend that.

- **pitch.py** ← `midi_to_freq` (from `realtime_envelope_release`) + `cents_to_hz`
  (from `microtonal_triads`). Pure, `SR`-independent functions.

- **events.py** ← `NoteKind`, `Source`, `NoteEvent` (from `input_integration`).
  **Rewrite:** `NoteEvent.midi: int` → `sounder_id` (opaque acoustic-object identity,
  documented per decision 2) **plus** `freq: float | None` (Hz on note-on, `None` on
  note-off). `InputRouter` is input-side reconciliation → stays for the input
  increment, not here. [[note-event-reconciliation]]

- **queue.py** ← `EventQueue` (from `event_queue`). Near-verbatim; drop the
  `SR`/`BLOCK_FRAMES` constants (→ config) and the vocab re-export (import from
  events). Semantics unchanged — topology A, non-blocking deque. [[event-queue]]

- **audio/envelope.py** ← `EnvStage`, `Envelope` (from `realtime_envelope_release`).
  Verbatim state-machine logic; times from config; drop module globals.
  [[realtime-gate-envelope]]

- **audio/voice.py** ← `Voice`→`SineVoice`, `PianoVoice` (from
  `realtime_envelope_release` + `piano_voice`), **plus a `Voice` Protocol/ABC** that
  makes the de-facto interface explicit: `note_on(freq)`, `note_off()`,
  `render(frames) -> np.ndarray`, `.env`. **Rewrite:** move master `AMP` *out* of the
  voice (see boundary note below); per-voice partial normalization (sum→1) stays.
  Drop `MonoSynth` (superseded) and `note_event` (a test helper → lives in tests).
  [[streaming-piano-voice]]

- **audio/polysynth.py** ← `PolySynth` (from `polyphony_voices`). **Rewrite:**
  `handle()` no longer calls `midi_to_freq` — note-on does `voice.note_on(ev.freq)`;
  allocation / steal / note-off route on `ev.sounder_id`. Master gain applied here:
  `tanh(AMP * mix)`. Allocation still inspects `voice.env` through the Protocol.
  [[polyphony-voice-pool]]

## The AMP / normalization boundary (behavior-preserving)

Today each voice renders `AMP * wave * gain`; `PolySynth` sums then `tanh`. Because
`AMP` factors out — `Σ AMP·vᵢ = AMP·Σvᵢ` — `tanh(AMP · Σ vᵢ)` is identical whether
`AMP` multiplies inside each voice or once on the mix. Moving it to the mix makes
**voice = pure timbre, PolySynth = gain + limit** with *zero numeric change*. This
is the clean answer to the "mixing/normalization vs oscillator" boundary question.

## Testing plan (pytest)

- Config via `pyproject.toml` → `[tool.pytest.ini_options]` with
  `pythonpath = ["src"]`, `markers = ["perf: ...", "slow: ..."]`, and
  `addopts = ["-m", "not perf"]`. **No install** (respects the venv policy). Run:
  `.venv/bin/python -m pytest` (all but perf); `-m perf` to opt in; `-m slow` for the
  threaded ones. **Verified in-venv: custom marks need no plugin** — pytest 9.1.1 +
  pluggy only; a CLI `-m perf` overrides the default `-m "not perf"`.
- Lift the `_selftest` **assertions** (leave `_plot` / `_play` behind) into
  deterministic `test_*`:
  - **pitch:** `midi_to_freq(69) == 440`; octave = 2×; `cents_to_hz(f, 1200) == 2f`,
    `(f, 0) == f`; neutral third ≈ between minor/major.
  - **envelope:** idle exact-silence; attack monotonic→1; sustain flat 1.0; release
    monotonic→0 then silent; max sample step ≤ one ramp step (click-free).
  - **voice_sine:** exactly one FFT partial; phase-continuous / click-free across
    block seams.
  - **voice_piano:** ≥4 audible partials; held note decays (late < 0.6·early);
    click-free fresh note; no clip.
  - **polysynth:** 3 notes → 3 independent peaks (pre-limiter linear sum); pool cap
    enforced; voices freed after release; steal is no-clip + click-bounded; note-off
    routes by `note_id`.
  - **queue:** no-drop / no-reorder under flood; producer never blocks; bounded ring
    drops the oldest.
- **Perf / timing** asserts (render-cost-vs-deadline, push µs) are machine-dependent
  → behind `@pytest.mark.perf` (deselected by default) so the default suite is
  deterministic. Threaded queue tests → `@pytest.mark.slow`, deadline-guarded.

## Non-negotiables to preserve

- **Topology A** — the callback owns the drain; no worker thread
  ([topology B](../speculations/audio-consumer-worker-thread.md) stays parked).
- **`latency='low'`** on the real OutputStream (app increment); the synth core is
  device-free / fully headless.
- **`.venv/bin/python` only; no pip installs by the agent**
  ([`../policy/locating_python_environment.md`](../policy/locating_python_environment.md)).
- **Spikes are frozen** — read-only reference, never edited.

## Resolved (2026-07-09)

- **note-off `freq`:** one `NoteEvent` dataclass, `freq: float | None` — `None` on
  note-off. ✓
- **identity field:** `sounder_id` (working name), typed `int` for now, with the
  acoustic-object / string docstring. ✓
- **packaging:** minimal `pyproject.toml` (metadata + pytest config; **not**
  installed). ✓
- **perf tests:** `@pytest.mark.perf`, off by default via `addopts = -m "not perf"`;
  **no extra pip install** (verified in-venv, pytest 9.1.1 + pluggy only). ✓

## Open questions (non-blocking)

- Whether the one-block transit-latency bound (event_queue T3 /
  `input_to_sound_latency`) belongs in this increment (as a `slow` integration test)
  or the input increment. **Leaning:** defer to input.

## Later increments (sketch — not in scope now)

- **Input:** promote the `piano_keyboard` widget, the QWERTY map, and `InputRouter`
  (events.py sibling) + the kbd/mouse→router glue. **This is where note-ids are
  minted and MIDI/cents→Hz happens.** Pulls reusable bits from `kbd_input` /
  `mouse_input` / `keyboard_static_display`.
- **App:** the `playable_instrument` shell (focus-loss all-notes-off,
  `latency='low'`) as an `Instrument`/`App` class instead of the procedural `state`
  dict.
- **Microtonal:** `microtonal_layout` — now unblocked; cents/JI live upstream of the
  (unchanged) synth. [[chords-as-cents-above-root]]
- **Deferred refinements:** crossfade voice-stealing; reclaim held-but-decayed voice
  slots.
