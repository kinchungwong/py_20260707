#!/usr/bin/env python3
"""
Play the promoted pypiano_2607 as a live, interactive GUI piano.

The runnable CLI for the ``PianoApp`` shell (the class lives in ``pypiano_2607.app``;
this is the entry point, mirroring ``examples/play_synth.py`` -- NOT library code).
QWERTY home row = white keys, the row above = black keys; click/drag the mouse too.
Esc or closing the window quits.

Run (from the repo root):
    .venv/bin/python examples/play_app.py                 # piano voice (default)
    .venv/bin/python examples/play_app.py --voice sine    # plain sine voice
    .venv/bin/python examples/play_app.py --selftest      # headless: drive the chain + assert, no device

``--selftest`` opens NO window or device (it sets the SDL dummy drivers, drives the
same ``dispatch()`` the live loop uses with scripted events, and asserts the chain
reconciles + sounds), so it runs in CI / headless. Everything else needs a real
display + output device.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make the src-layout package importable without an install (venv policy: no pip).
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _selftest(voice: str) -> None:
    """Headless: drive the whole GUI->audio chain with scripted PyGame events and a
    hand-driven callback (no window, no device), asserting it sounds + reconciles --
    the acceptance behaviors the frozen playable_instrument spike proved."""
    # Must precede PianoApp() -- its __init__ imports + inits pygame.
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import numpy as np
    from pypiano_2607.app import PianoApp
    from pypiano_2607.config import BLOCK_FRAMES

    app = PianoApp(voice=voice)
    try:
        pygame = app.pygame
        frames = BLOCK_FRAMES

        def drive(n: int) -> float:
            peak = 0.0
            for _ in range(n):
                out = np.zeros((frames, 1), dtype=np.float32)
                app.synth.callback(out, frames, None, None)   # audio thread: drain + render
                peak = max(peak, float(np.abs(out[:, 0]).max()))
            return peak

        def kd(ch):
            app.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.key.key_code(ch)))

        def ku(ch):
            app.dispatch(pygame.event.Event(pygame.KEYUP, key=pygame.key.key_code(ch)))

        def md(pt):
            app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pt, button=1))

        def mu(pt):
            app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pt, button=1))

        g4 = next(k.rect.center for k in app.wk if k.midi == 67)

        # A chord from BOTH sources at once: C4 via keyboard, G4 via mouse.
        kd("a")
        md(g4)
        assert app.router.held == {60, 67}, app.router.held
        peak = drive(20)
        assert app.synth.active_count() == 2, app.synth.active_count()
        assert {s for s in app.synth.voice_sounder if s is not None} == {60, 67}
        assert peak > 0.0, "chain produced no sound"

        # Release both -> voices free.
        ku("a")
        mu(g4)
        assert app.router.held == set(), app.router.held
        drive(40)
        assert app.synth.active_count() == 0

        # Focus-loss all-notes-off: hold a note, drop focus, it must go silent.
        kd("a")
        drive(3)
        assert app.synth.active_count() == 1
        app.dispatch(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        drive(40)
        assert app.synth.active_count() == 0, "focus-loss did not release the held note"

        print(f"selftest OK ({voice}): kbd C4 + mouse G4 -> 2 voices (peak {peak:.3f}); "
              "released -> 0; focus-loss all-notes-off works. No device opened.")
    finally:
        app.close()


def _play(voice: str) -> None:
    from pypiano_2607.app import PianoApp

    print(f"playable ({voice} voice)! home row = white keys, the row above = black keys; "
          "click/drag the mouse too. Esc to quit.")
    app = PianoApp(voice=voice)
    try:
        app.run()
    finally:
        app.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", choices=("piano", "sine"), default="piano",
                    help="timbre (default: piano)")
    ap.add_argument("--selftest", action="store_true",
                    help="headless: drive the chain + assert, open no device/window")
    args = ap.parse_args()
    if args.selftest:
        _selftest(args.voice)
    else:
        _play(args.voice)


if __name__ == "__main__":
    main()
