# The instrument's end-to-end signal chain (topology A, closed)

The canonical data path of the playable instrument, first wired whole by the
`playable_instrument` spike (`../../spikes/playable_instrument.py`). This is the
map; each stage has its own detail memory (linked below).

```
 keyboard / mouse            InputRouter              EventQueue            PolySynth               sounddevice
 (PyGame events) ─events──▶  merge+dedup ─NoteEvent─▶ lock-free ─drain────▶ pool + envelope ─mix──▶ OutputStream
        GUI THREAD (producer)                         deque                 tanh limiter            AUDIO THREAD (consumer)
        └──────────────── push ────────────────────▶  │  ◀──── drain each block ──────────────────────┘
                                                (the only thing shared across the two threads)
```

## The stages

1. **Input → note transitions.** PyGame key/mouse events go through one
   `InputRouter`, which reference-counts each note by holder-set and emits a single
   reconciled note-on/off stream tagged by source. [[note-event-reconciliation]]
2. **Cross the thread boundary.** Emitted `NoteEvent`s are pushed onto the
   `EventQueue` (a lock-free, non-blocking `deque`). The GUI thread is the
   producer; the audio callback is the consumer. [[event-queue]]
3. **Voice the notes.** Each block the audio callback drains the queue, allocates
   / steals voices, and renders summed polyphony. [[polyphony-voice-pool]]
4. **Envelope + oscillator per voice.** Phase-continuous sine × a gate envelope
   with click-free attack/release. [[realtime-gate-envelope]]  (Timbre to layer on:
   [[piano-note-synthesis-recipe]].)
5. **Out.** `tanh`-limited mono mix written into the `OutputStream` callback's
   `outdata`, honoring the `frames` it asks for. [[blocksize]]

## Non-obvious integration facts

- **Two threads, one lock-free deque, no other shared state.** The GUI thread
  never blocks pushing; the audio thread never blocks draining. `pygame.event.wait()`
  keeps the GUI thread at 0% CPU while idle without starving audio (separate thread).
- **Everything reused unmodified.** The whole instrument = the four modules above
  + ~30 lines of glue (route each router transition to BOTH the queue and a key
  repaint). This composability is the return on the shared-`piano_keyboard` widget
  and the enum-tagged `NoteEvent` vocabulary.
- **Focus-loss ⇒ all-notes-off**, never a cursor grab: on `WINDOWFOCUSLOST`, push a
  note-off per held note and reset the router. The sanctioned response from
  `../../policy/input-policy.md`.
- The `perf_counter()` stamp captured when the router emits a `NoteEvent` rides the
  whole chain unchanged — it's what `input_to_sound_latency` will measure against.

## Status / next

- Committed **topology A** (callback drains directly); topology B parked
  (`../../speculations/audio-consumer-worker-thread.md`).
- Pitch is 12-TET / MIDI here; microtonal is deferred (`microtonal_layout`).
- **Not yet measured:** keypress→audible-onset latency (`input_to_sound_latency`),
  which needs exactly this wired path.
- This chain is the seed of the real app; promoting it out of `spikes/` into a
  tested module is the natural structural step (with the synth-module work).
