# focused spike — staged chord entry

**Status:** active (see `status_active.md`). The first focused spike.

## The question

Does staged chord entry play like *playing*, or like *programming*? The mechanics are
cheap to build; the real unknown is **feel**. Everything here is scoped to answer that —
not to pick a "best" commit gesture in the abstract.

Origin design: `claude/ui-designs/staged-chord-entry-hud.md`.

## Run

    .venv/bin/python focused-spikes/staged-chord-entry/main.py
    .venv/bin/python focused-spikes/staged-chord-entry/main.py --voice sine
    .venv/bin/python focused-spikes/staged-chord-entry/main.py --tuning ji --tonic A
    .venv/bin/python focused-spikes/staged-chord-entry/main.py --selftest   # headless, no device

Playing needs a real display + output device; `--selftest` opens neither (it drives the
chain headlessly and asserts a committed chord actually sounds and the HUD renders).

## Controls

- **Tab** — toggle live / staged (also the Mode button).
- Live mode: **a s d f g h j k** = white keys C4..C5, **w e t y u** = the black keys —
  press-and-hold to play.
- Staged mode: the same keys **stage** a note (a short sine audition fires); **Shift+key**
  toggles a staged note off ("forget").
- **Space** (staged) — Play chord: fire the staged notes together, then clear.
- **Z** — fire the saved preset (either mode); **Shift+Z** — forget it.
- HUD buttons (mouse): **Play chord**, **Save chord -> Z**, **Release**.
- **Esc** / close window — quit.

Keyboard-first: the mouse drives only the HUD buttons, not the piano keys (v1 scope). The
upper octave is drawn for context but only the lower octave has key bindings.

## What's baked in (spike-simple — the pinned decisions)

- **Feel-test slice, the sketch's shape only**: persistent live⇄staged toggle + explicit
  Play-chord commit; ONE preset slot (`Z`); no quasimode / timeout comparison this round.
- **Audition**: a `pygame.mixer` one-shot sine behind `_audition()` (library-free) — a
  deliberate second acoustic authority. Named debt: consolidate into `PolySynth` at
  graduation (see `status_active.md`).
- **Commit**: staged notes fire as fire-and-forget note-ons minted straight onto the
  `EventQueue` (`sounder_id = midi`, bypassing the router's held-model, no note-off) → they
  ring out on the piano voice's natural decay; focus-loss silences them.
- **Loop**: spike-owned `clock.tick(60)`; composes `pypiano_2607`, no edits to `src/`.

## Files

- `main.py` — entry, arg parsing, `--selftest`, and a short move-safe preamble that reaches
  the `shared/` trunk for the library-path bootstrap (`shared/bootstrap.py`).
- `staged_app.py` — state, mode-aware dispatch, the render loop, library wiring.
- `hud.py` — the HUD strip (pygame-drawn) + multi-state keyboard painting.
- `audition.py` — the `pygame.mixer` one-shot audition (numpy + pygame only).

## Finding

_(To fill after playing it on real hardware: does it feel like playing, or like
programming? Which commit-gesture questions does it settle or reopen?)_
