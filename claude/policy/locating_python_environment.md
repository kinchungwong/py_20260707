# Python environment policy (hard constraint)

**Always invoke this project's Python through the repo-root virtualenv,
`.venv/bin/python`. Never run the project's code (spikes, tools, tests) with a
bare `python` or `python3`.**

The project's dependencies (NumPy, PyGame, sounddevice, sortedcontainers, cffi)
live *only* in `.venv`. Any interpreter outside it is the wrong environment.

## How to locate it

- The virtualenv is a directory named **`.venv` at the repository root** (sibling
  of `README.md` and `claude/`). It contains `bin/python`, `pyvenv.cfg`, and
  `lib/`. Presence of **`.venv/bin/python`** is the marker.
- Run from the repo root and use the relative path: `.venv/bin/python <script>`.
  Examples used in this project:
  - `.venv/bin/python claude/spikes/event_queue.py --selftest`
  - `.venv/bin/python tools/run_spike_tests.py`
- If `.venv/bin/python` is absent, **stop and ask** — do not silently fall back to
  a system interpreter. The environment may need to be created/activated first;
  guessing produces misleading results (see below).

## Why (settled — do not relitigate)

1. **Bare `python` may not exist at all.** On this machine `python` is not on
   `PATH` (`python: command not found`) — only `python3` is, at `/usr/bin/python3`.
   A command that assumes `python` fails outright.
2. **`python3` is the *system* interpreter, not ours.** `/usr/bin/python3` does
   **not** have the project's packages installed. Running a spike or test against
   it fails on import — or, worse, appears to run in a subtly different environment
   and gives results that don't reflect the project. That silent-wrong-answer
   outcome is exactly what this policy exists to prevent.
3. **`.venv` is the single source of truth for the environment.** Pinning every
   invocation to `.venv/bin/python` makes runs reproducible and keeps the
   dependency set honest — no accidental reliance on system-global packages.

## What to do instead

- Prefix every project invocation with `.venv/bin/python` (from the repo root).
- Do **not** rely on the shell's active virtualenv or on `source .venv/bin/activate`
  persisting — shell state does not carry across tool calls here, so name the
  interpreter explicitly each time.
- Need a package that isn't installed? Always talk to the user and let the user
  do it.
