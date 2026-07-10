# Plan — Promote the spike signal chain into `src/pypiano_2607/`

**Status: Approved — increments 1–3 complete; increment 4 (Just Intonation option) done 2026-07-10** ·
Created 2026-07-09 · Synth core + input layer + app done; JI opt-in added. Other microtonal → future spikes.

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

## Increment 2 — input layer (active, 2026-07-09)

**Goal:** promote the GUI input path so `NoteEvent`s originate from real keyboard +
mouse input — **minting `sounder_id`s and resolving pitch→Hz at this edge**.
Everything here is headless-testable (SDL dummy); the live app shell (sounddevice
wiring) stays the next increment.

**Target — NEW files only; increment-1 modules stay untouched:**
```
src/pypiano_2607/
  router.py      — InputRouter: reference-count note holders by source; press/release
                   RETURN NoteEvents. Mints sounder_id = the pitch slot (MIDI for now)
                   and freq = midi_to_freq(midi) (None on release). pygame-free.
  gui/
    __init__.py
    keyboard.py  — the piano_keyboard widget: geometry, Key, build_keys, offset_keys,
                   hit_test (black-first), note_name, render_full, redraw_key, colors.
                   pygame imported LAZILY (the module imports headless).
    qwerty.py    — WHITE_QWERTY / BLACK_QWERTY (QWERTY→MIDI) + a key_to_midi(pygame) helper.
```
`InputRouter` is available as `pypiano_2607.router.InputRouter`; the widget as
`pypiano_2607.gui.keyboard`. (Promoting either into the top-level `__init__` public
API is left to the app increment, so increment 1's verified files stay frozen.)

**Source spikes → target (frozen; read, don't edit):** `input_integration.py`
(`InputRouter`) → `router.py`; `piano_keyboard.py` → `gui/keyboard.py`;
`kbd_input.py` (the QWERTY map) → `gui/qwerty.py`.

**The one design decision (forced, to preserve reconciliation):**
`sounder_id = the note's pitch slot` (the MIDI number, for now), so keyboard-C4 and
mouse-C4 reconcile to one sounding object — the [[note-event-reconciliation]]
behavior. The router computes `freq = midi_to_freq(midi)` at emit, making it the
**pitch→Hz resolution point** (cents/JI slot in here later, upstream of the unchanged
synth). See [[sounder-id]].

**Tests (pytest, headless):** `test_router.py` (reconciliation → one on/one off; the
emitted event carries `sounder_id==midi`, `freq==midi_to_freq(midi)` on ON / `None`
on OFF); `test_keyboard.py` (SDL-dummy: 14 white + 10 black, black-first hit-test,
`note_name`, dirty-rect repaint); `test_qwerty.py` (map is well-formed); and a
**slow** `test_integration.py` porting event_queue **T3** (transit latency ≤ one drain
interval, now driveable by the real `InputRouter`) + a router→queue→`PolySynth`
end-to-end.

**Constraints:** pygame stays LAZY (importing `router`/`qwerty`/the package must not
import pygame); tests set `SDL_VIDEODRIVER=dummy`. The input policy still binds —
**no `pygame.event.set_grab`** anywhere (`../policy/input-policy.md`). Spikes frozen.

## Increment 3 — the app (active, 2026-07-10)

**Goal:** promote the frozen [`playable_instrument`](../spikes/playable_instrument.py)
spike into a real, tested **app layer** — a **`PianoApp`** class (replacing the spike's
procedural `state` dict) that wires the full live signal chain
**PyGame loop → `InputRouter` → `EventQueue` → `PolySynth` →
`sounddevice.OutputStream(latency='low')`**. This is a **faithful port** (human
decision, 2026-07-10): same behavior as the spike, **no new features** — no velocity,
no sustain pedal, no octave-shift (the upper octave, MIDI 73–83, stays mouse-only, as
in the spike). Two pieces deferred out of the input layer are **promoted to the
library** here — the **mouse-glissando** drag state machine and the **window
geometry** — and this increment performs the **public-API promotion** deferred from
increment 2 (export `InputRouter` + the app surface from the package root). [[signal-chain]]

**Target — NEW files:**
```
src/pypiano_2607/
  mouse.py     — MouseGlissando: the single-active-mouse-note drag state machine,
                 promoted from the spike's _mouse_to + m_down/m_note. pygame-free AND
                 events-free (stdlib only): hit-test results (a MIDI int or None) go
                 IN; ("release", old)/("press", new) transition tuples come OUT.
  app.py       — PianoApp: the reusable playable shell. Owns router + queue + synth +
                 keyboard model + glissando + the visual held-set; methods
                 dispatch(event)->bool, emit(ev), all_notes_off(), run(), close().
                 pygame AND sounddevice are imported LAZILY inside methods, so importing
                 the module stays headless. NO argparse / __main__ / device I/O at
                 module scope (that lives in examples/ — altitude, see below).
examples/
  play_app.py  — the runnable CLI, mirroring examples/play_synth.py (NOT library code):
                 --voice piano|sine, --selftest (headless). Constructs PianoApp and
                 calls .run() (live) or drives the dispatch+callback path headless.
tests/
  test_mouse.py — MouseGlissando unit tests (pure, no pygame) + import guard.
  test_app.py   — headless: construct PianoApp under SDL dummy, feed synthetic PyGame
                  events through dispatch(), drive synth.callback by hand, assert the
                  acceptance behaviors below.
```

**Edited files (the sanctioned additive public-API promotion — no logic changes):**
```
src/pypiano_2607/__init__.py     — export InputRouter, MouseGlissando, PianoApp.
src/pypiano_2607/gui/__init__.py — add MARGIN=24, WIN_W=WIDTH+2*MARGIN,
                                   WIN_H=HEIGHT+2*MARGIN (pure arithmetic) + __all__.
tests/test_gui_package.py        — add "pypiano_2607.app" and "pypiano_2607.mouse" to
                                   LAZY_MODULES, and also assert 'sounddevice' stays
                                   unloaded (app must import sounddevice lazily too).
```
No **logic-bearing** increment-1/2 file is touched (config, pitch, events, queue,
router, audio/\*, gui/keyboard, gui/qwerty). **Spikes stay frozen.**

**Design decisions (several forced by an adversarial review of the draft, 2026-07-10):**

1. **`PianoApp` class (working name; trivially renamable, cf. `sounder_id`).**
   Encapsulates the spike's `state` dict as instance attributes
   (`pygame, screen, router, queue, synth, glissando, wk, bk, key_to_midi`) and its
   glue as methods. `__init__(*, voice="piano")` lazily `import pygame`, `pygame.init()`,
   `set_mode((WIN_W, WIN_H))`, `build_keys` + `offset_keys(wk+bk, MARGIN, MARGIN)`,
   `key_to_midi(pygame)`, `InputRouter()`, `EventQueue()`,
   `PolySynth(queue, voice_factory = PianoVoice if voice=="piano" else SineVoice)`,
   `MouseGlissando()`, then paints the unpressed keyboard. `run()` opens
   `sd.OutputStream(samplerate=SR, channels=1, dtype='float32',
   callback=synth.callback, latency='low')` and runs the `pygame.event.wait()` loop;
   `close()` calls `pygame.quit()`. **The same `dispatch(event)` runs live and under
   the tests** — the spike's key testability property, preserved.

2. **`emit(ev)` MUST early-return on `None`.** `InputRouter.press`/`release` return
   `None` on every *reconciled* transition (`router.py:53,58,64`) — that is the router's
   whole job. `emit` guards `if ev is None: return` (exactly `playable_instrument.py:92`)
   before `queue.push(ev)` + `redraw_key(screen, ev.sounder_id, wk, bk, router.held)` +
   `display.update`. Omitting the guard crashes on kbd+mouse-same-note and on
   mouse-up of a keyboard-held note. (`ev.sounder_id == midi` today, so `redraw_key`
   — keyed by MIDI — is addressed correctly; a comment notes the coupling since
   `events.py` warns sounder_id is *not* a pitch.)

3. **`MouseGlissando` — exact `_mouse_to` semantics** (`playable_instrument.py:109-119`
   + the dispatch bookkeeping at 149,151,153-155): state `down: bool`, `note: int|None`.
   - `press(midi)` sets `down=True` **regardless of `midi`** (a click in the 24px
     margin arms the drag with `midi=None`), then the change-detection below.
   - `motion(midi)` returns `[]` when `not down` (a bare mouse-move must be silent);
     else the change-detection.
   - `release()` returns the release of the current `note` (if any) and resets
     `down=False, note=None`.
   - change-detection `_move_to(new)`: `if new == note: return []`; else emit
     `("release", note)` if `note is not None`, then `("press", new)` if
     `new is not None`, then `note = new`.
   The app maps each `("press"/"release", midi)` to `router.press/release(midi,
   Source.MOUSE)` then `emit(...)`, so mouse↔keyboard reconciliation still happens in
   the one `InputRouter` (verified sound by the review).

3a. **Window geometry in `gui/__init__.py`** (mirrors `input_integration.py:75-76`):
   `MARGIN=24`, `WIN_W=WIDTH+2*MARGIN`, `WIN_H=HEIGHT+2*MARGIN`. Homed in the gui
   package `__init__` (already edited for exports) so `gui/keyboard.py` stays
   byte-frozen.

4. **`all_notes_off()` rewritten for the 5-field NoteEvent.** For each `midi` in
   `list(router.held)`, `queue.push(NoteEvent(NoteKind.OFF, midi, None,
   Source.KEYBOARD, perf_counter()))` (sounder_id=midi, freq=None) — each held note is
   in ATTACK/SUSTAIN so `PolySynth.handle` frees it by `sounder_id` (`polysynth.py:60`,
   review-confirmed) — then `router = InputRouter()`, reset the glissando,
   `render_full(unpressed)` + `flip`. (The spike's 4-field construct at line 127 is now
   wrong arity.)

5. **Altitude — the library stays pure; the CLI lives in `examples/`.** Every promoted
   `src/` module is import-only (no argparse, no `__main__`, no device);
   `examples/play_synth.py` is explicitly "not part of the library." So `PianoApp`
   (reusable class, incl. `run()`) lives in `src/pypiano_2607/app.py`, but the
   **argparse `main()`, `--voice/--selftest`, and `if __name__=="__main__"`** live in
   `examples/play_app.py`, mirroring `play_synth.py`. `--selftest`
   `os.environ.setdefault`s the SDL dummy drivers **before** constructing `PianoApp`
   (which imports+inits pygame). A `[project.scripts]` console entry is **deferred**
   (open question) — run via `.venv/bin/python examples/play_app.py`.

6. **The spike→library reconciliations applied** (the 12 deltas): new package import
   paths; `ev.midi`→`ev.sounder_id`; `synth.voice_midi`→`synth.voice_sounder`; use
   `gui.qwerty.key_to_midi(pygame)` (not the inline dict); explicit `SineVoice` for the
   sine default; the live path renders the callback's `frames` (never `BLOCK_FRAMES`);
   the router already mints `freq`, so the press/release/emit glue is otherwise
   unchanged. [[sounder-id]]

**Testing (pytest, headless — mirrors `test_router.py` / `test_integration.py`):**
- `test_mouse.py`: `press`→one press-transition; drag to a new key→release-old +
  press-new (glissando); drag to same key→`[]`; `motion` while not `down`→`[]`;
  margin-click (`press(None)`) then drag onto a key→arms then presses; `release`→
  release-transition + note cleared. (Pure — no pygame, no synth.)
- `test_app.py` (`SDL_VIDEODRIVER`/`AUDIODRIVER=dummy` at module top; a fixture that
  `close()`s each `PianoApp` — repeated `set_mode` needs teardown, cf.
  `test_keyboard.py:27`): via synthetic `pygame.event.Event`s through `dispatch()` +
  `synth.callback(out, frames, None, None)`:
  - kbd C4 + mouse G4 → `router.held == {60,67}`, `active_count()==2`,
    `{s for s in synth.voice_sounder if s is not None} == {60,67}`, peak>0;
  - release both → `active_count()==0` (after the release fade);
  - hold a note, `WINDOWFOCUSLOST` → `active_count()==0`;
  - mouse glissando C4→E4 while dragging → `router.held == {64}`;
  - kbd + mouse on the SAME note → exactly one voice (reconciliation holds);
  - `K_ESCAPE` / `QUIT` → `dispatch()` returns False.
- `test_gui_package.py`: `"pypiano_2607.app"` and `"pypiano_2607.mouse"` join
  `LAZY_MODULES`; the guard also asserts `'sounddevice' not in sys.modules` (app's
  sounddevice import must be lazy too).
- **Both nets green:** full pytest suite + `../../tools/run_spike_tests.py` 14/14
  (spikes untouched) + `../../tools/check_docs_links.py` clean.

**Acceptance = the spike's `--selftest` behaviors, preserved** (kbd+mouse chord →
2 reconciled voices; release → 0; focus-loss → all-notes-off → 0; glissando drag),
now asserted as deterministic pytest. **Not unit-tested** (as with the spike): the
live `run()` loop + real device I/O — only `dispatch()` is headless-driveable.

**Constraints preserved:** topology A (callback owns the drain, no worker thread);
`latency='low'`; focus-loss ⇒ all-notes-off, **never** `set_grab`; pygame + sounddevice
stay lazy so importing the package/app is headless; `.venv/bin/python` only, no pip;
spikes frozen; increment-1/2 logic files untouched.

**Bookkeeping on completion:** tick `../tasks/current.md`; a memory note only if an
integration fact proves non-obvious ([[signal-chain]]); a `../retrospectives/`
handoff; `check_docs_links` clean; commit (additive diff).

**The live ear-test** (`--voice piano` vs `sine` on a real device — the human A/B
outstanding since increment 1) is best finally done here.

**Open questions:** class name `PianoApp` vs `Instrument`; whether to add a
`[project.scripts]` console entry (`pypiano = ...`) — deferred unless wanted.

## Increment 4 — Just Intonation, as an option (active, 2026-07-10)

**Goal:** add **Just Intonation as an option** — 12-TET stays the default; a 5-limit JI
tuning is opt-in via a CLI flag. **Scope (human decision): JI ONLY.** Other microtonal
systems (non-12-EDO, arbitrary scales) are explicitly OUT — they need co-designed UI +
mechanics and must begin as **spikes** first. Spikes stay untouched.

**How it plugs in:** the `InputRouter` was designed as the pitch→Hz resolution point
("a cents/JI slot can live here later"). That slot is now used: `InputRouter` takes a
**`tuning` callable (`midi → Hz`)**, defaulting to 12-TET `midi_to_freq` — fully
backward-compatible (existing mint is byte-identical). The synth never sees it, and
`sounder_id` stays the MIDI pitch slot, so reconciliation + voice allocation are unchanged.

**Target — NEW file:**
```
src/pypiano_2607/tuning.py — JI_5LIMIT_RATIOS (1/1,16/15,9/8,6/5,5/4,4/3,45/32,3/2,8/5,
                             5/3,9/5,15/8); just_tuning(tonic=60) -> a midi->Hz closure
                             (tonic anchored to its 12-TET Hz, pure 2/1 octaves);
                             tonic_to_midi (note name -> midi; sharp = '#' or 's', flat =
                             'b' -- 's'/flats are shell-safe, '#' is a shell comment char).
                             pygame-free.
tests/test_tuning.py       — ratio table, anchoring, pure octaves, below-tonic wrap,
                             tonic-octave-cancels, name parsing, import guard.
```
**Edited (additive / backward-compatible):**
```
router.py            — InputRouter(tuning=midi_to_freq); press mints freq = tuning(midi).
app.py               — PianoApp(voice=..., tuning=None); all_notes_off recreates the
                       router WITH self._tuning (keeps the temperament across focus-loss).
__init__.py          — export just_tuning, tonic_to_midi.
examples/play_app.py — --tuning 12tet|ji (default 12tet), --tonic C (note name);
                       ap.error on a bad tonic.
tests/{test_router,test_app,test_gui_package}.py — JI coverage + tuning in the lazy guard.
```
No spike touched; the synth core + gui untouched.

**Decisions (human-chosen):** 5-limit standard ratios; a **selectable tonic** (`--tonic`,
default C), anchored to its 12-TET frequency (the tonic matches ET, other notes are
just-tuned around it). A runtime toggle is out — tuning is chosen at launch (the
router/synth are construction-time), matching the "command-line option" ask.

**Acceptance:** `just_tuning(60)(67) == midi_to_freq(60)·3/2` (just fifth); octaves pure;
JI audibly differs from ET; the default `InputRouter()` / `PianoApp()` stay exactly
12-TET; the JI tuning survives the focus-loss all-notes-off router reset. 137 pytest
green; spike net 14/14; spikes frozen.

## Later increments (sketch — not in scope now)

- **Input:** → now **Increment 2 (active)**, detailed above.
- **App:** → now **Increment 3 (active)**, detailed above — the `playable_instrument`
  shell as a `PianoApp` class (mouse-glissando + window geometry promoted to the
  library; `InputRouter`/`PianoApp` exported from the package root).
- **Just Intonation:** → now **Increment 4 (active)**, detailed above — a pluggable
  `tuning` at the `InputRouter` edge, 5-limit JI opt-in, 12-TET default.
- **Other microtonal (spikes first):** non-12-EDO / isomorphic layouts, or JI derived
  from arbitrary frequency ratios (e.g. 11/9 neutral third) — deliberately deferred to
  new spikes (co-designed UI + mechanics), NOT this library increment.
  [[chords-as-cents-above-root]]
- **Deferred refinements:** crossfade voice-stealing; reclaim held-but-decayed voice
  slots.
