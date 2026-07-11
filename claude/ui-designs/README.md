# UI designs

Concrete, captured **interaction and interface designs** — detailed enough that a
sketch or a conversation's converged shape doesn't get lost, but not yet a commitment
to build. A design sits between a [discussion](../discussions/README.md) (still open,
many threads at once) and a [plan](../plans/README.md) (a committed implementation
roadmap with increments): it's the point where "here's exactly how this would look and
behave" has been worked out, even if *whether and when* to build it is still undecided.

## What belongs here

- A specific screen, control, or interaction worked out in enough detail to build from
  later: states, controls, gestures, labels, and the reasoning behind non-obvious
  choices.
- Reference source (HTML/CSS/JS, an SVG, whatever medium a sketch used) kept as an
  exact behavioral record — even if it only ran inside a sketching tool and isn't
  standalone-runnable in the real app.
- Decisions made *while* designing it (a button's label, a gesture's scope) and the
  open questions still riding along.

## What does NOT belong here

- Open, many-topic exploration that hasn't converged on a specific design →
  `../discussions/`.
- A committed, staged implementation roadmap (increments, target file structure) →
  `../plans/` — a design graduates here once building it is actually decided.
- An architectural alternative not yet chosen → `../speculations/`.
- The actual, maintained implementation → the real source tree (`src/pypiano_2607/`).

## How to use

- One file per design, named for what it is: `staged-chord-entry-hud.md`, not a date —
  designs are topic-lived, not session-lived.
- Mark a design's status near the top (`Sketch` / `Refined` / `Adopted into a plan` /
  `Superseded`), mirroring how `../plans/` marks status.
- A design is a **living document** while still a sketch — revise it in place as the
  idea is refined, rather than piling up numbered versions, unless a genuinely
  different direction is worth keeping side by side with the original.
- When a design graduates into `../plans/`, keep the design file as the detailed spec
  the plan implements, and link both ways.
- If a design grew out of a `../discussions/` session, link back to the thread it grew
  from, and have that discussion note link forward here — keep the trail intact.
