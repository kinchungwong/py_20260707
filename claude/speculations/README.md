# Speculations

Architectural directions we've **considered and want to remember, but have not
committed to**. A speculation is a parked "we might do it this way later" — kept
so that when the question comes back around, we revisit it with the original
reasoning intact instead of re-deriving it from scratch.

Speculations are explicitly **not decisions**. Recording one commits us to
nothing; it just refuses to let a good idea (or a known trade-off) evaporate.

## What belongs here

- Alternative architectures or topologies we didn't pick — *yet* — and why they
  might earn their place later.
- "If X gets heavy / if Y stops scaling, we could do Z" ideas.
- Forks we deliberately deferred, with the **condition that would make us revisit**.

## What does NOT belong here

- A strategy we've actually adopted, or the chosen option for a feature being
  built now → `../plans/` (a plan already records *its* considered-and-rejected
  alternatives inline; a speculation is the un-adopted idea that belongs to no
  active plan).
- Enduring direction, or a direction **rejected for good** with the reason → `../vision/`.
- A fact we discovered and verified → `../memory/`.
- Live, checkable work → `../tasks/`.

## How to use

- One speculation per file, named for the idea (`audio-consumer-worker-thread.md`).
- State up front that it's a **speculation, not a committed decision**, and name
  the **committed baseline it's an alternative to** so the contrast is explicit.
- Give the **trigger to revisit** — the observation or threshold that would make
  us reopen the question. A speculation with no revisit condition is just a note.
- A speculation can later **graduate**: into `../plans/` if we adopt it, into
  `../vision/` if we reject it for good, or get validated/killed by a `../spikes/`
  experiment. Cross-link when it moves.
- Cross-reference memory/spikes with a relative link (they live in sibling trees).
