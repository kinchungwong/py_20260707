# Spikes — legacy (pre-milestone-1), frozen

> **Legacy · frozen — read-only reference.** These are the **pre-milestone-1** spikes:
> throwaway experiments from before the library-promotion arc shipped. Their code is
> **frozen** and kept only as a historical record. **Do not add new spikes here, and do not
> modify the experiments.** New exploratory work lives in the project-level
> [`focused-spikes/`](../../focused-spikes/README.md) — self-contained, relocatable spikes
> under their own policy. Everything below is the original pre-freeze intent, preserved for
> the record; it no longer governs current work.

One-off, throwaway **experiments** to answer a question before committing to it.
A spike exists to *learn*, not to ship — its value is the understanding it produces,
not the code it leaves behind.

## What belongs here

- Probes that verify how something actually works
  (e.g. the timing and threading of a `sounddevice.OutputStream` callback,
  what NumPy dtype the buffer really wants, how latency behaves under load).
- Quick prototypes of an architecture or UI decision — "what would it look like if…"
  — built just far enough to judge, then set aside.
- The **finding**: what the experiment taught you, written down so the spike doesn't
  have to be re-run to recover the answer.

## What does NOT belong here

- Production code or anything meant to be maintained → the real source tree.
- The durable conclusion a spike produces, once it informs a real decision →
  record it in [`../memory/`](../memory/README.md) (and link back to the spike).
- The strategy you adopt as a result → [`../plans/`](../plans/README.md).

## How to use

- One self-contained script or small folder per spike, named for the question:
  `sounddevice-callback-timing.py`, `keyboard-latency.py`, `ui-layout-sketch/`.
- Put the takeaway at the top of the file (a comment or a sibling `.md`): the
  question asked, what you observed, and the conclusion. A spike with no recorded
  finding is a spike you'll run twice.
- Spikes are allowed to be messy and are not held to the project's code standards.
- Don't let them rot silently: once a spike has served its purpose, lift its lesson
  into `../memory/` and either delete the spike or keep it clearly marked as an
  archived experiment.
