# Current tasks

## Synthesis

- [x] Spike: prove piano major (C-E-G) vs minor (C-Eb-G) chord synthesis through
      sounddevice, no PyGame. → `../spikes/piano_chord_major_minor.py`;
      recipe in `../memory/acoustics/piano-note-synthesis-recipe.md`.
- [x] Spike: extend to microtonal triads — major/minor/augmented/diminished/
      **neutral** via cents-above-root. → `../spikes/microtonal_triads.py`;
      approach in `../memory/musictheory/chords-as-cents-above-root.md`. Confirms the
      cents-based frequency source generalizes the synth beyond 12-TET.
- [x] Spike: headless FFT plots of the chord wavs → PNG (matplotlib Agg, no
      GUI/X/Wayland/TTY). → `../spikes/fft_plots.py`; technique in
      `../memory/matplotlib/headless-png.md`. `fft_triads_compare.png` shows the
      shared root, moving third, and aug/dim fifth in one view.
- [x] Spike: pull-model audio — sounddevice `OutputStream` with a callback, mono,
      generate exactly the requested `frames` per call, run 5 s. →
      `../spikes/outputstream_callback.py`; block-size findings in
      `../memory/sounddevice/outputstream/blocksize.md`. This is the audio-engine
      foundation the interactive GUI feeds into.
- [x] Spike: bring the batch timbre into the STREAMING voice — inharmonic partials
      + per-partial decay + phase randomization, per-block, drop-in to `PolySynth`.
      → `../spikes/piano_voice.py` (`--selftest` + PNG); `../memory/acoustics/streaming-piano-voice.md`.
      **`PianoVoice`** (same `note_on/note_off/render/.env` interface as `Voice`,
      swapped via `PolySynth(voice_factory=...)`). Held notes now decay like a piano;
      affordable (~26% of the block deadline at 16 voices, ~39% at `latency='low'`).
- [x] **Increment 1 — promote the synth core** into `src/pypiano_2607/` with a
      pytest suite (**DONE 2026-07-09**). Plan:
      [`../plans/library-promotion.md`](../plans/library-promotion.md). Built
      bottom-up from the frozen spikes; 68 pytest tests, all green.
    - [x] `config.py` — one home for SR / block / AMP / env times / partial params / MAX_VOICES
    - [x] `pitch.py` — `midi_to_freq`, `cents_to_hz` (the only pitch knowledge; synth never sees MIDI)
    - [x] `events.py` — `NoteKind`, `Source`, `NoteEvent(kind, sounder_id, freq|None, source, t)`
    - [x] `queue.py` — `EventQueue` (topology-A deque, verbatim)
    - [x] `audio/envelope.py` — `EnvStage`, `Envelope`
    - [x] `audio/voice.py` — `Voice` Protocol (runtime-checkable) + `SineVoice` + `PianoVoice` (master `AMP` at the mix)
    - [x] `audio/polysynth.py` — `PolySynth` (routes on `sounder_id`/`freq`; master gain + tanh limit)
    - [x] `pyproject.toml` (pytest `pythonpath=src`, `perf`/`slow` marks) + `tests/` (8 files)
    - [x] Green: pytest 65 + 3 perf = 68 · `../../tools/run_spike_tests.py` 14/14 (spikes untouched) · `../../tools/check_docs_links.py` clean
    - Deferred to the input increment: `InputRouter`, the one-block transit-latency test.
    - **Not yet ear-tested** through a live device (headless-verified only — worth a human A/B before the next increment).
- [x] Swap `PianoVoice` into `playable_instrument` as the **default** voice, with
      `--voice piano|sine` to A/B against the plain sine. → `../spikes/playable_instrument.py`
      (`voice_factory` wired to the `--voice` choice; both paths pass `--selftest`).
- [ ] Future spike: just-intonation color — derive cents from frequency ratios
      (e.g. neutral third 11/9 ≈ 347.4c) instead of a fixed cent grid.
- [ ] Refinement (deferred): crossfade voice-stealing (kill the small steal artifact
      the piano voice adds), and reclaim held-but-fully-decayed voice slots.

## Interactive GUI (PyGame)

A sequence of mostly-spikes building toward a playable instrument: draw → capture
input → hand events across a thread boundary → make sound → measure latency. Input
is split into separate keyboard and mouse spikes, then integrated; pitch stays
plain 12-TET / MIDI for now (microtonal deferred — see the end of this section).
**Milestone reached:** the full path is now wired end to end and playable
(`playable_instrument`); the canonical signal chain lives in
`../memory/architecture/signal-chain.md`. What's left here is measurement
(`input_to_sound_latency`) and the deferred microtonal layout.

Shared keyboard widget: `../spikes/piano_keyboard.py` (geometry, drawing, hit-test,
`note_name`) — extracted from `kbd_input`/`mouse_input`; build the remaining GUI
spikes on it rather than re-drawing the keyboard.

- [x] Spike: static keyboard display — draw a piano keyboard, quit on Esc.
      Establishes the PyGame window, draw, and basic event loop. →
      `../spikes/keyboard_static_display.py` (`--selftest` for a headless smoke
      test); headless-verify technique in `../memory/pygame/headless-render-to-png.md`.
