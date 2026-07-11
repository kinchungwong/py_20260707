# Discussion facilitator — 2026-07-10

**Meta-theme: the future directions of the project.** Several of them, and **not
mutually exclusive** — the point today is to open the terrain, not to pick a path. This
session is a **pure conversation: no code is written.** This file is the **agenda and
map** so a wide-ranging talk stays navigable and no thread gets lost.

**Where we're standing.** The library-promotion arc is a **completed milestone**: a
fully-playable, tested piano app with 12-TET + 5-limit Just Intonation, human-played on
real hardware. What comes next is **deliberately open** — see the milestone retro,
`../../retrospectives/2026-07-10-d.md`. Today explores that open space; it does not
close it.

**Scope narrowed (2026-07-10, mid-session).** Topic 1 (keyboard/input) turned out to be
where the session's energy actually was — it produced a fully iterated, captured design
(`../../ui-designs/staged-chord-entry-hud.md`). Topics 2 and 3 (pedagogy, microtonality)
are **paused, not abandoned** — deferred to a future discussion session so today could
stay focused on piano UI design. Everything captured under them so far is still valid
starting material.

## The topics on the table

Each has its own note with the current state of knowledge and the open questions. They
**cross-pollinate** — the connections may matter as much as the topics themselves.

1. **The computer keyboard: living with its limits, then going beyond them.**
   Overcoming the hardware rollover/jamming ceiling — and then *supercharging* the
   instrument's expressiveness **despite** (or by sidestepping) the QWERTY surface.
   → `keyboard-and-input-surface.md`
   - Reignite: Do we make QWERTY *playable*, or *transcend* it (keyboard as a command
     surface, pitch expression elsewhere)? What would "supercharge" even mean here?

2. **Paused — Pedagogical products from the project.** Turning what we built — and
   *how* we built it — into a step-by-step, show-by-construction guide for students to
   grow their own project like this, in **smaller ("baby") steps** than we actually
   took. → `pedagogical-products.md`
   - Reignite (next session): Is the lesson *audio programming*, or the *method*
     (spikes → library → app, and the knowledge layers)? Who is the student?

3. **Paused — Microtonality, the deferred frontier.** Novel UI, novel interactions, and
   library-interface changes to make room for non-12-tone instruments — even ones with
   **no discrete tones at all**. The synth core is already frequency-native; the
   12-tone assumptions live at the input/UI edge.
   → `microtonality.md`
   - Reignite (next session): What's the general abstraction for "a thing you can play"
     — a discrete tone set, a continuous pitch field, or both? What's the *first* spike?

## Cross-cutting guidance (added mid-session, 2026-07-10)

Not a fourth direction — **guidance that shapes all three topics above**, prompted by
stepping back to ask *who is this for*. Three short notes, meant to be read alongside
whichever topic is active:

- **Audience.** The audience for everything here is **newbies**, in two overlapping
  senses — UI users with little-to-no instrument-playing background, and pedagogical
  users with little-to-no programming/theory/acoustics background. No assumed skill
  level, in either direction. → `audience-and-accessibility.md`
- **Terminology.** Reuse real, existing terminology rather than inventing a parallel
  vocabulary — but always explain it for the newbie audience rather than assuming it's
  known. (This is what the vocabulary section in `keyboard-and-input-surface.md` was
  already doing, now named as policy.) → `terminology-policy.md`
- **UI affordance.** The display needs to grow to give newbies clues about what's
  possible, and unmissable feedback about what mode is currently active — "a bit of
  WYSIWYG." Directly answers the mode-error risk raised under archetype 5 in
  `keyboard-and-input-surface.md`. → `ui-affordance-and-feedback.md`

## Cross-links worth not losing

- **Keyboard ⇄ microtonality.** A non-12 layout still has to sit on *some* input
  surface, so the QWERTY ceiling constrains any layout mapped onto it. Meanwhile the
  mouse-glissando path already produces **continuous pitch** — a live example of a
  "no-discrete-tones" instrument, and a bridge between both topics.
- **Pedagogy ⇄ everything.** The teaching product is a lens on the whole project;
  alternative input and microtonality are exactly the kind of "next step" a student
  guide could build toward.
- **Audience / terminology / UI-affordance ⇄ everything.** These three aren't a fourth
  topic — they're a lens applied to all three above; see "Cross-cutting guidance."

## Parking lot (things that surface mid-talk)

- _(add as we go — ideas that deserve their own thread but shouldn't derail the current
  one)_

## Session handoff

Session concluded 2026-07-10 — see
[`../../retrospectives/2026-07-10-e.md`](../../retrospectives/2026-07-10-e.md) for the
full handoff and the pre-implementation gap list the next session starts from.

## Ground rules for today (provisional — see `../README.md`)

- Pure conversation; **no code, no spikes** today.
- Capture as we go; let threads stay **open** — record the questions, don't force
  conclusions.
- Standing decisions still hold: **no direction is being chosen or pushed**, and
  anything microtonal beyond JI would **begin as a new spike**, not a library change.
