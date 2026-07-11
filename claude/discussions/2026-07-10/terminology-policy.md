# Topic: terminology policy — reuse real words, explain them for newbies

*A discussion note: current knowledge + open questions. Not a decision, not a plan.*

## The policy (2026-07-10)

**Reuse existing terminology wherever it exists.** Don't invent a parallel, in-house
vocabulary when a real term already names the concept — that's the fast path to a
private Babel that isolates the project from the practitioners (musicians, synth users,
programmers) who already have a working shared language.

This is already how tonight's session actually operated, not just an aspiration: the
vocabulary gathered in `keyboard-and-input-surface.md` — **voicing, chord mode, Hold /
Latch, step entry, quasimode, rolled chord** — was assembled specifically by finding
what musicians and interaction designers already call these ideas, rather than naming
them ourselves. This topic file names that practice as a **policy**, going forward.

## The newbie clause

Reusing real terms does **not** mean assuming the audience already knows them — see
`audience-and-accessibility.md`. The move is: **use the correct, established word, and
explain it in place**, not skip it and not replace it with a simplified made-up
substitute. A newbie who learns "quasimode" from us has learned something true and
transferable; a newbie who learns our invented substitute has learned nothing outside
this project.

## A same-project reuse, not just a music-world one (2026-07-10)

The staged-entry sketch's "release" button (see `keyboard-and-input-surface.md`) reuses
a term that isn't just generic musician vocabulary — it's already a first-class stage
name in this project's own synth core: the envelope state machine is literally
`IDLE → ATTACK → SUSTAIN → RELEASE → IDLE`
(`../../memory/acoustics/realtime-gate-envelope.md`). Reusing "release" for "let go of
the pending/staged notes" costs nothing new to learn for anyone who later reads the
DSP code — the policy pays off *within* the project, not only against the outside
world.

## Where this already applies, and where it's still open

- **Keyboard/input** — done in practice already; the standing vocabulary list in
  `keyboard-and-input-surface.md` is the precedent to keep extending.
- **Microtonality** — terms like **cents, Just Intonation, EDO (equal division of the
  octave), ratio, isomorphic layout** are already established (some already appear in
  `../../memory/musictheory/chords-as-cents-above-root.md`) and should stay as-is, with
  newbie glosses layered on, not renamed for simplicity.
- **Pedagogy** — arguably the primary consumer of this policy: a "term introduced +
  explained the first time it's used" approach (or an actual glossary) could become a
  concrete technique in the teaching product itself, not just an internal convention.

## Open questions

- **Where do the explanations live?** In-UI tooltips, a glossary page, inline in the
  pedagogical text, some combination? See `ui-affordance-and-feedback.md`.
- **What happens when traditions disagree?** Jazz, classical, and electronic-music
  circles sometimes use different words for close ideas. Do we pick one and note the
  alternates, or let context decide?
- Is there a *lightweight* way to keep a running glossary as the project's own
  vocabulary grows, without it becoming a maintenance burden?
