# Vision

The enduring **why** and **where we're going**. This is the north star that everything
else in `claude/` should trace back to.

## What belongs here

- Long-term goals and the shape of the finished product.
- Architectural direction and the principles that survive across many features
  (e.g. "keep input-to-sound latency low", "the sound model must generalize beyond
  12-TET and beyond the piano-string model").
- Non-negotiables and hard constraints (platform, key dependencies, user-approval gates).
- Explicitly rejected directions and *why*, so we don't relitigate them.

## What does NOT belong here

- Concrete implementation steps → `../plans/`
- Granular, checkable work items → `../tasks/`
- Discovered facts, gotchas, and decisions-in-passing → `../memory/`

## How to use

- Keep it short and stable. Vision changes rarely; when it does, it's a deliberate act.
- One file per coherent theme is fine (e.g. `sound-model.md`, `latency.md`), or a single
  `overview.md` while the project is small.
- When a plan or task conflicts with vision, the vision wins or the vision is
  consciously updated — never let them silently drift.
