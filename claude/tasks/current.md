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
- [ ] Promote the spike's `synth_note` / `synth_chord` into a real, tested module
      (pytest). Decide the module boundary before coding — likely a `Note` render
      function separate from mixing/normalization. Adopt cents-above-root as the
      chord API (see memory), not MIDI integers.
- [ ] Future spike: just-intonation color — derive cents from frequency ratios
      (e.g. neutral third 11/9 ≈ 347.4c) instead of a fixed cent grid.

## Interactive GUI (PyGame)

A sequence of mostly-spikes building toward a playable instrument: draw → capture
input → hand events across a thread boundary → make sound → measure latency. Input
is split into separate keyboard and mouse spikes, then integrated; pitch stays
plain 12-TET / MIDI for now (microtonal deferred — see the end of this section).

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
- [ ] Spike `realtime_envelope_release`: sustain a voice **while a key is held**,
      click-free release on key-up — replaces the fixed-1 s render from the batch
      spikes. Consumes drained note_on/note_off events. *Q: attack/sustain/release
      per-block in a streaming callback?*
- [ ] Spike `polyphony_voices`: multiple held keys → summed voices with allocation
      + headroom/limiting in the callback. *Q: how many voices before underruns;
      how to allocate/steal?*
- [ ] Spike `input_to_sound_latency`: measure keypress→audible onset and find what
      dominates (audio blocksize vs event-poll interval vs envelope attack). Serves
      the latency non-negotiable in `../vision/`.
- [ ] Deferred: Spike `microtonal_layout` — non-piano / isomorphic layout exposing
      the neutral third etc. Parked until the interactive path works end-to-end;
      ties back to `../memory/musictheory/chords-as-cents-above-root.md`.

## Notes

- Blocked/open: none yet. See `../vision/` for the latency and tuning constraints
  these tasks must respect.
- Architectural forks that aren't committed live in `../speculations/` (currently:
  the worker-thread audio consumer, topology B).
