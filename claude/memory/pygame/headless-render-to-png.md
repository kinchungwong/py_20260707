# Verify a PyGame spike headlessly by rendering the surface to PNG

PyGame GUI spikes can be **drawn and checked with no display and no human** —
proven by the first GUI spike (`../../spikes/keyboard_static_display.py`). Use this
to verify geometry/layout in headless or agent-driven runs, the same way the
matplotlib Agg trick handles plots (see [[headless-png]]).

## The two rules

1. Set the SDL dummy drivers **before** the video subsystem comes up — i.e. before
   `pygame.display.set_mode(...)`:
   ```python
   import os
   os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
   os.environ.setdefault("SDL_AUDIODRIVER", "dummy")   # avoids needing an audio device
   import pygame
   pygame.init()
   screen = pygame.display.set_mode((W, H))
   ```
   Setting them *after* `set_mode` has no effect — the driver is already chosen.
2. Draw normally, then capture the surface with
   `pygame.image.save(screen, "out.png")`. Drawing to the surface works fully under
   the dummy driver; only *presenting to a real display* is stubbed out. So the
   PNG is a faithful picture of what a real window would show.

## Why it's genuinely headless (verified)

- With `SDL_VIDEODRIVER=dummy`, `pygame.init()` / `set_mode` / `draw.*` all succeed
  with no X/Wayland and no window; `image.save` produces a valid PNG.
- The static-keyboard spike rendered its two-octave keyboard this way and the PNG
  showed the correct 2-then-3 black-key grouping — layout bugs would be visible.

## Patterns worth reusing

- Give the spike a `--selftest` flag that sets the dummy drivers, draws one frame,
  posts a synthetic quit event (`pygame.event.post(Event(KEYDOWN, key=K_ESCAPE))`),
  and exits — so the init/draw/quit path runs in CI without blocking on input.
- A **static** display should loop on `pygame.event.wait()` (blocks, 0% CPU idle),
  not a busy poll. Animated/interactive spikes need a polled, clock-driven loop.

## Limits

- This checks *rendering and logic*, not real windowing: an actual window + a real
  keypress still needs a display and a human. Good enough to catch geometry/layout
  and event-handling bugs; not a substitute for one interactive run.

## Env facts (as of 2026-07-09)

- `pygame` 2.6.1 (SDL 2.28.4), Python 3.13 in the project venv.
