# focused-spikes

Project-level home for **post-milestone-1** exploratory spikes — a sibling of `claude/`,
deliberately outside it. Where the legacy `claude/spikes/` held one-off *throwaway*
experiments (now frozen), a **focused spike** is built to answer a specific question and is
worth keeping: self-contained, relocatable, and — when it earns it — extractable into
something else (a plan, or a pedagogical product).

This README is also the **index** (bottom) and the one stable inbound address for the whole
tree: link *to here* rather than deep into a spike, because spikes are allowed to move.

## Why "focused" (and not "active" / "new")

The name is an **intrinsic, time-invariant property**: a focused spike was built to target a
specific question, and that stays true whether it is touched today or sits untouched for a
year. A status word (`active`, `working`, `new`) would instead encode a lifecycle
*expectation* — implying the thing owes a next stage and needs tending — which this folder
cannot honor: spikes legitimately linger, sometimes precisely because they are waiting to
become pedagogical products. `focused` also pairs against the legacy set's *throwaway*: those
were not built to be kept; these are.

**This is a durable home, not a work-in-progress queue.** A spike sitting untouched is not
debt or neglect — it may be a candidate biding its time. Do not "clean it up" on sight.

## The core rule: self-contained and relocatable

Each spike is a self-contained subfolder that must survive being **moved** — the *mv test*:

> Move a spike's folder anywhere (archive it, regroup it by topic) and it must still run,
> unchanged.

That is what keeps the internal organization a free decision — we can invent `active/` /
`archived/` groupings, or topic groupings, later and reshuffle at will, at zero code cost.
It is also what makes a spike **portable** — the same property a pedagogical product needs.

What a spike may and may not depend on:

- **The promoted library — yes.** `import pypiano_2607` is fine: it resolves via the
  environment regardless of where the spike sits, so it survives a move.
- **The standard library and third-party packages — yes.** Depending on the `.venv`
  environment is expected; that is not what "self-contained" forbids.
- **Another spike — no, not by relative import.** A relative peer-import (`../other-spike/…`)
  is the one coupling that breaks the mv test. When two spikes need the same helper, hoist it
  into [`shared/`](shared/README.md) instead — a stable vertical dependency in place of a
  fragile horizontal one.

## Status: a marker file, not a parent folder

A spike's status lives in a marker file **inside** the spike, named so the filename carries
the status:

- `status_active.md` — under active work, or deliberately kept live.
- `status_archived.md` — hardened and set aside (see below).

`find focused-spikes -name status_active.md` lists the live set without opening anything.
Status is an **attribute that travels with the spike**, not its position — so a status change
is an edit in place, never a move, and a spike's path stays stable for its whole life. Keep
the marker minimal: a date, and at most one backlink to the origin discussion.

## Hardening, and two tiers of immutability

Archiving a spike is a real step, not just a relabel:

- **Active** spikes are *relocation-safe*: they may lean on `pypiano_2607` and on `shared/`.
- **Archiving** a spike **inlines** those external dependencies — copying in what it used from
  `shared/` (and, if it is headed out of the repo, vendoring the library pieces it needs) — so
  the result is **fully self-contained and extractable**.

That yields a *best-effort* immutability: soft-frozen by convention, not tool-enforced —
distinct from the legacy `claude/spikes/`, whose freeze is hard (`git diff` must stay empty).
Same stability, but here it is earned per-spike, by choice, when a spike is done — not imposed
on the whole tree. **A label alone is not hardening:** flipping the marker to
`status_archived.md` inlines nothing; the inlining is the work.

## Cross-references: address by what survives a move

Because spikes move, reference them by whatever is **invariant under the move**:

- **Inside a spike, pointing within itself** → relative paths (they move together).
- **Inside a spike, pointing out** (to `claude/…` or the library) → repo-root-anchored
  `claude/…`, never `../../…` (whose depth breaks on a move).
- **From the outside world, pointing in** → the fragile direction. Prefer to reference the
  spike *by name through this index* rather than a deep path — this README is the stable
  address a move never changes.

`tools/check_docs_links.py` does not yet scan `focused-spikes/`; adding `focused-spikes/**/*.md`
to its globs would mechanically enforce the rule above. A future option, not done here.

## Layout

```
focused-spikes/
  README.md            # this file — policy + index
  shared/              # opt-in shared utilities (see shared/README.md)
  <topic-name>/        # one focused spike, named for its question
    status_active.md   # minimal status marker
    …                  # self-contained spike contents
```

## Index

*(No focused spikes yet.)* Add one line per spike as it lands — name, the question it
targets, and its status — so this index stays the map of the tree.
