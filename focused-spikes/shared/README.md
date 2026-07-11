# focused-spikes / shared

Utility code shared across more than one focused spike — the **one sanctioned place** a
focused spike may depend on code it does not own. Everything else in `focused-spikes/` is
a self-contained spike that must survive being moved (the relocatability rule in the parent
`focused-spikes/README.md`); `shared/` is the pressure-release valve that keeps that rule
from making genuine reuse impossible.

## Why it exists

A focused spike must be **relocatable** — you can move it (say, mark it archived, or regroup
it by topic) without breaking it. A relative peer-import between two spikes (`../other-spike/…`)
is exactly the coupling that breaks that: move either side and it snaps. So when two spikes
need the same helper, the answer is not "import across" — it's "hoist it here." `shared/`
turns a fragile horizontal dependency between leaves into a stable vertical one on a common
trunk, the same shape as depending on the promoted library `pypiano_2607`.

## What belongs here

- A helper, fixture, test harness, or reference datum used by **two or more** focused spikes.
- Code general enough that copying it into each spike would be worse than sharing it.

## What does NOT belong here

- Anything only one spike uses → it lives inside that spike. Self-contained is the default;
  `shared/` is the deliberate exception, not the first resort.
- A dependency on any spike. `shared/` is a trunk, and a trunk that imports a leaf is a cycle
  waiting to happen. It may import only the promoted library (`pypiano_2607`), the standard
  library, and third-party packages from the environment — **never** a spike.
- Promotable, maintained library code → that graduates to `src/pypiano_2607/`, not here.

## Rules that keep it honest

- **Not a spike.** `shared/` carries no `status_active.md` / `status_archived.md` marker — it
  is infrastructure, on a different axis from a spike's lifecycle.
- **Inlined on harden.** When a spike is hardened for extraction (e.g. toward a pedagogical
  product), whatever it uses from `shared/` is **copied into that spike**, so the extractable
  artifact stands alone. `shared/` is a convenience for live work, not a permanent dependency
  the archived tier leans on.

## Status

Empty by design. Nothing is shared until a **second** spike actually needs it — don't build
the trunk before there are two leaves. This README exists now as the policy anchor and a
stable link target, not because there is code to document yet.
