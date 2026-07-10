# Retrospectives

A dated **log, one entry per working session** — a handoff from each session to the
next (whether the next driver is the human or Claude). A retrospective captures the
*narrative* of a session: what got built, what was decided, where things were left,
and what to watch. It's the "you are here" note you'll wish you had when you sit
back down.

## What belongs here

- One file per session, named by date (`YYYY-MM-DD.md`; add `-b`, `-c`… if a day
  has more than one).
- What was accomplished, the key decisions and *why*, and — most important — the
  **state handoff**: what's next, what's half-done, what's blocked, what to watch.
- Honest "what went well / what to do differently" notes.

## What does NOT belong here

- Durable facts and decisions that outlive the session → `../memory/` (a
  retrospective may *summarize and link* to them, but the canonical fact lives in
  memory).
- Live task state → `../tasks/`.
- Long-term direction → `../vision/`; prohibitions → `../policy/`.

## How to use

- Write it at the **end** of a session, aimed at whoever picks up next.
- Treat entries as an **append-only historical record** — don't rewrite past
  retrospectives to match how things later turned out; they're a log, not a wiki.
- Link out to the tasks, memory, spikes, and decisions the session touched.
