# Step 4 (C) review→merge workflow, and F resuming from main

The agreed process around **mouse-in-staged (C)** and the handoff to **UI pane
modularization (F)** — stated by the user 2026-07-14.

1. Wire up **C** (mouse in staged mode) — the last work in the `staged-chord-entry` spike.
2. C counts as done only after **all four**: **self-tested** (`--selftest` green),
   **manually tested** by the user, **manually reviewed** by the user, and **git committed**.
3. Then the **user** (their side, not the assistant): pushes to GitHub, opens a PR,
   approves it, and **merges to main**.
4. **F resumes on a FRESH branch cut from main** — not a continuation of the current
   feature branch.

## Implications for the assistant

- **Do not push / open PRs / merge** — the user does all of that (consistent with the
  standing "push is disabled" constraint). Stop at a local commit.
- C's definition-of-done includes a **human manual-test + manual-review gate**: after
  `--selftest` is green, hand C off for the user's testing/review rather than treating
  self-test as sufficient.
- After C is merged, expect a **branch change** — do not pile F work onto the current
  branch; F starts from `main` on a new branch.

See `../../plans/programming-modes-buildout.md` (Scope boundary + sequence) and
[[mouse-hit-test-piano]] (the drag model C reuses).
