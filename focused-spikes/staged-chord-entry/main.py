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

        def ku_key(key):
            app.dispatch(pygame.event.Event(pygame.KEYUP, key=key))

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

        # staged: stage C-E-G, then exercise SPACE press-duration. Sound fires on KEYDOWN;
        # a SHORT release auditions (keeps staged), a LONG release plays + clears. An injected
        # clock makes the hold durations deterministic (threshold SPACE_LONG_S = 0.20s).
        special(pygame.K_TAB)
        assert app.mode == "staged"
        clock = [0.0]
        app._now = lambda: clock[0]
        kd("a"); kd("d"); kd("g")                       # C4 E4 G4
        assert app.staged == [60, 64, 67], app.staged
        app.render()                                   # staged-mode HUD + highlights draw

        # short space press (0.05s < 0.20s): chord sounds, staged is KEPT
        special(pygame.K_SPACE); clock[0] += 0.05; ku_key(pygame.K_SPACE)
        peak = drive(6)
        assert app.synth.active_count() == 3, app.synth.active_count()
        assert peak > 0.0, "space audition produced no sound"
        assert app.staged == [60, 64, 67], "short space press must keep the staged chord"

        # long space press (0.50s >= 0.20s): plays and CLEARS
        special(pygame.K_SPACE); clock[0] += 0.50; ku_key(pygame.K_SPACE)
        assert app.staged == [], "long space press must clear the staged chord"
        assert drive(6) > 0.0, "long space press produced no sound"

        # shift toggles a staged note off (forget), then Save -> the next empty launcher slot
        kd("s"); kd("s", mod=pygame.KMOD_SHIFT)        # stage then un-stage D4
        assert app.staged == [], app.staged
        kd("a"); kd("d"); kd("g")                       # C4 E4 G4
        click(app.hud.save_rect.center)                # Save -> first empty slot (z)
        assert app.slots[0] == [60, 64, 67], app.slots
        assert app.staged == []

        # a second Save auto-picks the NEXT empty slot (x)
        kd("f"); kd("h")                                # F4 A4
        click(app.hud.save_rect.center)
        assert app.slots[1] == [65, 69], app.slots

        # a launcher key fires its chord in BOTH modes at saved absolute pitch (b1). Test each
        # from silence so the voice count is exact.
        def silence():
            app.dispatch(pygame.event.Event(pygame.WINDOWFOCUSLOST))
            drive(60)
            assert app.synth.active_count() == 0, app.synth.active_count()

        silence()
        assert app.mode == "staged"
        special(pygame.key.key_code("z"))              # slot z fires in STAGED mode
        assert drive(6) > 0.0 and app.synth.active_count() == 3, app.synth.active_count()

        silence()
        special(pygame.K_TAB)
        assert app.mode == "live"
        special(pygame.key.key_code("x"))              # slot x fires in LIVE mode
        assert drive(6) > 0.0 and app.synth.active_count() == 2, app.synth.active_count()

        # forget a slot (shift+z): it clears, and firing it is then silent
        special(pygame.key.key_code("z"), mod=pygame.KMOD_SHIFT)
        assert app.slots[0] is None, app.slots
        silence()
        special(pygame.key.key_code("z"))
        assert drive(6) == 0.0 and app.synth.active_count() == 0, "forgotten slot still fires"

        print(f"selftest OK ({voice}, {label}): live hold, staged C-E-G, space short=audition/"
              f"long=play+clear (peak {peak:.3f}), save->next launcher slot, launcher fires in "
              "both modes, forget clears a slot, focus-loss all-off, HUD renders. No device opened.")
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
