"""Shared helpers for the maintenance scripts in tools/."""

from __future__ import annotations

import os


def repo_root(start: str | None = None) -> str:
    """Return the nearest ancestor directory that contains a `.venv/` directory,
    which marks the repo root. Walks up from `start` (default: this file's
    directory), so the tools work regardless of the current working directory.

    Safeguard: the search never ascends to (or past) the current user's home
    directory. The project always lives well below $HOME, so a real root is found
    first; reaching $HOME means `.venv/` is missing, and we fail there rather than
    roam the filesystem (and never mistake a stray `~/.venv` for the repo root)."""
    home_raw = os.path.expanduser("~")                      # str; "~" if HOME unresolved
    home = os.path.abspath(home_raw) if home_raw != "~" else None   # str | None
    d = os.path.abspath(start or os.path.dirname(__file__))
    while True:
        if home is not None and d == home:
            raise SystemExit(
                "tools: reached the home directory without finding .venv/; "
                "refusing to search $HOME or above")
        if os.path.isdir(os.path.join(d, ".venv")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise SystemExit("tools: could not locate repo root (no ancestor has a .venv/ directory)")
        d = parent
