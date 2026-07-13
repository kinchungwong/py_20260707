#!/usr/bin/env python3
"""Run the staged-chord-entry focused spike.

    .venv/bin/python focused-spikes/staged-chord-entry/main.py
    .venv/bin/python focused-spikes/staged-chord-entry/main.py --voice sine --tuning ji --tonic A
    .venv/bin/python focused-spikes/staged-chord-entry/main.py --selftest   # headless, no device

See README.md for the controls and the question this spike asks.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# --- bootstrap: reach the shared/ trunk, then let it put src/ on sys.path ---------------
# pypiano_2607 is a src-layout package NOT installed into the venv (no-pip policy), so every
# active spike needs src/ on sys.path first. That logic lives once in
# focused-spikes/shared/bootstrap.py; here we only walk UP to the dir holding shared/ so we
# can import it -- which works from wherever this spike is moved inside the repo.
for _anchor in Path(__file__).resolve().parents:
    if (_anchor / "shared" / "bootstrap.py").exists():
        if str(_anchor) not in sys.path:
            sys.path.insert(0, str(_anchor))
        break
from shared.bootstrap import ensure_library_on_path  # noqa: E402

ensure_library_on_path()


def _build_tuning(which: str, tonic: str):
    if which == "ji":
        from pypiano_2607.tuning import just_tuning, tonic_to_midi
        return just_tuning(tonic_to_midi(tonic)), f"JI · {tonic}"
    return None, "12-TET"


def _selftest(voice, tuning, label) -> None:
    """Headless: drive the staged->commit loop with scripted events + a hand-driven
    callback (no window, no device), asserting a committed chord actually sounds and that
    the HUD/keyboard render without error."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import numpy as np
    import pygame
    from staged_app import StagedApp
    from pypiano_2607.config import BLOCK_FRAMES

    app = StagedApp(voice=voice, tuning=tuning, tuning_label=label)
    try:
        def drive(n):
            peak = 0.0
            for _ in range(n):
                out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
                app.synth.callback(out, BLOCK_FRAMES, None, None)
                peak = max(peak, float(np.abs(out[:, 0]).max()))
            return peak

        def kd(ch, mod=0):
            app.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.key.key_code(ch), mod=mod))

        def ku(ch):
            app.dispatch(pygame.event.Event(pygame.KEYUP, key=pygame.key.key_code(ch)))

        def special(key, mod=0):
            app.dispatch(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))

        def click(pos):
            app.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))

        app.render()                                   # live-mode HUD draws without error

        # live mode: hold a note -> one voice, then release -> silent
        kd("a")
        assert app.router.held == {60}, app.router.held
        assert drive(6) > 0.0, "live note produced no sound"
        ku("a")
        drive(40)
        assert app.synth.active_count() == 0

        # input window: q/\ re-aim future input; the clamp keeps it on-screen
        assert app.window.offset == 0
        assert app.window.resolve(pygame.key.key_code("a")) == 60
        special(pygame.key.key_code("q"))              # slide down one semitone
        assert app.window.offset == -1
        assert app.window.resolve(pygame.key.key_code("a")) == 59
        for _ in range(40):
            special(pygame.key.key_code("q"))
        assert app.window.offset == -12, app.window.offset      # clamped at the low bound
        for _ in range(60):
            special(pygame.key.key_code("\\"))
        assert app.window.offset == 6, app.window.offset        # clamped at the high bound
        for _ in range(6):
            special(pygame.key.key_code("q"))
        assert app.window.offset == 0

        # re-aim only: a note held across a shift releases the pitch it STARTED at (no stuck note)
        kd("a")                                        # press C4 at offset 0
        assert app.router.held == {60}
        special(pygame.key.key_code("q"))              # slide down WHILE held
        ku("a")                                        # must still off 60, not 59
        drive(40)
        assert app.synth.active_count() == 0, "held note stuck after a mid-hold window shift"
        special(pygame.key.key_code("\\"))             # restore offset 0
        assert app.window.offset == 0

        # two keys landed on ONE pitch by a shift must not cut each other off (router dedups by
        # pitch): the note holds until the LAST of them releases
        kd("d")                                        # press E4 = 64 at offset 0
        assert app.router.held == {64}
        special(pygame.key.key_code("q")); special(pygame.key.key_code("q"))   # offset -2
        kd("t")                                        # 't' now targets 64 too
        assert app.router.held == {64}
        ku("d")                                        # first release must NOT silence 64 ('t' holds it)
        assert app.router.held == {64}, "note dropped while another key still targets it"
        ku("t")                                        # last release lets it go
        drive(40)
        assert app.synth.active_count() == 0, "note not released after the last holder"
        special(pygame.key.key_code("\\")); special(pygame.key.key_code("\\"))  # restore offset 0
        assert app.window.offset == 0

        # staged: stage C-E-G, render, then Play chord -> 3 voices sound, tray cleared
        special(pygame.K_TAB)
        assert app.mode == "staged"
        kd("a"); kd("d"); kd("g")                       # C4 E4 G4
        assert app.staged == [60, 64, 67], app.staged
        app.render()                                   # staged-mode HUD + highlights draw
        special(pygame.K_SPACE)                        # commit
        assert app.staged == [], "staged not cleared after Play chord"
        peak = drive(6)
        assert app.synth.active_count() == 3, app.synth.active_count()
        assert peak > 0.0, "committed chord produced no sound"

        # shift toggles a staged note off (forget), then Save via the HUD button (mouse)
        kd("s"); kd("s", mod=pygame.KMOD_SHIFT)        # stage then un-stage D4
        assert app.staged == [], app.staged
        kd("a"); kd("d"); kd("g")
        click(app.hud.save_rect.center)                # Save chord -> Z
        assert app.preset == [60, 64, 67], app.preset
        assert app.staged == []

        # fire the preset (Z, either mode), then forget it (shift+Z)
        special(app._z_key)
        assert drive(6) > 0.0, "preset fire produced no sound"
        special(app._z_key, mod=pygame.KMOD_SHIFT)
        assert app.preset is None

        # focus loss silences committed/ringing notes
        app.dispatch(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        drive(60)
        assert app.synth.active_count() == 0, "focus-loss did not silence committed notes"

        print(f"selftest OK ({voice}, {label}): live hold, staged C-E-G commit "
              f"(peak {peak:.3f}), forget, save→Z fire, focus-loss all-off, HUD renders. "
              "No device opened.")
    finally:
        app.close()


def _play(voice, tuning, label) -> None:
    from staged_app import StagedApp
    print(f"staged-chord-entry spike ({voice}, {label}). Tab: live/staged, Esc: quit.")
    app = StagedApp(voice=voice, tuning=tuning, tuning_label=label)
    try:
        app.run()
    finally:
        app.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", choices=("piano", "sine"), default="piano",
                    help="timbre (default: piano)")
    ap.add_argument("--tuning", choices=("12tet", "ji"), default="12tet",
                    help="temperament (default: 12tet)")
    ap.add_argument("--tonic", default="C", help="JI tonic/key (only with --tuning ji)")
    ap.add_argument("--selftest", action="store_true",
                    help="headless: drive the chain + assert, open no device/window")
    args = ap.parse_args()

    try:
        tuning, label = _build_tuning(args.tuning, args.tonic)
    except ValueError as e:
        ap.error(str(e))

    (_selftest if args.selftest else _play)(args.voice, tuning, label)


if __name__ == "__main__":
    main()
