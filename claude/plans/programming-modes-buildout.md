# Plan: programming-modes buildout

**Status: Active** (2026-07-13; promoted from Draft the same day once the blocking
questions were resolved — see "Decisions" below). Sequences the work coming out of the
2026-07-13 discussion (`../discussions/2026-07-13/`). Step 1 is unblocked; only the
melody-spike-scoped Q4 remains open. Not yet decomposed into `../tasks/`.

## Decisions (resolved 2026-07-13)

- **Chord source: save-your-own** (Q1). Build a chord in staged mode, bind it to a
  launcher key. File load/save is a later add.
- **Launcher keys: row-delimited zones** (a). A zone = a contiguous run within one
  keyboard row, given by its leftmost+rightmost key `{row, left, right, role}`, resolved
  against the row order in `gui/qwerty.py` / `layout.py`. v1 ships a **fixed default**
  (bottom row `z–m` = launcher, home+upper rows = note-entry) expressed *through* that
  zone structure, so later reconfiguration is data, not a rewrite. **No config UI yet.**
- **Launcher coexists with live mode** (Q2): saved chords fire in **both** modes
  (generalizes today's `Z`), so the launcher does not replace live mode.
- **Saved chords fire at saved absolute pitch** (b1). On-the-fly chord transposition
  (b2) is parked — a semitone nudge is too blunt for chords; its gesture stays open.
- **Note-window shift redesign is parked**, not gating step 1: the `q`/`\` semitone
  shift breaks the white/black mnemonic (geometry, not a bug). Terminology + the
  isomorphic-geometry option live in
  `../discussions/2026-07-13/note-entry-shift-and-keyboard-geometry.md` →
  `../speculations/isomorphic-hex-keyboard-geometry.md`.
- **Melody mode = a new spike** (Q3): it needs a bar/timeline display pane plus a
  details text area — a whole UI surface, too much to bolt onto the current spike.
- **Shared machinery: lift opportunistically** (Q5): promote code to
  `focused-spikes/shared/` as it stabilizes during the current spike, rather than
  designing the shared layer up front.

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
   **each launcher-zone key auto-plays a saved chord** (save-your-own; default zone =
   bottom row `z–m`; fires in both live and staged modes; saved chords play at saved
   absolute pitch). Deliver as the next iteration of the existing spike; it needs no
   mouse work, so it gives the fastest "does this feel right?" signal. Pin the demo to
   **12-TET** (JI conflicts with the semitone shift — see the discussion / graduate to
   `../memory/musictheory/`). Leave the note-window shift as-is (redesign is parked).
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

## Open questions

Q1, Q2, Q3, Q5 and sub-questions (a)/(b) are **resolved** — see "Decisions" above.
Remaining:

4. **Timing model** for melody base notes: grid/transport vs. free-then-edited?
   Deferred until the melody spike (5) starts — not blocking near-term work.

Parked (own docs, not gating this plan): on-the-fly chord transpose gesture (b2);
the note-window shift redesign / keyboard geometry
(`../speculations/isomorphic-hex-keyboard-geometry.md`).

## Deferred — needs planning + architecture review

- **Stored-chord visibility surface** (surfaced by the 2026-07-13 chord-launcher eval): a
  mini-map / display pane to see saved chords and *correct mistakes* (e.g. fix one wrong
  note in a 6-note chord), which also subsumes the one-line-toast HUD limitation. Blocked on
  a **UI-pane-modularization refactor** — the current spike UI wasn't designed for modular
  panes — so it needs its own planning + architecture review before implementation. Overlaps
  with the melody-editor's WYSIWYG (step 5), which also needs display panes; the refactor
  should serve both. **Do not start without that review.**
