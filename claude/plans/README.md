# Plans

Concrete, medium-lived **implementation plans** for specific features or milestones.
A plan is the bridge between the [vision](../vision/README.md) and the individual
[tasks](../tasks/README.md) that carry it out.

## What belongs here

- Step-by-step strategy for building a specific feature (e.g. "microtonal tuning
  support", "sounddevice output pipeline").
- The critical files/modules involved and how they fit together.
- Architectural trade-offs considered, the option chosen, and the reasoning.
- Open questions that must be resolved before or during implementation.

## What does NOT belong here

- The long-term rationale a plan serves → `../vision/`
- The checklist of atomic work the plan decomposes into → `../tasks/`
- Facts learned while executing → `../memory/`

## How to use

- One file per plan, named for the feature: `microtonal-tuning.md`, `note-rendering.md`.
- Write the plan *before* large changes; it's the natural home for output from
  plan mode or the Plan agent.
- Mark a plan's status near the top (`Draft` / `Active` / `Done` / `Superseded`).
  Keep completed plans as a record rather than deleting them.
- When a plan is approved and broken down, spawn the concrete items into `../tasks/`.
