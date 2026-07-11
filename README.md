# py_20260707

Python interactive piano GUI project.

## Basic design

Allows user to play a piano by mouse or keyboard.

The sound of each piano note is rendered on demand, with overtones, inharmonicity, decay, sustain, and initial phase randomization.

This is the initial plan. Later, the app needs to be extended to microtonal, not limited to 12-TET; in fact, it may go beyond equal-division-of-octaves (EDO) and may go beyond the piano string model. As the sound rendering model advances, the architecture will need to keep up.

Due to the inherent interactivity, we would like to keep the delay between user input and sound playback small, but we recognize that the particular choice of Python and PyGame may pose inherent limits. All tradeoffs are negotiable, but ultimately the human user must personally evaluate the application and approve.

## Project vital information

- Python environment: the repo-root `.venv`. Always run code via `.venv/bin/python`,
  never a bare `python`/`python3` — see
  [`claude/policy/locating_python_environment.md`](claude/policy/locating_python_environment.md).
- Platform: Linux only, via PyGame
- Interactivity: PyGame + Python sounddevice
    - (Note) Some demo scripts may be terminal with and without interactivity
- Computation: NumPy
    - (Future) NumPy + Python multiprocessing
- Tests: pytest
- Other dependencies:
    - sortedcontainers
    - cffi

## Working with Claude

The `claude/` directory (no leading dot) holds human-readable, version-controlled
project knowledge that both the developer and Claude curate. It layers from
long-lived intent down to short-lived work — each folder has its own `README.md`:

- [`claude/vision/`](claude/vision/README.md) — the enduring **why** and where we're
  going: north-star goals, architectural principles, hard constraints. Changes rarely.
- [`claude/policy/`](claude/policy/README.md) — hard **off-limits**: things that are
  never allowed, full stop, for safety and user-trust reasons. Absolute prohibitions,
  kept explicit so they're never relitigated or quietly reintroduced.
- [`claude/plans/`](claude/plans/README.md) — concrete **implementation plans** for
  specific features or milestones; the bridge from vision to tasks.
- [`claude/speculations/`](claude/speculations/README.md) — **architectural speculations**:
  directions we've considered but not committed to, parked with a revisit trigger so
  we don't re-derive or relitigate them later.
- [`claude/spikes/`](claude/spikes/README.md) — one-off, throwaway **experiments** to
  verify how something works or sketch a design before committing to it.
- [`claude/tasks/`](claude/tasks/README.md) — active, granular, **checkable work items**
  that a plan decomposes into. Kept current and pruned.
- [`claude/memory/`](claude/memory/README.md) — cumulative **facts and decisions**
  discovered along the way: rationale, gotchas, conventions. Grows, rarely deleted.
- [`claude/retrospectives/`](claude/retrospectives/README.md) — **session retrospectives**:
  a dated entry per working session — what changed, what was decided, and where the
  next session should pick up.
- [`claude/discussions/`](claude/discussions/README.md) — open-ended **discussions** of
  future directions, captured by date before they crystallize into vision, plans, or
  spikes; the forward-looking counterpart to retrospectives. *(New — conventions still
  settling.)*
- [`claude/ui-designs/`](claude/ui-designs/README.md) — concrete, captured **interaction
  and interface designs**: detailed enough to build from later, but not yet a committed
  plan. Sits between a discussion and a plan. *(New — conventions still settling.)*

This is separate from `.claude/` (the Claude Code harness config) and from Claude's
own private memory store.
