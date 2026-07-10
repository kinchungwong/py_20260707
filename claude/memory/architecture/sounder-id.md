# Note identity = the acoustic object (`sounder_id`), not a key or a pitch

Adopted in the library promotion (increment 1, [[synth-core-library]]). The promoted
`NoteEvent` carries a **`sounder_id`** — an opaque identity for the *acoustic object*
an event addresses — kept SEPARATE from the frequency to sound.

## The idea

Two events that share a `sounder_id` act on the **same** sounding object: a note-on
then a note-off stop that object; a second note-on **retriggers** it. The
`sounder_id` is:

- **not a keyboard key** (a key is just one input that may address it),
- **not a pitch** (the guitar/violin model: one *string* is a single sounder that
  plays a wide range of pitches over its life),
- **not a synth voice** (a `Voice` is a finite pool slot temporarily assigned to
  service a sounder; a steal reassigns the slot, never the identity).

So `NoteEvent` splits what the spikes' `midi: int` conflated into two fields:
`sounder_id` (identity — opaque + hashable) and `freq` (Hz, what the oscillator
needs; `None` on note-off). This split is the seam that lets the synth speak pure
frequency and stay microtonal-ready — **MIDI never enters the audio layer**.

## How the synth uses it

`PolySynth` routes entirely on `sounder_id`: allocation retriggers the voice already
on this sounder, else takes a free voice, else steals the quietest; note-off finds
the voice holding the sounder. It treats the id as opaque — it never assumes it
relates to pitch. Verified in increment 1: a note-off (`freq=None`) never reaches an
oscillator, and a late note-off for a *stolen* sounder is a harmless no-op.

## Who mints ids (input-layer concern)

The **input layer** owns id assignment, and the choice is dictated by the
reconciliation it wants:

- **pitch-slot (the 12-TET keyboard):** `sounder_id = the note's pitch slot` (the
  MIDI number, for now). Keyboard-C4 and mouse-C4 map to the same id ⇒ they
  reconcile to one sounding object — the [[note-event-reconciliation]] behavior.
- **per-press / per-string (future):** a fresh id per gesture, or one-per-string for
  a guitar/violin model, when independent overlapping instances are wanted.

## Related

- The package that introduced it: [[synth-core-library]]; the plan:
  `../../plans/library-promotion.md`.
- Upstream reconciliation that mints ids: [[note-event-reconciliation]].
- The frequency side of the split: [[chords-as-cents-above-root]] (cents/Hz, the
  microtonal source that now slots in upstream of an unchanged synth).
