# Current tasks

> **Milestone:** the library-promotion arc (increments 1–4) is complete, committed, and
> human-tested. Collapsed record: [`done.md`](done.md) · as-built plan:
> [`../plans/library-promotion.md`](../plans/library-promotion.md). This file is back to
> **live tasks only**.

## Active

**Focused spike — staged-chord-entry** (scaffolded 2026-07-10):
[`../../focused-spikes/`](../../focused-spikes/README.md) → `staged-chord-entry/`. The first
focused spike; asks whether staged chord entry plays like *playing* or like *programming*.
Runnable, with a headless `--selftest`; granular checklist + the finding live in the spike's
own `README.md`/`status_active.md` (the hybrid tasks-location convention).

Minimal slice — **now pinned**:
- **Scope:** feel-test slice, the sketch's shape only; ONE preset slot (`Z`); keyboard-first
  (mouse drives only the HUD buttons).
- **Commit gesture:** persistent live⇄staged toggle + explicit Play-chord (space). No
  quasimode / timeout comparison this round.
- **Audition:** lightweight `pygame.mixer` one-shot sine behind `_audition()` — a deliberate,
  documented second acoustic authority; consolidates into `PolySynth` at graduation.
- **Commit path:** staged notes fire as fire-and-forget note-ons on the `EventQueue`
  (`sounder_id = midi`, bypass the router, no note-off) → ring out on natural decay;
  focus-loss silences them.
- **Loop:** spike-owned `clock.tick(60)`; composes the library, no edits to `src/`.

Friction surfaced (and handled): the library isn't pip-installed (src-layout), so `src/` must
go on `sys.path` first. That shim now lives in `focused-spikes/shared/bootstrap.py`
(`ensure_library_on_path()`) — the trunk's first occupant, shared infrastructure every active
spike reuses; each spike keeps only a tiny move-safe walk-up-to-`shared/` preamble. A
relocatable stand-in for the env-resolution the `focused-spikes/` READMEs had assumed (their
dependency bullets are updated to match).

## Backlog / deferred

- **Focused-spike candidate — just-intonation color:** derive cents from frequency ratios
  (e.g. neutral third 11/9 ≈ 347.4c) instead of a fixed cent grid. Microtonal-beyond-JI, so
  it begins as a spike (scope rule).
- **Focused-spike candidate — microtonal layout:** a non-piano / isomorphic layout exposing
  the neutral third etc.
- **Library refinement:** crossfade voice-stealing (kill the small steal artifact the piano
  voice adds) + reclaim held-but-fully-decayed voice slots.

## Notes

- **Spikes have moved (2026-07-10):** new exploratory spikes live at the project-level
  [`focused-spikes/`](../../focused-spikes/README.md) — self-contained, relocatable, with
  in-folder `status_active.md`/`status_archived.md` markers. The now-**legacy** `../spikes/`
  is frozen (pre-milestone-1, read-only reference).
- Blocked/open: none. See [`../vision/`](../vision/README.md) for the latency and tuning
  constraints these tasks must respect.
- Architectural forks that aren't committed live in
  [`../speculations/`](../speculations/README.md) (currently the worker-thread audio
  consumer, topology B).
