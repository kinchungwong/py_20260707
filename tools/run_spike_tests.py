#!/usr/bin/env python3
"""
Run every spike's headless self-check, to catch regressions without a display.

The spikes don't share one uniform entry point -- GUI spikes assert via
``--selftest``, the audio spikes render silently via ``--no-play``, and a couple
have no safe headless mode -- so the invocations are listed explicitly below (a
spike with no headless mode is listed under SKIP, with the reason). Each check
runs with the SDL dummy drivers so pygame needs no display, from the repo root so
the spikes' ``claude/spikes/*.png`` output paths resolve. FAILS (exit 1) if any
check returns non-zero.

Modes in the report:
    selftest  runs the spike's --selftest, which makes assertions (the real net)
    render    runs the widget/plot renderer; passes if it renders without error
    smoke     runs the audio spike with --no-play; passes if it doesn't crash

Usage:
    python tools/run_spike_tests.py            # run all checks
    python tools/run_spike_tests.py -k input   # only spikes whose filename matches
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from _repo import repo_root

SPIKES_DIR = "claude/spikes"
HEADLESS_ENV = {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
TIMEOUT_S = 120

# Ordered on purpose: the chord/triad spikes write the .wav files that fft_plots
# reads, so they must run before it. Each entry: (spike, argv, mode).
CHECKS = [
    ("keyboard_static_display.py", ["--selftest"], "selftest"),
    ("kbd_input.py",               ["--selftest"], "selftest"),
    ("mouse_input.py",             ["--selftest"], "selftest"),
    ("input_integration.py",       ["--selftest"], "selftest"),
    ("event_queue.py",             ["--selftest"], "selftest"),
    ("realtime_envelope_release.py", ["--selftest"], "selftest"),
    ("piano_keyboard.py",          [],             "render"),
    ("piano_chord_major_minor.py", ["--no-play"],  "smoke"),
    ("microtonal_triads.py",       ["--no-play"],  "smoke"),
    ("fft_plots.py",               [],             "smoke"),
]

# Spikes with no safe headless mode (documented so the gap is explicit, not silent).
SKIP = [
    ("outputstream_callback.py", "opens a real audio output device for ~5 s"),
]


def _last_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def run_check(root: str, spike: str, argv: list[str]) -> tuple[bool, str]:
    """Run one spike headlessly. Returns (passed, one-line summary)."""
    path = os.path.join(root, SPIKES_DIR, spike)
    if not os.path.isfile(path):
        return False, "spike file not found"
    try:
        proc = subprocess.run(
            [sys.executable, path, *argv],
            cwd=root, env={**os.environ, **HEADLESS_ENV},
            capture_output=True, text=True, timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {TIMEOUT_S}s"
    if proc.returncode == 0:
        return True, _last_line(proc.stdout)
    return False, _last_line(proc.stderr) or _last_line(proc.stdout) or f"exit {proc.returncode}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-k", metavar="SUBSTR", default="",
                    help="only run spikes whose filename contains SUBSTR")
    args = ap.parse_args(argv)

    root = repo_root()
    failures = 0
    ran = 0

    for spike, spike_argv, mode in CHECKS:
        if args.k and args.k not in spike:
            continue
        ran += 1
        passed, summary = run_check(root, spike, spike_argv)
        status = "PASS" if passed else "FAIL"
        print(f"{status}  [{mode:8}] {spike:30} {summary}")
        if not passed:
            failures += 1

    if not args.k:
        for spike, reason in SKIP:
            print(f"SKIP  [{'':8}] {spike:30} {reason}")

    print(f"\n{ran - failures}/{ran} checks passed"
          + (f", {failures} FAILED" if failures else "."))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
