# Memory

Cumulative, durable **facts and decisions** discovered along the way — the project's
long-term notebook. Unlike tasks, memory only grows and is rarely deleted.

## What belongs here

- Decisions and their rationale ("we chose sounddevice over PyGame mixer because …").
- Non-obvious gotchas and constraints (latency quirks, PyGame/NumPy interactions,
  platform-specific behavior).
- Conventions the code doesn't make obvious on its own.
- Pointers to external references (docs, tickets, discussions).

## What does NOT belong here

- Anything the code, tests, or git history already record — don't duplicate them.
  If asked to remember such a thing, capture instead *what was non-obvious about it*.
- Long-term product intent → `../vision/`
- Forward-looking plans → `../plans/`
- Live work items → `../tasks/`

## How to use

- One fact per file keeps recall precise; name files in kebab-case for the fact
  (`sounddevice-latency.md`, `phase-randomization-rationale.md`).
- Before adding, check for an existing file on the topic and update it rather than
  duplicating. Delete a memory only when it turns out to be wrong.
- Cross-link related memories so a fact leads to its neighbors.
- This is distinct from Claude Code's own harness memory under `.claude/` / the
  agent's private memory store — this folder is human-readable, versioned project
  knowledge that both you and Claude curate.
