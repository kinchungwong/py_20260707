# Policy

Hard **off-limits** — things that are never allowed in this project, full stop,
for safety and user-trust reasons. A policy is a flat "**never do this**,"
independent of any feature, plan, or convenience argument. Recorded here so the
prohibition is explicit and is never relitigated or quietly reintroduced.

## What belongs here

- Absolute prohibitions: APIs, behaviors, or techniques that are banned outright
  (e.g. anything that seizes control of the user's machine — see
  [`input-policy.md`](input-policy.md)).
- The **why** behind each ban, so a future reader understands the reasoning and
  doesn't undo it, plus **what to do instead**.

## What does NOT belong here

- Product direction, goals, and shaping constraints ("keep latency low", "go
  beyond 12-TET") → `../vision/`. Those describe where we're headed; a policy is a
  flat prohibition, not a direction.
- Discovered facts, gotchas, and decisions-in-passing → `../memory/`.
- Implementation strategy → `../plans/`; granular work → `../tasks/`.

## How to use

- One prohibition (or one coherent group) per file, named for the ban.
- State the rule first, in absolute terms, then the rationale, then the sanctioned
  alternative.
- Treat every policy as **settled**. Loosening or removing one is a deliberate act
  that needs the human developer's explicit sign-off — not a casual edit.