- [x] Spike `kbd_input`: computer keyboard → highlight the mapped on-screen key
      on `KEYDOWN`/`KEYUP`, track the held-key set. Defines the QWERTY→MIDI-note
      map. No audio. → `../spikes/kbd_input.py` (`--selftest`). Answered both Qs:
      clean press/release pairs (no auto-repeat by default → note-on/off in
      `../memory/pygame/key-events-note-on-off.md`); yes to per-key dirty-rect
      redraw, minding black-over-white overlap.
- [x] Spike `mouse_input`: mouse → hit-test `MOUSEBUTTONDOWN`/`UP` against the
      drawn key rects, highlight + track pressed. No audio. → `../spikes/mouse_input.py`
      (`--selftest`); model in `../memory/pygame/mouse-hit-test-piano.md` (black-first
      hit-test, glissando drag). Edge cases handled; release-outside-window confirmed
      fine by manual test (SDL2 implicit mouse capture; no `set_grab` needed).
- [x] Spike `input_integration`: unify keyboard + mouse behind one abstraction
      that emits a single **note-on / note-off event stream** (tagged by source),
      reconciling held-state from both. → `../spikes/input_integration.py`
      (`--selftest`). `InputRouter` reference-counts each note by holder-set (note-on
      on 0→1, note-off on 1→0); `NoteEvent(kind, midi, source, t)` is the interface
      the audio side consumes. Approach in `../memory/input/note-event-reconciliation.md`.
- [x] Spike `event_queue`: GUI loop pushes semantic events onto a **thread-safe
      queue**; a consumer drains it **non-blocking** and applies them. **Committed
      topology A**: the audio callback drains the queue directly (worker-thread
      topology B still parked in `../speculations/audio-consumer-worker-thread.md`).
      → `../spikes/event_queue.py` (`--selftest`); decision + properties in
      `../memory/concurrency/event-queue.md`. Carrier is a lock-free
      `collections.deque` (NOT `queue.Queue` — its lock is an RT hazard); verified
      no drop/reorder under flood, producer never blocks (~0.15 µs/push), transit
      latency bounded by one drain interval (~8.7 ms block period). Fed by the real
      `InputRouter`. No audio, as planned.
- [x] Spike `realtime_envelope_release`: sustain a voice **while a key is held**,
      click-free release on key-up — replaces the fixed-1 s render from the batch
      spikes. Consumes drained note_on/note_off events. → `../spikes/realtime_envelope_release.py`
      (`--selftest` + preview PNG); technique in `../memory/acoustics/realtime-gate-envelope.md`.
      First spike that makes sound from the interactive path. **A: yes** — per-block
      ASR state machine carrying `(stage, level)`; click-free = ramp from the
      *current* level (release) / re-attack from current (retrigger); phase
      accumulator gives seam-continuity for free. Scope: **monophonic** (last-note
      priority), pure sine, flat sustain, block-granular events (jitter ≤ 1 block).
      Piano decay + inharmonic partials layer on later (synth-module task).
- [x] Spike `polyphony_voices`: multiple held keys → summed voices with allocation
      + headroom/limiting in the callback. → `../spikes/polyphony_voices.py`
      (`--selftest` + PNG); technique in `../memory/acoustics/polyphony-voice-pool.md`.
      **A:** fixed pool (**16**); allocate = same-note / free / **steal the quietest**
      (releasing voice goes first, no age bookkeeping); steal is click-free by
      reusing the envelope retrigger; `tanh` soft-limit on the mix never clips.
      Cost: 16 voices ≈ 2.8% of the block deadline (~15 µs/voice) — 16 is comfy,
      true ceiling deferred to `input_to_sound_latency` on the real device. FFT
      confirms 3 notes → 3 independent peaks.
- [x] Spike `playable_instrument`: **wire it all end to end** — keyboard/mouse →
      `InputRouter` → `EventQueue` → `PolySynth` → sounddevice. First playable
      instrument. → `../spikes/playable_instrument.py` (`--selftest` + PNG);
      architecture in `../memory/architecture/signal-chain.md`. ~30 lines of glue
      over four reused-unmodified modules; GUI thread = producer, audio callback =
      consumer, one lock-free deque between them. Chord from both sources sounds
      once; focus-loss = all-notes-off (never a cursor grab). Seed of the real app.
- [x] Spike `input_to_sound_latency`: measure keypress→audible onset and find what
      dominates. → `../spikes/input_to_sound_latency.py` (`--selftest` + PNG; real
      device mode for term (d)); finding in `../memory/sounddevice/outputstream/latency.md`.
      **A:** device output latency dominates (~11.4 ms); the lever is **`latency='low'`**
      (~35 → ~9 ms), NOT a smaller requested blocksize (which does nothing).
      With `latency='low'`: onset ~12.9 ms mean / ~19 ms p99; software glue ~0.1 µs.
      Tail (max ~28 ms) is Python/GC jitter — the vision's inherent-limits caveat.
      **Committed `latency='low'`; applied to `playable_instrument`.** Front-end
      (OS→PyGame) unmeasured (needs mic loopback).
- [ ] Deferred: Spike `microtonal_layout` — non-piano / isomorphic layout exposing
      the neutral third etc. Parked until the interactive path works end-to-end;
      ties back to `../memory/musictheory/chords-as-cents-above-root.md`.

## Notes

- Blocked/open: none yet. See `../vision/` for the latency and tuning constraints
  these tasks must respect.
- Architectural forks that aren't committed live in `../speculations/` (currently:
  the worker-thread audio consumer, topology B).
