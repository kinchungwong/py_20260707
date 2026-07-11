# Done

Collapsed record of finished work — **one line per item, plus a pointer** to where the
detail lives (plan / retrospective / memory). The finished counterpart to
[`current.md`](current.md). **Rule: collapse, don't copy** — when a task closes it becomes a
line here, never a paragraph. Everything below is also in git history.

## Library-promotion arc → `pypiano_2607`  (2026-07-09 → 07-10, committed `2be5011`)

As-built plan: [`../plans/library-promotion.md`](../plans/library-promotion.md) ·
milestone retrospective: [`../retrospectives/2026-07-10-d.md`](../retrospectives/2026-07-10-d.md)

- Increment 1 — synth core (config / pitch / events / queue / audio) into `src/`.
- Increment 2 — input layer (`InputRouter`, `gui/keyboard`, `gui/qwerty`).
- Increment 3 — the app (`PianoApp` + `MouseGlissando`, the full live chain).
- Increment 4 — Just Intonation as an option (`tuning.py`, `--tuning ji --tonic`).

## Pre-library exploratory spikes  (2026-07-09 → 07-10)

Frozen (legacy) in [`../spikes/`](../spikes/README.md) · lessons distilled into
[`../memory/`](../memory/README.md)

- Synthesis — chord synth, microtonal triads, FFT plots, pull-model audio, streaming piano voice.
- Interactive GUI — static keyboard, kbd/mouse input, input integration, event queue,
  realtime envelope, polyphony, playable_instrument, input→sound latency.
