# Topic: microtonality — the deferred frontier

*A discussion note: current knowledge + open questions. Not a decision, not a plan.*

**Discussion status: paused (2026-07-10).** Today's session narrowed to piano UI design
(see `discussion_facilitator.md`); this thread resumes in a future session. Distinct
from the standing decision below that microtonality *itself* is deferred to a future
spike — this is only about when we next talk about it.

## The standing intent

The vision has always been that **the sound model generalizes beyond 12-TET, and even
beyond the piano-string model** (`../../vision/README.md`). Microtonality is the part of
that intent we consciously **deferred** at the milestone.

## What is already microtonal-ready (the good news)

The synth core was built freq-native precisely so this door stays open
(`../../memory/architecture/synth-core-library.md`):

- **Frequency in, MIDI out of the synth.** `NoteEvent` carries `freq` (Hz); `PolySynth`
  plays `voice.note_on(freq)` directly. **Nothing downstream of the seam knows about 12
  tones** — or about tones being discrete at all.
- **`pitch.py` already holds a general primitive**: `cents_to_hz` sits alongside the
  12-TET `midi_to_freq`. Chords are proven expressible as **cents above a root**
  (`f = root · 2^(cents/1200)`), so an in-between interval like a neutral third comes
  out exact, not "detuned" (`../../memory/musictheory/chords-as-cents-above-root.md`).
- **Just Intonation already ships** as a pluggable `tuning` at the `InputRouter` edge.
- **Mouse glissando already produces continuous pitch** — a live, shipped example of an
  instrument with **no discrete tones**.

So the *engine* is ready. The friction is at the **edge**, where human input becomes
pitch.

## Where the 12-tone assumption actually lives

The framing for today: the 12-tone assumptions "sit at the prime spots of the library
source organization." Concretely they cluster at the **input/UI layer**, not the DSP:

- The **keyboard → note mapping** assumes semitone rows.
- The **on-screen piano** is a 12-per-octave *visual* — white/black key hit-testing
  (`../../memory/pygame/mouse-hit-test-piano.md`).
- **MIDI note numbers / `midi_to_freq`** as the default pitch currency of the input
  path.
- Chord and key **definitions** phrased in 12-TET names.

So the real question isn't "how do we make the synth microtonal" (it already is) — it's
**"how do we generalize the input/UI edge, and the pitch abstraction it mints, without
breaking the shipped 12-TET and JI?"**

## The three things it demands (the axes named for today)

1. **Novel UI.** How do you *show* a non-12 layout? A 19- or 31-EDO keyboard? An
   **isomorphic** grid (Wicki–Hayden, Bosanquet) where one shape = one interval
   everywhere? A **continuous ribbon/strip** with no keys at all?
2. **Novel interactions.** How do you *play* microtones? Continuous drag (we have
   glissando), **snap-to-scale**, pitch-bend, per-key retuning, quantize on/off?
3. **Library-interface changes.** The seam currently mints Hz from *pitch + tuning*. To
   generalize, the **"pitch" concept itself** must generalize — from a MIDI integer
   toward something tuning-system-agnostic (scale degree + tuning? a raw ratio? cents?
   raw Hz? a continuous field?). This is the real design work.

## The frontier case: instruments with no discrete tones

"Beyond discrete tones" isn't hypothetical here — **the mouse-glissando path already is
one.** A question worth chewing on: is the general model a **discrete tone set**, a
**continuous pitch field**, or a **continuum with an optional discretization** (a scale
as a snapping grid laid over a continuum)? That last framing might unify keyboard,
isomorphic, and ribbon instruments under a single abstraction.

## The standing scope rule (binds this discussion)

A settled human decision (milestone retro / app-increment record): **the library
carries Just Intonation only.** Anything else microtonal — non-12-EDO, isomorphic
layouts, ratio-derived JI, continuous instruments — **begins as a NEW spike that
co-develops UI *and* mechanics**, not as a library increment. And the **existing spikes
stay frozen** — don't touch them. So the natural output of this topic is *"what is the
first spike, and what does it try to answer?"* — not a library change.

## Open questions

- What's the right **general abstraction** for "a thing you can play" — discrete set,
  continuous field, or continuum-plus-snapping?
- What is the **first spike**, and what single question should it answer (a 19-EDO
  keyboard? an isomorphic layout? a ribbon that snaps to a chosen scale)?
- How do **UI and mechanics co-develop** inside that spike (the scope rule requires
  both)?
- How does this collide with the **keyboard ceiling**
  (`keyboard-and-input-surface.md`) — any layout mapped onto QWERTY inherits the
  rollover wall.
