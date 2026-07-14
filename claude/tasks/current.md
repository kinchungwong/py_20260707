# Current tasks

> **Milestone:** the library-promotion arc (increments 1–4) is complete, committed, and
> human-tested. Collapsed record: [`done.md`](done.md) · as-built plan:
> [`../plans/library-promotion.md`](../plans/library-promotion.md).

## Active

**Focused spike — staged-chord-entry**, now entering its **chord-launcher** iteration.
[`../../focused-spikes/staged-chord-entry/README.md`](../../focused-spikes/staged-chord-entry/README.md)
· status: [`status_active.md`](../../focused-spikes/staged-chord-entry/status_active.md).

- **v1 (the minimal `Z`-slice) is delivered and human-tested** — the 2026-07-11 eval plus
  the 3-octave / slidable-window follow-up. The eval's feedback and a further round of use
  produced a design direction, now captured in the 2026-07-13 discussion and an **Active**
  plan: [`../plans/programming-modes-buildout.md`](../plans/programming-modes-buildout.md).
- **Step 1 (chord launcher) is built and feel-evaluated** — save-your-own chords across the
  `z–m` zone (Save → next empty slot; fires in both modes at saved pitch; Shift+key forgets).
  Tested headlessly (selftest green, piano + sine) and in a live session; the core mechanic
  feels right. Granular checklist: **[`chord-launcher.md`](chord-launcher.md)**. Eval
  follow-ups recorded in the spike README "Finding" (2026-07-13): audition / press-duration
  per-key correctness, a **stored-chord visibility mini-map** (would also subsume the
  one-line-toast HUD limit), and a parked ~1.5 s staged-note-duration tweak.
- **Next:** plan step 2 (press-duration primitive). Sidecar:
  **[`press-duration.md`](press-duration.md)**.
- **Deferred (needs planning + architecture review):** the stored-chord **visibility /
  display surface** from the eval requires a UI-pane-modularization refactor (the spike UI
  wasn't built for modular panes) — see the plan's "Deferred" section. Don't start it
  without that review; it overlaps with the melody-editor WYSIWYG.

**v1 decisions that still hold** (carry into the chord-launcher iteration): audition via
the `pygame.mixer` one-shot sine behind `_audition()`; commit path = fire-and-forget
note-ons on the `EventQueue` (`sounder_id = midi`, bypass the router, no note-off) ringing
out on natural decay, focus-loss silences them; spike-owned `clock.tick(60)`, no edits to
`src/`. **Superseded:** the "ONE preset slot (`Z`)" scope → now the `z–m` launcher zone.

Bootstrap infrastructure (unchanged, still relevant): the library isn't pip-installed
(src-layout), so `src/` goes on `sys.path` via `focused-spikes/shared/bootstrap.py`
(`ensure_library_on_path()`); each spike keeps only a tiny walk-up-to-`shared/` preamble.

## Backlog / deferred

- **Plan steps after the chord launcher** (see the plan for the dependency shape):
  press-duration input primitive (2) → mouse hit-test core (3) → mouse in staged mode (4)
  → **melody-editing mode as a new spike** (5; needs a bar/timeline pane + details area).
  Q4 (melody timing model) stays open, scoped to step 5.
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
