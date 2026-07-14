# Topic: the note-entry shift is broken, and it opens the keyboard-geometry question

*A discussion note: current knowledge + open questions. Not a decision, not a plan.
This thread graduated one part into a speculation (linked below).*

## The problem

The `q`/`\` **semitone shift** of the note-entry window (built into the
staged-chord-entry spike) interacts badly with the piano layout: it slides home-row
keys onto **black** keys and upper-row keys onto **white** keys, which is hard to
use.

**Root cause (not a code bug — geometry):** the mapping is piano-like (home row →
white, upper row → black), but white/black keys don't alternate uniformly — each
octave has two spots (E–F, B–C) where two white keys are adjacent with no black key
between. So the white/black pattern is periodic only at the **octave** (12
semitones), never at 1. Any sub-octave chromatic shift *must* break the
row → colour mnemonic.

## Two viewpoints (user's framing → established terminology)

The user named two distinct axes; research maps both onto standard vocabulary:

1. **"Spatial access"** — quickly reach a key outside the current window. Semitone
   too slow, whole-tone still slow, octave too far; the interval others use is the
   **fifth** (C→G), applied **diatonically** so it stays in key and doesn't add
   accidentals. Established terms:
   - **Diatonic transposition** — move by scale steps, no accidentals, stays in key
     (this is what "doesn't break the WYSIWYG" means: notation stays clean).
   - **Circle of fifths** — the fifth is the *generator* of the 12-tone system, so
     it's the efficient coverage interval (large jump, maximal musical relation).
   - The "shift shouldn't change fingering/appearance" goal is **transpositional
     invariance**.
2. **"Effect"** — a temporary chromatic shift as a sibling of frequency bending,
   *for effect, not as the conceptual music model*. Established term: **pitch bend**
   (temporary, expressive, self-centering) — the textbook opposite of **transpose**
   (a persistent, structural setting). Portamento/glissando/vibrato are the
   continuous cousins.

So the clean model is **two separate controls**: a structural **diatonic transpose**
(the fifth-based "spatial access") and an expressive **pitch bend** (the "effect") —
exactly how MIDI/synth hardware already separates them.

## Where it leads: keyboard geometry is the root variable

The white/black problem isn't fixable by picking a better *step size*; it's a
property of the **layout**. Transpositional invariance, microtonal capability, and
the shift problem are all downstream of geometry (piano → 1D-uniform → 2D-square →
2D-hexagonal isomorphic). Correction worth keeping: invariance is *cheap* (even a 1D
uniform row has it); **hexagonal 2D** is the *optimal* geometry for microtonal live
play, not the *simplest* for invariance.

**Graduated to speculation:**
[`../../speculations/isomorphic-hex-keyboard-geometry.md`](../../speculations/isomorphic-hex-keyboard-geometry.md)
— with a revisit trigger, so we don't re-derive it.

## Open questions

- For the **near-term** demo (still 12-TET piano), is the fix just "swap the
  semitone shift for a **diatonic fifth** transpose", accepting the layout stays
  imperfect — or do we not touch the shift until the geometry question is faced?
- Do we add **pitch bend** as its own control now, or park it with the geometry work?
- The **JI-vs-shift** snag (logged in `chord-launcher-and-programming-modes.md`)
  actually *resolves* under diatonic/scale-degree thinking — worth reconciling when
  geometry is picked up.
