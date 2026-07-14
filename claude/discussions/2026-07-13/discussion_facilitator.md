# Discussion facilitator — 2026-07-13

*Agenda + parking lot for the 2026-07-13 forward-looking talk. Not a decision, not a
plan. Builds directly on the 2026-07-10 keyboard/input discussion.*

## Framing

The 2026-07-11 human eval of the staged-chord-entry spike, plus a further round of
hands-on use, sharpened one thing: the computer keyboard's **simultaneity ceiling**
(`../2026-07-10/keyboard-and-input-surface.md`) is not something more key *bindings*
can fix. That reframes the roadmap around **programming-style entry modes** rather
than trying to make QWERTY a playable polyphonic surface.

## Topics captured today

1. [`chord-launcher-and-programming-modes.md`](chord-launcher-and-programming-modes.md)
   — the decision to lean hard into **one-key-to-many (chord launcher)**; the framing
   that staged entry is just **one of several programming modes**; and **mouse as a
   first-class input**, not just HUD buttons.
2. [`melody-editing-mode.md`](melody-editing-mode.md) — a **second** programming mode:
   hunt-and-peck base-note entry (press-duration), then a WYSIWYG mouse editor for
   per-note properties. Previously only a germ in the spike README "Finding".
3. [`note-entry-shift-and-keyboard-geometry.md`](note-entry-shift-and-keyboard-geometry.md)
   — the `q`/`\` semitone shift breaks the white/black row mnemonic; research pins the
   terminology (diatonic transpose + circle-of-fifths vs. pitch bend) and opens the
   keyboard-geometry question. Graduated one part into a speculation.

## Parking lot (raised, not resolved today)

- **Velocity** — no input path and no hardware right now; derive-from-timing vs.
  set-in-WYSIWYG. See `melody-editing-mode.md` and `../../retrospectives/2026-07-10-b.md`.
- **JI vs. the semitone-shift feature** — they conflict; the current demo must stay
  12-TET. This is a music-theory decision that should graduate to
  `../../memory/musictheory/` rather than live only here.
- Still-open items from the 2026-07-11 eval not yet placed: chord-history HUD with
  mouse recall; the melody-contour realization (now → `melody-editing-mode.md`).

## Where today's threads are heading

Both topics graduate toward a **Draft plan**:
[`../../plans/programming-modes-buildout.md`](../../plans/programming-modes-buildout.md),
which sequences the work and its dependencies.
