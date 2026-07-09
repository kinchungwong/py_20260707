#!/usr/bin/env python3
"""
SPIKE: Static piano-keyboard display in PyGame, quit on Esc

Question asked
--------------
First step of the interactive-GUI track: can we open a PyGame window, draw a
recognizable piano keyboard (white + black keys), and cleanly quit on the Esc
key (or the window-close button)? No input mapping, no sound -- just the window,
the draw, and a well-behaved event loop we can build every later GUI spike on.

What this does
--------------
Opens a fixed-size window and draws two octaves of a piano keyboard: white keys
as adjacent rectangles, black keys as the narrower overlaid keys in the correct
C#/D#  F#/G#/A# pattern (no black key at E-F or B-C). Then it waits for events
and exits on Esc or QUIT.

Design choices worth noting:
  * The display is static, so the loop uses ``pygame.event.wait()`` (blocks until
    an event) rather than a busy 60 fps poll -- zero CPU while idle, which is the
    right shape for a static screen. Later interactive spikes that animate will
    switch to a polled clock-driven loop.
  * ``--selftest`` runs the whole thing headless (SDL dummy video/audio drivers):
    it draws one frame, posts a synthetic Esc, and exits -- so the init/draw/quit
    path can be verified without a display or a human. Mirrors the ``--no-play``
    escape hatch in piano_chord_major_minor.py.

Finding
-------
- Works: window opens, the keyboard draws, and it quits on Esc and on the
  window-close (QUIT) event. Verified *visually* -- see keyboard_preview.png
  (gitignored): two octaves with the correct 2-then-3 black-key grouping and the
  gaps at E-F and B-C. 14 white keys, 10 black keys, 840x260.
- ``pygame.event.wait()`` is the right loop for a *static* screen: it blocks
  until an event, so the spike sits at 0% CPU while idle. (Interactive spikes that
  animate will need a polled, clock-driven loop instead.)
- Headless verification technique (reusable for every later PyGame spike, and the
  PyGame analogue of the matplotlib-Agg trick): set ``SDL_VIDEODRIVER=dummy`` (and
  ``SDL_AUDIODRIVER=dummy``) *before* ``set_mode``; drawing still works, and
  ``pygame.image.save(screen, "out.png")`` captures the surface so the visual can
  be checked with no display or human. ``--selftest`` exercises the init/draw/quit
  path this way. Distilled into ../memory/pygame/headless-render-to-png.md.
- Gotcha: the SDL_*_DRIVER env vars must be set before the video subsystem comes
  up (before ``set_mode``); setting them after has no effect.
- Not covered here: verifying a *real* window + a *real* Esc keypress needs an
  actual display -- left to the human runner; the headless render + selftest cover
  the geometry and the quit logic.

Run
---
    python claude/spikes/keyboard_static_display.py            # real window
    python claude/spikes/keyboard_static_display.py --selftest # headless smoke test
"""

from __future__ import annotations

import argparse
import os

# Window geometry.
N_OCTAVES = 2
WHITE_PER_OCTAVE = 7
N_WHITE = N_OCTAVES * WHITE_PER_OCTAVE          # 14 white keys
WHITE_W = 60
WHITE_H = 260
WIDTH = N_WHITE * WHITE_W                        # 840
HEIGHT = WHITE_H
BLACK_W = int(WHITE_W * 0.6)                     # 36
BLACK_H = int(WHITE_H * 0.6)                     # 156

# Within one octave, a black key sits to the RIGHT of these white-key indices:
#   0=C(->C#) 1=D(->D#)  [2=E: none]  3=F(->F#) 4=G(->G#) 5=A(->A#)  [6=B: none]
BLACK_AFTER = (0, 1, 3, 4, 5)

# Colors (R, G, B).
BG = (24, 24, 28)
WHITE_KEY = (238, 238, 234)
BLACK_KEY = (18, 18, 20)
BORDER = (70, 70, 76)


def draw_keyboard(screen) -> None:
    import pygame

    screen.fill(BG)

    # White keys first (they form the base row); black keys overlay on top.
    for i in range(N_WHITE):
        x = i * WHITE_W
        rect = (x, 0, WHITE_W - 1, WHITE_H)   # -1 leaves a thin seam between keys
        pygame.draw.rect(screen, WHITE_KEY, rect)
        pygame.draw.rect(screen, BORDER, rect, width=1)

    # Black keys: centered on the boundary between white key (base) and the next.
    for octave in range(N_OCTAVES):
        for offset in BLACK_AFTER:
            white_index = octave * WHITE_PER_OCTAVE + offset
            boundary_x = (white_index + 1) * WHITE_W
            x = boundary_x - BLACK_W // 2
            pygame.draw.rect(screen, BLACK_KEY, (x, 0, BLACK_W, BLACK_H))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless smoke test: draw one frame, auto-quit, no display")
    args = ap.parse_args()

    if args.selftest:
        # SDL reads these when the video/audio subsystems come up; set before init.
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Static keyboard spike — press Esc to quit")

    draw_keyboard(screen)
    pygame.display.flip()

    if args.selftest:
        # Inject the quit so the blocking wait() returns and we exit cleanly.
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

    running = True
    while running:
        event = pygame.event.wait()     # blocks until something happens (static screen)
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    pygame.quit()
    if args.selftest:
        print(f"selftest OK: {N_WHITE} white keys, "
              f"{N_OCTAVES * len(BLACK_AFTER)} black keys, {WIDTH}x{HEIGHT} window; "
              f"drew one frame and quit on Esc.")


if __name__ == "__main__":
    main()
