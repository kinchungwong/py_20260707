# Topic: a melody-editing mode — base-note contour, then WYSIWYG

*A discussion note: current knowledge + open questions. Not a decision, not a plan. Fills
in a design that previously existed only as a germ in the spike README "Finding".*

## Origin

From the 2026-07-11 eval, a music-newbie realization: when recalling a tune, one recalls
the **melody contour** — the sequence of perceptual **base notes** — not necessarily the
harmony under it (`../../../focused-spikes/staged-chord-entry/README.md`, "Finding"). The
germ there ("audition-commit the base notes, visualize them, then customize each") is now
fleshed out into a distinct **programming mode** (one of the family — see
[`chord-launcher-and-programming-modes.md`](chord-launcher-and-programming-modes.md)).

## The two-phase shape

**Phase 1 — hunt-and-peck base-note entry.** Enter the melody's perceptual **base notes
only**, one at a time, using **press duration** as the intent signal:

- **short press** → *audition* the note (hear it, don't commit) — hunt freely;
- **slightly longer press** → *commit / add* the note to the melody.

Notes land in sequence and are **visualized** as they're entered. This reuses the
**press-duration idiom** already proposed for staged mode's space bar (short = audition,
long = play + clear) — worth noting the recurrence; it may be shared machinery.

**Phase 2 — WYSIWYG editor.** Once the base notes are down, the user **mouse-clicks each
base note** and edits its properties:

- **duration**, **start time**,
- **chord** (harmonize the base note — ties straight into the chord-launcher work),
- **volume / velocity**.

"A bit of WYSIWYG" is an existing project theme
(`../2026-07-10/ui-affordance-and-feedback.md`): what you see represents what will sound.
This mode is a concrete instance of it, and it **depends on the first-class mouse work**
described in the sibling note.

## Velocity — a gap, not a feature yet

There is currently **no way to specify velocity, and no input hardware for it** (recorded
as a deliberate non-feature in `../../retrospectives/2026-07-10-b.md`; "timing → velocity"
was floated in `../2026-07-10/keyboard-and-input-surface.md`). The WYSIWYG editor is a
natural home for **setting velocity by hand** even without a velocity-sensitive
controller — possibly the first real velocity path in the project.

## Open questions

- **Is this a separate spike** from staged-chord-entry, or an extension of it? (It shares
  audition + press-duration + mouse machinery but has a very different surface.)
- **Timing model**: are base notes placed on a grid/transport, or free, with timing set
  later in Phase 2? How does this relate to the "transport / step entry" vocabulary from
  2026-07-10?
- **Contour-first, harmony-later** implies the melody is the spine and chords hang off
  it — does that match how the chord-launcher mode wants to think about chords, or are
  they two different mental models we need to reconcile?
