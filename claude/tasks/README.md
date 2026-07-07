# Tasks

Active, granular, **checkable work items** — the short-lived layer. Tasks are the
atomic steps a [plan](../plans/README.md) decomposes into.

## What belongs here

- Concrete TODOs scoped small enough to finish in one sitting.
- Their current state (todo / in-progress / done / blocked) and any blockers.
- Just enough context to act without re-reading the whole plan — but link back to
  the parent plan for the full picture.

## What does NOT belong here

- The strategy the tasks implement → `../plans/`
- Long-term intent → `../vision/`
- Durable facts and decisions worth remembering after the task is closed → `../memory/`

## How to use

- Keep it current. A stale task list is worse than none.
- Either one file per active workstream (`current.md`) with a checklist, or one file
  per task for larger items — pick the lightest thing that works.
- When a task teaches something durable (a gotcha, a decision, a constraint),
  record that in `../memory/` before closing the task, then check it off.
- Prune or archive finished tasks so the folder reflects what's actually live.
