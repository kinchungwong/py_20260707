# Task sidecar — chord launcher (plan step 1)

Granular checklist for **step 1** of
[`../plans/programming-modes-buildout.md`](../plans/programming-modes-buildout.md).
Parent workstream: [`current.md`](current.md) → Active. All work lands in the existing
spike `../../focused-spikes/staged-chord-entry/` (no edits to `src/`).

## Scope (from the 2026-07-13 decisions)

Generalize the single `Z` preset into **save-your-own chords over a `z–m` launcher zone**,
firing in **both** live and staged modes, at **saved absolute pitch**. Demo stays
**12-TET**; the note-window `q`/`\` shift is left **as-is** (redesign is parked). No config
UI, no file load/save this round.

## Status

**Done — code complete, selftest green, and feel-evaluated (2026-07-13).** The core
mechanic feels right ("interesting chords"). Follow-ups from the eval (audition /
press-duration per-key correctness, a stored-chord **visibility mini-map**, a parked ~1.5 s
staged-note-duration tweak) live in the spike README "Finding". Bind gesture built =
**Save → next empty slot** (per the decision). Next workstream: plan step 2 (press-duration)
and/or the visibility surface.

## Checklist

**Survey (grounding)**
- [x] Read how the current single-`Z` preset is stored, saved, fired, forgotten
  (2026-07-13). Findings: preset = `self.preset: list[int] | None` (`staged_app.py:82`),
  key `_z_key` (`:71`); fire/forget in `dispatch` (`:222–224`) sits **before** the mode
  branch, so `Z` **already fires in both modes**, at **saved absolute pitch** via `_fire`
  (`:94–101`) — b1 already holds. `Save` (`_save_chord :165–173`) is **HUD-mouse-only**,
  hardwired to `Z`. Key map (`layout.py:62–65`) = home + upper rows only; **bottom row
  `x c v b n m` is UNMAPPED, `z` is the sole bottom-row key** → the `z–m` launcher zone is
  essentially free, no collision with note entry. So step 1 is mostly: generalize the one
  slot → a `z…m`-keyed map, and widen the `_z_key` special-case to the whole zone.
- [x] **Design micro-point (decide at build):** how to pick which slot to bind — "Save then
  press a `z–m` key" (transient await-target state) vs. "Save → next empty slot". Save is
  currently mouse-only + hardwired to `Z`.

**Zone model (layout.py)**
- [x] Introduce a zone structure `{row, left_key, right_key, role}` resolved against each
  row's key order; roles: `note-entry`, `launcher`.
- [x] Define the **default zoning**: home + upper rows = `note-entry` (the slidable window
  maps here, unchanged); bottom row `z–m` = `launcher`.
- [x] Ensure `z–m` no longer act as note-entry keys (remove any prior note role on that row).

**Saved-chord data model (staged_app.py)**
- [x] Replace the single-slot preset with a **slot map keyed by launcher key** (`z…m` → a
  chord = set of midi notes), storing absolute pitches. Generalize the current `Z` storage.

**Bind / forget gestures (staged mode)**
- [x] Build-a-chord → **Save** binds the staged chord to a chosen launcher key (press the
  target key to pick the slot, or via the HUD). Overwrites if occupied (save-your-own).
- [x] **Shift + launcher key = forget** (reuse the existing "forget" gesture/word); a
  forgotten slot is simply available again.

**Fire (both modes)**
- [x] Pressing a bound launcher key fires its chord as fire-and-forget note-ons on the
  `EventQueue` (`sounder_id = midi`, saved absolute pitch), in **live and staged** modes.
  Empty slot = no-op. Focus-loss still all-notes-off (`../policy/input-policy.md`).

**HUD**
- [x] Render the `z–m` slot strip: which are bound vs. empty; ideally the bound chord's
  notes. Replace the single `Save chord → Z` affordance with the slot-targeted version.
  - **Known limitation (deferred):** the HUD today has only ONE toast-style `hint` line
    (`hud.py:102`) + one `Z:` line (`:98`) at fixed y-positions in a 200px strip —
    insufficient to show a whole row of 7 launcher slots + status. A HUD layout rework is
    needed; for step 1 do the minimum slot readout and revisit the fuller status area later.

**Verify + document**
- [x] Extend `--selftest` (headless): bind a chord to a launcher key, fire it in **both**
  modes and assert it sounds, then forget it and assert it's gone.
- [x] `.venv/bin/python tools/run_spike_tests.py` stays green; the spike's own selftest passes.
- [x] Update the spike `README.md` controls + `status_active.md` to describe the launcher
  (supersede the single-`Z` description). Record any durable gotcha in `../memory/` before
  checking items off.

## Out of scope / do not touch

- Note-window `q`/`\` shift redesign, pitch bend, keyboard geometry — parked
  (`../speculations/isomorphic-hex-keyboard-geometry.md`).
- On-the-fly chord transposition (b2), file load/save, zone-config UI, mouse-on-piano-keys
  (that's plan steps 3–4), and melody mode (step 5).

## Definition of done

Multiple save-your-own chords bound across the `z–m` zone, each firing correctly in both
live and staged modes at saved pitch, with bind + forget working; selftest + spike-test
green; spike docs updated. Then re-evaluate feel (the spike's actual question).
