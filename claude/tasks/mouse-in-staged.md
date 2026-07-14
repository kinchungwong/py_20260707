# Task sidecar — mouse in staged mode (plan step 4 / dependency C)

Granular record for **step 4 (C)** of
[`../plans/programming-modes-buildout.md`](../plans/programming-modes-buildout.md)
(`[B. mouse hit-test core] → [C. mouse in staged mode] → [F. UI pane modularization]`).
Parent: [`current.md`](current.md) → Active. Work lands in
`../../focused-spikes/staged-chord-entry/` (no edits to `src/`). **C is the last piece in
scope for the `staged-chord-entry` spike** (plan "Scope boundary").

## Status

**Code complete + selftest green (2026-07-14) — pending human manual-test + review.** Fills
step 3's `Region.KEYBOARD` no-op seam: the mouse now drives the piano keys in both modes,
reusing the `mouse_input` glissando drag model (one active mouse note; `MOUSEMOTION` while
down re-hit-tests; `MOUSEBUTTONUP`/empty clears it). Per the review→merge handoff
([`../memory/process/c-review-and-merge-handoff.md`](../memory/process/c-review-and-merge-handoff.md)),
C is done only after **self-test + manual test + manual review + commit** — self-test is
green; the rest is the human gate, so **hand off before committing**.

## Model (as built — the user's spec, 2026-07-14)

- **Live mode = sustained glissando via the router.** `MOUSEBUTTONDOWN` on a key presses it
  (`_press`); dragging onto another key offs the old / ons the new (glissando); dragging
  onto empty space offs it; `MOUSEBUTTONUP` offs it. This is the `mouse_input` drag model
  wired to `InputRouter`, so the mouse is a first-class live-play surface.
- **Staged mode = audition on down, stage on up (same-key), Shift+click toggles.**
  - `MOUSEBUTTONDOWN` on a key **auditions** it (always) and records it as the gesture's
    start key. Dragging **auditions each newly-entered key** (explore), no staging.
  - `MOUSEBUTTONUP` **stages** the start key **iff the gesture ends on that same key** — a
    drag away cancels the stage. (The down-audition already gave feedback.)
  - **Shift+click** is the immediate toggle/forget gesture (`_stage_shift`): un-stages a
    staged note, or stages+auditions an unstaged one — matching Shift+note on the keyboard.
    A shift-click does not also stage on release.
- **No `set_grab`, ever** (`../policy/input-policy.md`). SDL2 implicit capture delivers
  out-of-window motion + the button-up; focus-loss ⇒ all-notes-off (existing) and now also
  clears any in-flight mouse gesture.
- **Launcher-slot clicking stays out of C** (user decision 2026-07-14): Save/Play/Release
  remain mouse-driven via the existing HUD buttons; per-slot click-to-fire / shift-forget
  belongs to the **stored-chord visibility/editing pane in step 5 (F)**.

## Where it lives (`staged_app.py`)

- State (`__init__`): `_mouse_active` (a keyboard gesture is in progress), `_mouse_note`
  (key under the cursor now — sustained in live), `_mouse_down_midi` (key the gesture began
  on — the staged up-stage test). All three cleared in `_all_notes_off`.
- `_key_under(pos)` — the keyboard midi under a point (or `None`) via the step-3 `_hit`.
- `_mouse_to(midi)` — moves the single active mouse note; live = router off-old/on-new,
  staged = audition on entering a key. No-op if unchanged.
- `_mouse_press` / `_mouse_drag` / `_mouse_release` — the three event handlers, routed from
  `dispatch()` (`MOUSEBUTTONDOWN`/`MOUSEMOTION`/`MOUSEBUTTONUP`). `MOUSEBUTTONDOWN` reads
  Shift from `pygame.key.get_mods()` (mouse events carry no `.mod`; the selftest injects
  `mod=`).

## Checklist

- [x] Live-mode glissando over the router (down/drag/empty/up).
- [x] Staged-mode audition-on-down, stage-on-up-if-same-key, drag-away-cancels.
- [x] Shift+click toggle/forget in staged mode (auditions when it stages).
- [x] Focus-loss / mode-toggle clears in-flight mouse state (`_all_notes_off`).
- [x] Launcher-slot clicking deferred to F (Save/Play/Release stay on HUD buttons).
- [x] `--selftest` covers all of the above (live glissando incl. drag-to-empty and back;
  staged click-stages / drag-cancels / drag-out-and-back-stages / shift-toggles). Piano +
  sine green; `tools/run_spike_tests.py` 14/14; mypy + pyright clean; doc-links OK.
- [ ] **Human manual test** (real device/window) — pending.
- [ ] **Human manual review** — pending.
- [ ] **Commit** after the two gates above (then the user pushes / PRs / merges to main; F
  resumes on a fresh branch from main).

## Out of scope (defer)

- **Launcher-slot rects / clickable slots** → step 5 (F), the stored-chord editing pane.
- **UI pane modularization** → step 5 (F), a new spike; do not start here.
- **Editing `src/`** — the library `hit_test` and `InputRouter` are reused as-is.
