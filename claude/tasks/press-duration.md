# Task sidecar — press-duration primitive (plan step 2)

Granular checklist for **step 2** of
[`../plans/programming-modes-buildout.md`](../plans/programming-modes-buildout.md).
Parent: [`current.md`](current.md) → Active. Work lands in
`../../focused-spikes/staged-chord-entry/` (no edits to `src/`).

## Status

**Code complete + selftest green (2026-07-13).** Space-bar press-duration works headlessly
(piano + sine): short = audition (keeps staged), long = play + clear, sound on KEYDOWN.
Remaining: **live feel-tuning** of the threshold + the per-key-type check on real hardware,
and the human feel-evaluation. See the open questions (answered) below.

## Scope

Build a **reusable short-vs-long press primitive** and apply it to the **staged-mode space
bar**: short press = **audition** the staged chord without clearing; long press = **play +
clear** (today's behaviour). This is the same idiom the melody mode's Phase-1 entry will
reuse, so build it once and keep it liftable to `focused-spikes/shared/`.

## Grounding (from the code)

- Staged mode currently **ignores KEYUP** (`staged_app.py`: KEYUP handled only in live
  mode); space in staged mode fires `_play_chord` on **KEYDOWN** (fire + clear).
- pygame does not auto-repeat KEYDOWN (no `set_repeat`), so a press = one KEYDOWN + one
  KEYUP — duration is `t_up − t_down`.
- Auditions today are the `pygame.mixer` one-shot (`_audition`); the chord itself fires as
  fire-and-forget note-ons ringing on natural decay.

## Checklist

- [x] **Primitive** — a small `press.py` (`PressTimer`): `key_down(keycode, t)` /
  `key_up(keycode, t) -> "short" | "long" | None`, classified against a configurable
  threshold. **Clock injectable** (takes explicit timestamps) so it is headless-testable.
  Liftable to `shared/` when the melody spike needs it.
- [x] **Wire the space bar (staged mode)** — start handling space KEYUP in staged mode:
  record `t_down` on space KEYDOWN, classify on KEYUP → short = audition (see decision Q1),
  long = `_play_chord` (fire + clear).
- [x] **Threshold** — a named constant with a sensible default; note it needs live tuning
  (feel, per-device). Keep it in one place.
- [ ] **Per-key-type check** (from the 2026-07-13 eval; PENDING real hardware) — confirm KEYUP is reliably
  delivered for space (and note keys, if we extend later); document any key that misbehaves.
- [x] **`--selftest`** — inject controlled timestamps: a short space press auditions and
  **keeps** the staged chord; a long space press fires and **clears** it.
- [x] Run `main.py --selftest` (piano + sine) + `tools/run_spike_tests.py`; update spike
  README controls + `status_active.md`.

## Open design questions (confirm before building)

1. **Space short-press semantics.** Recommended: *short* = fire the staged chord so you hear
   it but **keep it staged** (audition); *long* = fire **and clear** (commit-away). And fire
   the sound on **KEYDOWN** (instant feedback) with the short/long only deciding whether
   staged is cleared on release — audio identical, retention differs. Alternative: fire only
   on KEYUP.
2. **Threshold default** — a feel value needing device tuning (e.g. ~200 ms). Build
   configurable; pick a starting default.
3. **Scope** — space bar only this round; defer note-key press-duration and the melody-mode
   reuse (per plan step 2 focus).

## Out of scope

- Note-key press-duration entry (melody mode / step 5), the visibility surface (deferred,
  needs architecture review), and the parked ~1.5 s staged-note-duration tweak (a separate
  audition-timing fine-tune, tracked in the README "Finding").
