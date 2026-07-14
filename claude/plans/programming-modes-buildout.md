# Plan: programming-modes buildout

**Status: Active** (2026-07-13; updated 2026-07-14). Sequences the work coming out of the
2026-07-13 discussion (`../discussions/2026-07-13/`). **Steps 1–4 are built and
selftest-green** (chord launcher, press-duration, mouse hit-test core, mouse in staged mode).
Step 4 (C) is the last piece in scope for the current `staged-chord-entry` spike and is pending the human gate;
everything after C is a **new spike** (see "Scope boundary").
everything after C is a **new spike** (see "Scope boundary"). Decomposed into `../tasks/`
(chord-launcher, press-duration, mouse-hit-test). Only the melody-spike-scoped Q4 stays open.

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

## Scope boundary (2026-07-14)

- **In scope for the current `staged-chord-entry` spike: through step 4 (C) only.** C
  completes the mouse work over the existing gadgets and is the spike's last iteration.
- **Everything after C is a new spike.** Step 5 (UI pane modularization) and step 6 (melody
  mode) each get their own `focused-spikes/` directory; neither extends the current spike.
- Parked / speculative items (note-window redesign, isomorphic geometry, JI color, library
  refinements) remain future-spike candidates, unchanged.

## Dependency shape (what blocks what)

```
[A. chord launcher] (done)
[B. mouse hit-test core] → [C. mouse in staged mode] → [F. UI pane modularization] → [D. melody mode WYSIWYG]
[E. press-duration input]  (shared by staged space-bar AND melody Phase-1)
```

- **A**, **B**, **E** are **done** (steps 1–3, plus A). B (coarse-to-fine `collidepoint`
  scaffolding) was the long pole for everything mouse-driven.
- **C** finishes the current spike — the mouse work over the existing gadgets (fills B's
  `Region.KEYBOARD` seam). Last piece in scope for `staged-chord-entry`.
- **F** (UI pane modularization) is a **new spike inserted between C and D**: the melody
  editor needs a real display surface anyway, which merits doing the pane refactor properly.
  It also delivers the **stored-chord visibility / editing surface**.
- **D** (melody mode) is a **new spike** built on F's panes.

## Proposed sequence

**Progress (2026-07-14):** steps 1–3 built and selftest-green. **Step 4 (C) is next and is
the last step in the current spike;** steps 5–6 are **new spikes** (see "Scope boundary").

1. ✅ **Chord launcher (staged mode) — the pivot.** Generalize the single `Z` preset into
   **each launcher-zone key auto-plays a saved chord** (save-your-own; default zone =
   bottom row `z–m`; fires in both live and staged modes; saved chords play at saved
   absolute pitch). Delivered in the existing spike; pinned to **12-TET** (JI conflicts
   with the semitone shift). Note-window shift left as-is (redesign is parked).
2. ✅ **Press-duration input primitive (E).** Short-press-vs-long-press as reusable input
   machinery: staged mode's space bar (short = audition, long = play + clear) and the
   melody mode's Phase-1 entry (short = audition, long = commit) are the **same idiom**.
   Built once, clock-injectable; threshold is a feel value tuned on device.
3. ✅ **Mouse hit-test core (B).** The coarse-to-fine `collidepoint` scaffolding for
   on-screen gadgets the 2026-07-11 eval flagged. Foundational; no user-visible mode.
   Respects the no-grab policy (`../policy/input-policy.md`): focus-loss ⇒ all-notes-off.
4. **Mouse in staged mode (C) — finishes the current spike.** Wire the mouse to piano keys
   + preset management (not just HUD buttons): click to stage/explore chords, manage
   launcher bindings — reusing the `mouse_input` drag model (one active mouse note,
   glissando, off-on-empty; never `set_grab`). Fills step 3's `Region.KEYBOARD` seam.
   **This is the last work in scope for `staged-chord-entry`.**
5. **UI pane modularization (F) — a NEW spike, between C and D.** The current spike UI
   wasn't built for modular panes; the melody editor (step 6) needs a real display surface
   (bar/timeline + details area), which merits doing this properly rather than bolting it
   on. Deliverable includes the **stored-chord visibility / editing surface** (a mini-map /
   pane to see saved chords and *correct mistakes* — e.g. fix one wrong note in a 6-note
   chord — subsuming today's one-line-toast HUD limit). **Opens with an architecture
   review** (now the first task of this step, not a gate before it). The panes it
   establishes serve **both** the visibility surface and the melody editor.
6. **Melody-editing mode (D) — a NEW spike, on top of F.** Phase 1: hunt-and-peck
   base-note entry (reuses E), visualized. Phase 2: WYSIWYG editor (needs B + F's panes)
   — click a base note, edit duration/start-time/chord/volume+velocity. First real
   **velocity** authoring path in the project (no hardware needed). Opens Q4 (timing model).

## Critical files / modules

- `focused-spikes/staged-chord-entry/{staged_app.py, layout.py, hud.py, hittest.py, audition.py}`
  — chord launcher (1), press-duration (2), mouse hit-test core (3), and mouse-in-staged
  (4) all land here. **Step 4 is the last work in this spike.**
- **New focused-spike dirs** (siblings under `focused-spikes/`), per the "one directory per
  exploratory arc" convention (`../discussions/2026-07-10/keyboard-and-input-surface.md`):
  one for UI pane modularization (5), one for melody mode (6). Steps 5–6 do **not** extend
  `staged-chord-entry`.
- `src/pypiano_2607/` stays untouched until a spike graduates; shared machinery
  (press-duration, the mouse hit-test core `hittest.py`, and the audition→`PolySynth`
  consolidation named in the spike `status_active.md`) are graduation candidates, not
  per-spike-forever.

## Open questions

Q1, Q2, Q3, Q5 and sub-questions (a)/(b) are **resolved** — see "Decisions" above.
Remaining:

4. **Timing model** for melody base notes: grid/transport vs. free-then-edited?
   Deferred until the melody spike (5) starts — not blocking near-term work.

Parked (own docs, not gating this plan): on-the-fly chord transpose gesture (b2);
the note-window shift redesign / keyboard geometry
(`../speculations/isomorphic-hex-keyboard-geometry.md`).

## Sequenced (was deferred): UI pane modularization + stored-chord visibility — step 5 (F)

**Re-scoped 2026-07-14:** previously an open-ended "deferred — do not start" item; now
**sequenced as step 5 (F), a new spike between C and D.** Rationale: the melody editor
(step 6) needs a new display surface regardless, so the pane refactor is worth doing
properly instead of bolting it on — and the same panes deliver the **stored-chord
visibility / editing surface** (surfaced by the 2026-07-13 chord-launcher eval: a mini-map /
pane to see saved chords and *correct mistakes*, e.g. fix one wrong note in a 6-note chord,
subsuming the one-line-toast HUD limit). The **architecture review still happens** — it is
now the **first task of step 5**, not a gate that blocks scheduling it. The panes serve both
the visibility surface and the melody editor, so build them once.
