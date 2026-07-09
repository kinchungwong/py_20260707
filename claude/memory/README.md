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
- Group related facts under **1–2 levels of topic subdirectory** to keep the space
  organized as it grows (`sounddevice/outputstream/blocksize.md`). The path itself
  carries the topic, so the leaf filename can be short (`blocksize.md`, not
  `sounddevice-outputstream-blocksize.md`). Keep the nesting shallow — two levels max.
  - **First layer = the domain the fact is *about*** — either a subject area
    (`musictheory/`, `acoustics/`) or the external library/tool it concerns
    (`matplotlib/`, `sounddevice/`, `numpy/`). Ask "what is this fact about?" and
    use that noun. Prefer reusing an existing first-layer folder over minting a
    near-synonym.
  - **Second layer (optional)** narrows within a busy domain (`sounddevice/outputstream/`).
    Only add it once a first-layer folder actually has enough files to warrant it.
  - Cross-links use `[[leaf-name]]` (by slug, not path), so they keep resolving no
    matter which folder a fact lives in — moving a file doesn't break its backlinks.
- Before adding, check for an existing file on the topic and update it rather than
  duplicating. Delete a memory only when it turns out to be wrong.
- Cross-link related memories so a fact leads to its neighbors.
- This is distinct from Claude Code's own harness memory under `.claude/` / the
  agent's private memory store — this folder is human-readable, versioned project
  knowledge that both you and Claude curate.
