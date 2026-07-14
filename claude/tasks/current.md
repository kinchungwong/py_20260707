# Current tasks

> **Milestone:** the library-promotion arc (increments 1–4) is complete, committed, and
> human-tested. Collapsed record: [`done.md`](done.md) · as-built plan:
> [`../plans/library-promotion.md`](../plans/library-promotion.md).

## Active

**Focused spike — staged-chord-entry** — chord launcher + press-duration built and
feel-evaluated; at a **resting point** pending the chord-editing surface.
[`../../focused-spikes/staged-chord-entry/README.md`](../../focused-spikes/staged-chord-entry/README.md)
· status: [`status_active.md`](../../focused-spikes/staged-chord-entry/status_active.md).

- **v1 (the minimal `Z`-slice) is delivered and human-tested** — the 2026-07-11 eval plus
  the 3-octave / slidable-window follow-up. The eval's feedback and a further round of use
  produced a design direction, now captured in the 2026-07-13 discussion and an **Active**
  plan: [`../plans/programming-modes-buildout.md`](../plans/programming-modes-buildout.md).
- **Steps 1–2 built and feel-evaluated (2026-07-13):**
  - **Chord launcher** — save-your-own chords across the `z–m` zone (Save → next empty slot;
    fires in both modes at saved pitch; Shift+key forgets). Sidecar:
    **[`chord-launcher.md`](chord-launcher.md)**.
  - **Press-duration** — one idiom, *short = trial, long = commit*: staged note keys
    tap = audition / hold = stage; space short = audition the chord (kept) / long = play +
    clear. Threshold 0.20 s confirmed good enough live. Sidecar:
    **[`press-duration.md`](press-duration.md)**.
  Both tested headlessly (selftest green, piano + sine) and in live sessions; the user's
  verdict is positive ("good enough, nothing to complain about"). Findings + parked tweaks
  (e.g. the ~1.5 s staged-note-duration idea) are in the spike README "Finding".
- **Editing saved chords — the stored-chord visibility / editing surface** is now folded
  into the **UI pane modularization** work, **sequenced as plan step 5 (F), a new spike
  between C and D** (re-scoped 2026-07-14). The architecture review is now the first task of
  that step, not a gate before it. It is NOT part of the current `staged-chord-entry`
  spike — see the plan's "Sequenced (was deferred)" section and "Scope boundary".
- **Step 3 — mouse hit-test core — built + selftest green (2026-07-14).** Sidecar:
  **[`mouse-hit-test.md`](mouse-hit-test.md)**. New `hittest.py`: a coarse-to-fine
  `(region, gadget)` resolver (`Region` StrEnum + `RegionSpec` + `pick`) unifying `Hud.hit`
  + the library `gui.hit_test`; `MOUSEBUTTONDOWN` routes through it. **Foundational — no
  behaviour change** (HUD acts as before; piano-key hits resolve to a no-op seam). Piano +
  sine selftest green, `run_spike_tests.py` 14/14.
- **Step 4 — mouse in staged mode (C) — built + selftest green (2026-07-14), pending the
  human gate.** Sidecar: **[`mouse-in-staged.md`](mouse-in-staged.md)**. Fills step 3's
  `Region.KEYBOARD` seam via the `mouse_input` glissando drag model: **live** = sustained
  router play (down/drag/empty/up); **staged** = audition on button-down, stage on
  button-up iff the gesture ends on the down-key (drag away cancels), Shift+click
  toggles/forgets. Launcher-slot clicking deferred to F (Save/Play/Release stay on HUD
  buttons). Piano + sine green, `run_spike_tests.py` 14/14, mypy + pyright clean, doc-links
  OK. **C is the last work in scope for this spike;** it now awaits the human gate — manual
  test on a real device + manual review, then commit (see
  [`../memory/process/c-review-and-merge-handoff.md`](../memory/process/c-review-and-merge-handoff.md)).
  The per-key-type press-duration reliability check on real hardware also remains open.

**v1 decisions that still hold** (still in force): audition via
the `pygame.mixer` one-shot sine behind `_audition()`; commit path = fire-and-forget
note-ons on the `EventQueue` (`sounder_id = midi`, bypass the router, no note-off) ringing
out on natural decay, focus-loss silences them; spike-owned `clock.tick(60)`, no edits to
`src/`. **Superseded:** the "ONE preset slot (`Z`)" scope → now the `z–m` launcher zone.

Bootstrap infrastructure (unchanged, still relevant): the library isn't pip-installed
(src-layout), so `src/` goes on `sys.path` via `focused-spikes/shared/bootstrap.py`
(`ensure_library_on_path()`); each spike keeps only a tiny walk-up-to-`shared/` preamble.

## Backlog / deferred

- **Plan sequence** (see the plan for the dependency shape): press-duration (2) → mouse
  hit-test core (3) → **mouse in staged mode (4, C — next; last step in the current spike)**
  → **UI pane modularization (5, F — NEW spike; includes the stored-chord visibility surface)**
  → **melody-editing mode (6, D — NEW spike; bar/timeline pane + details area)**. In scope
  for `staged-chord-entry` = through step 4 only; steps 5–6 are new spikes. Q4 (melody
  timing model) stays open, scoped to step 6.
- **Focused-spike candidate — just-intonation color:** derive cents from frequency ratios
  (e.g. neutral third 11/9 ≈ 347.4c) instead of a fixed cent grid. Note: JI conflicts with
  the note-window semitone shift, so the *current* demo stays 12-TET (see the plan).
- **Microtonal / isomorphic layout** — now parked as a speculation with a revisit trigger:
  [`../speculations/isomorphic-hex-keyboard-geometry.md`](../speculations/isomorphic-hex-keyboard-geometry.md).
  Still a future-spike candidate when microtonal live play becomes a goal.
- **Library refinement:** crossfade voice-stealing (kill the small steal artifact the piano
  voice adds) + reclaim held-but-fully-decayed voice slots.

## Notes

- **Spikes location (2026-07-10):** exploratory spikes live at project-level
  [`../../focused-spikes/`](../../focused-spikes/README.md); the legacy `../spikes/` is
  frozen (pre-milestone-1, read-only).
- **Speculations (now two):** the worker-thread audio consumer (topology B) and the
  isomorphic-hex keyboard geometry — both in
  [`../speculations/`](../speculations/README.md).
- **Blocked/open:** nothing blocks the chord launcher. See
  [`../vision/`](../vision/README.md) for the latency/tuning constraints all tasks respect.
