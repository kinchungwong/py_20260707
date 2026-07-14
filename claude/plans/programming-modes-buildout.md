# Plan: programming-modes buildout

**Status: Draft** (2026-07-13). Sequences the work coming out of the 2026-07-13
discussion (`../discussions/2026-07-13/`). Not yet decomposed into `../tasks/`; several
open questions below must be answered first.

## Goal

Move from "staged-chord-entry, one mode" to a **family of programming-style entry modes**
built on shared machinery, with the **chord launcher** (one key → one saved chord) as the
lead interaction and a **first-class mouse** underneath. Live per-note QWERTY playing is
accepted as a hardware dead end and is **not** a goal.

## Dependency shape (what blocks what)

```
[A. chord launcher]        (independent — can start now)
[B. mouse hit-test core] → [C. mouse in staged mode] → [D. melody mode WYSIWYG]
[E. press-duration input]  (shared by staged space-bar AND melody Phase-1)
```

- **A** is independent of the mouse work — start it first for early feel feedback.
- **B** (coarse-to-fine `collidepoint` scaffolding) gates everything mouse-driven; it is
  the long pole for the melody editor.
- **E** is shared machinery; build it once, reuse in both places.

## Proposed sequence

1. **Chord launcher (staged mode) — the pivot.** Generalize the single `Z` preset into
   **each key auto-plays a saved chord**. Answer open Q1 first (preloaded bank vs.
   save-your-own vs. mix). Deliver as the next iteration of the existing spike; it needs
   no mouse work, so it gives the fastest "does this feel right?" signal. Pin the demo to
   **12-TET** (JI conflicts with the semitone shift — see the discussion / graduate to
   `../memory/musictheory/`).
2. **Press-duration input primitive (E).** Extract short-press-vs-long-press as reusable
   input machinery: staged mode's space bar (short = audition, long = play + clear) and
   the melody mode's Phase-1 entry (short = audition, long = commit) are the **same
   idiom**. Build/measure it once (thresholds are a feel question — needs a real device).
3. **Mouse hit-test core (B).** The coarse-to-fine `collidepoint` scaffolding for
   on-screen gadgets the 2026-07-11 eval flagged. Foundational; no user-visible mode yet.
   Respect the no-grab policy (`../policy/input-policy.md`): focus-loss ⇒ all-notes-off.
4. **Mouse in staged mode (C).** Wire the mouse to piano keys + preset management (not
   just HUD buttons): click to stage/explore chords, manage launcher bindings.
5. **Melody-editing mode (D).** New surface, likely a **new focused spike**. Phase 1:
   hunt-and-peck base-note entry (reuses E), visualized. Phase 2: WYSIWYG editor (needs B)
   — click a base note, edit duration/start-time/chord/volume+velocity. First real
   **velocity** authoring path in the project (no hardware needed).

## Critical files / modules

- `focused-spikes/staged-chord-entry/{staged_app.py, layout.py, hud.py, audition.py}`
  — chord launcher (1), press-duration (2), mouse-in-staged (4) land here.
- A **new focused spike** dir (sibling under `focused-spikes/`) for melody mode (5),
  per the "one directory per exploratory arc" convention
  (`../discussions/2026-07-10/keyboard-and-input-surface.md`).
- `src/pypiano_2607/` stays untouched until a spike graduates; shared machinery
  (press-duration, mouse hit-test, and the audition→`PolySynth` consolidation named in
  the spike `status_active.md`) are graduation candidates, not per-spike-forever.

## Open questions (resolve before decomposing into tasks)

1. **Chord-launcher source model**: preloaded bank vs. save-your-own vs. mix? (Blocks 1.)
2. **Mode relationship**: does the launcher replace live mode or sit beside it? Does
   `q`/`\` transpose whole chords now? (Shapes 1 and 4.)
3. **Melody mode = new spike or extension** of staged-chord-entry? (Shapes 5.)
4. **Timing model** for melody base notes: grid/transport vs. free-then-edited? (Shapes 5.)
5. How much machinery is **genuinely shared** vs. mode-specific (what graduates to `src/`)?
