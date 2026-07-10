"""Lock the input layer's two package-level invariants.

1. The **pygame-lazy** invariant — the defining constraint of the input increment:
   importing the package or any input-layer module must NOT pull in pygame (pygame is
   imported lazily, only inside the widget's build/draw functions). This is what keeps
   the library importable headless / in CI. Checked in a fresh subprocess per module,
   because other test modules import pygame into *this* pytest process (which would
   mask an eager import).

2. The ``pypiano_2607.gui`` package re-export surface (``__all__``) actually resolves.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Absolute path to the src-layout root, so the subprocess finds the package with no
# install (pyproject pythonpath=src only applies inside pytest, not a bare subprocess).
_SRC = str(Path(__file__).resolve().parents[1] / "src")

# Every import surface the plan/module docstrings promise stays pygame-free (and, for
# the app, sounddevice-free too -- both are imported lazily inside methods).
LAZY_MODULES = [
    "pypiano_2607",
    "pypiano_2607.router",
    "pypiano_2607.mouse",
    "pypiano_2607.tuning",
    "pypiano_2607.app",
    "pypiano_2607.gui",
    "pypiano_2607.gui.keyboard",
    "pypiano_2607.gui.qwerty",
]


@pytest.mark.parametrize("module", LAZY_MODULES)
def test_import_does_not_load_pygame(module):
    """Importing `module` must not import pygame. Run in a clean subprocess (uses the
    same venv interpreter via sys.executable) so a pygame already loaded by another
    test can't mask an eager import here."""
    code = "\n".join([
        "import sys, importlib",
        f"importlib.import_module({module!r})",
        f"assert 'pygame' not in sys.modules, 'eager pygame import from {module}'",
        f"assert 'sounddevice' not in sys.modules, 'eager sounddevice import from {module}'",
        "print('ok')",
    ])
    env = dict(os.environ, PYTHONPATH=_SRC)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, f"{module}: {result.stderr.strip()}"
    assert result.stdout.strip() == "ok"


def test_gui_reexport_surface_resolves():
    """Every name in `pypiano_2607.gui.__all__` is importable from the package, and the
    load-bearing public names are present."""
    import pypiano_2607.gui as gui

    assert gui.__all__, "gui.__all__ should be non-empty"
    for name in gui.__all__:
        assert hasattr(gui, name), f"gui.__all__ lists {name!r} but it does not resolve"

    for name in ("build_keys", "hit_test", "note_name",
                 "WHITE_QWERTY", "BLACK_QWERTY", "key_to_midi"):
        assert name in gui.__all__, f"{name!r} missing from gui.__all__"
        assert hasattr(gui, name)
    assert callable(gui.build_keys) and callable(gui.hit_test) and callable(gui.key_to_midi)
