# Current tasks

> **Milestone:** the library-promotion arc (increments 1–4) is complete, committed, and
> human-tested. Collapsed record: [`done.md`](done.md) · as-built plan:
> [`../plans/library-promotion.md`](../plans/library-promotion.md). This file is back to
> **live tasks only**.

## Active

*(Nothing active yet.)* Next up is the first **focused spike**, staged-chord-entry
([`../../focused-spikes/`](../../focused-spikes/README.md)); its tasks land here — or inside
the spike, per the tasks-location convention we settle — once the minimal slice is pinned.

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
