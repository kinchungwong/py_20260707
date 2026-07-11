# Topic: audience — designing for newbies, everywhere

*A discussion note: current knowledge + open questions. Not a decision, not a plan.*

## The audience, stated plainly (2026-07-10)

Two overlapping newbie populations, one guiding rule: **assume no prior skill, in
either direction.**

- **UI/app users** may have **little to no training playing any musical instrument at
  all** — not "a beginner pianist," genuinely never played anything.
- **Pedagogical-product users** (see `pedagogical-products.md`) may have **little to no
  programming experience, and/or music theory, and/or acoustics** knowledge.

We will **not assume a demanded skill level** for either population, because the actual
audience might have none of it.

## What this implies for design

Newbies make mistakes — especially in **live** interaction with a UI. So:

- **Low-friction.** Nothing should require prior knowledge just to attempt.
- **Forgiving.** Mistakes should be recoverable, not punished — no dead ends, no
  "start over" states.
- **Easy to correct.** Fixing a mistake should be at least as easy as making it.

This is a direct constraint on decisions elsewhere in this discussion. For example, the
**persistent-mode risk** raised in `keyboard-and-input-surface.md` (a "true mode
toggle" commit gesture can produce a **mode error** — acting as if in one mode while
actually in another) is *exactly* the kind of newbie-hostile trap this principle warns
against: a newbie has no accumulated muscle memory to catch the error, so either the
gesture needs to be self-cancelling (a **quasimode**), or the modality needs to be made
unmissable — see `ui-affordance-and-feedback.md`.

## Connections to the other topics

- **Keyboard/input** (`keyboard-and-input-surface.md`) — every commit-gesture and
  chord-mode idea there should be re-read through this lens: does a newbie's *first,
  clumsy* attempt fail safely?
- **Pedagogy** (`pedagogical-products.md`) — extends "newbie" beyond "newbie at
  coding": the finished app the student ends up with should *also* be forgiving to
  play, not only easy to build. The teaching journey and the playing experience share
  one audience.
- **Microtonality** (`microtonality.md`) — a non-12-TET UI is unfamiliar even to
  *trained* musicians; for a newbie it doubles the unfamiliarity, so this principle
  applies with extra force there.
- **Terminology** (`terminology-policy.md`) and **UI affordance**
  (`ui-affordance-and-feedback.md`) are the two concrete mechanisms this session
  identified for actually satisfying "low-friction, forgiving, no assumed skill."

## Open questions

- What does "easy to correct" mean concretely for a *live, real-time* instrument (as
  opposed to a document you can undo)? Is there an instrument-appropriate analog of
  undo?
- Where's the line between "forgiving" and "so lenient it stops meaning anything" (e.g.
  a chord-timing tolerance window so wide it swallows intentional separate notes)?
- Do the two newbie populations (player vs. builder) ever pull the design in opposite
  directions, and if so, where?
