# py_20260707

Python interactive piano GUI project.

## Basic design

Allows user to play a piano by mouse or keyboard.

The sound of each piano note is rendered on demand, with overtones, inharmonicity, decay, sustain, and initial phase randomization.

This is the initial plan. Later, the app needs to be extended to microtonal, not limited to 12-TET; in fact, it may go beyond equal-division-of-octaves (EDO) and may go beyond the piano string model. As the sound rendering model advances, the architecture will need to keep up.

Due to the inherent interactivity, we would like to keep the delay between user input and sound playback small, but we recognize that the particular choice of Python and PyGame may pose inherent limits. All tradeoffs are negotiable, but ultimately the human user must personally evaluate the application and approve.

## Project vital information

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
- [`claude/plans/`](claude/plans/README.md) — concrete **implementation plans** for
  specific features or milestones; the bridge from vision to tasks.
- [`claude/tasks/`](claude/tasks/README.md) — active, granular, **checkable work items**
  that a plan decomposes into. Kept current and pruned.
- [`claude/memory/`](claude/memory/README.md) — cumulative **facts and decisions**
  discovered along the way: rationale, gotchas, conventions. Grows, rarely deleted.

This is separate from `.claude/` (the Claude Code harness config) and from Claude's
own private memory store.
