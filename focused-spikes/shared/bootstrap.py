"""Put the src-layout `pypiano_2607` on sys.path without installing it (venv policy: no pip).

Shared by every active focused spike: the library is a src-layout package that is NOT
pip-installed, so a spike needs `<repo>/src` on sys.path before `import pypiano_2607`. That
logic lives here, once, instead of being copied into every spike.

This module SELF-LOCATES: it always lives at `focused-spikes/shared/bootstrap.py`, a fixed
spot under the repo, so it walks UP from its OWN __file__ to the repo root (the dir holding
`src/pypiano_2607`) -- it needs nothing from the caller. A spike only has to get
`focused-spikes/` onto sys.path far enough to import this module, then call
`ensure_library_on_path()`; see any spike's `main.py` for the ~5-line preamble that does so
in a move-safe way (walk up to the dir containing `shared/`).

Stdlib only -- never imports a spike (shared is a trunk; a trunk importing a leaf is a cycle).
"""
from __future__ import annotations

import sys
from pathlib import Path


def ensure_library_on_path() -> None:
    """Idempotently insert `<repo>/src` at the front of sys.path so `import pypiano_2607`
    resolves. Walks up from this file (not the caller) to find the repo root by marker, so
    it is robust no matter where the importing spike sits inside the repo."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "pypiano_2607" / "__init__.py").exists():
            src = str(parent / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            return
    raise SystemExit(
        "could not locate src/pypiano_2607 above focused-spikes/shared/ -- is this still "
        "inside the pypiano repo? (active-tier spikes import the library; extraction vendors.)"
    )
