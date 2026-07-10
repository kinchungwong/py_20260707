#!/usr/bin/env python3
"""
Validate intra-repo path references across the project's docs and spikes.

Files under `claude/` (plus the root README) link to sibling docs, memory notes,
and spikes by relative path (`../memory/...`) or repo-root path (`claude/...`).
When a file moves or is renamed those links silently rot. This checker resolves
every such reference and FAILS (exit 1) if any is broken -- run it after moving or
renaming files, and in CI.

It can also report *dangling* `[[wikilink]]` slugs (memory cross-links that don't
resolve to a memory note). Per claude/memory/README.md a dangling wikilink is
allowed -- it marks a note worth writing later -- so these are warnings only and
never fail the run.

Scope / limitations:
- Checks two reference shapes: `../...` (resolved against the file's directory)
  and `claude/...` (resolved against the repo root). `.claude/` (the harness dir)
  is intentionally excluded.
- Trailing sentence punctuation (`.`, `)`, `,` ...) is stripped before resolving.
- It does not follow `:line` suffixes or external URLs -- only local paths.

Usage:
    python tools/check_docs_links.py             # check, print report, exit 0/1
    python tools/check_docs_links.py --wikilinks # also list dangling [[wikilinks]]
    python tools/check_docs_links.py --root PATH # override repo root (default: auto)
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass

from _repo import repo_root

# `../foo`, `../../spikes/bar.py` -- resolved against the containing file's dir.
REL_REF = re.compile(r"\.\.(?:/[A-Za-z0-9_.\-]+)+")
# `claude/vision/README.md` -- resolved against the repo root. The lookbehind keeps
# us from matching `.claude/` (harness dir) or a `claude/` embedded in a longer word.
ROOT_REF = re.compile(r"(?<![./\w])claude/[A-Za-z0-9_.\-/]+")
WIKILINK = re.compile(r"\[\[([a-z0-9-]+)\]\]")

# Characters that commonly trail a link inside prose but aren't part of the path.
_TRAILING = ").,;:'\"`"

# Files the checker scans (globs, relative to the repo root).
DOC_GLOBS = ("claude/**/*.md", "claude/**/*.py", "README.md")
# Where memory notes live, for resolving [[wikilink]] slugs.
MEMORY_GLOB = "claude/memory/**/*.md"


@dataclass(frozen=True)
class Ref:
    file: str      # repo-relative path of the file containing the reference
    line: int
    text: str      # the reference as written


def scan_files(root: str) -> list[str]:
    """Repo-relative paths of every doc file to check, sorted and de-duplicated."""
    found: set[str] = set()
    for pattern in DOC_GLOBS:
        for path in glob.glob(os.path.join(root, pattern), recursive=True):
            found.add(os.path.relpath(path, root))
    return sorted(found)


def _resolves(root: str, file_dir: str, ref: str, *, root_relative: bool) -> bool:
    base = root if root_relative else file_dir
    for candidate in (ref, ref.rstrip(_TRAILING)):
        if os.path.exists(os.path.normpath(os.path.join(base, candidate))):
            return True
    return False


def broken_refs(root: str, relpath: str) -> list[Ref]:
    """Every path reference in `relpath` that does not resolve to a file/dir."""
    out: list[Ref] = []
    file_dir = os.path.dirname(os.path.join(root, relpath))
    with open(os.path.join(root, relpath), encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            for m in REL_REF.finditer(line):
                if not _resolves(root, file_dir, m.group(), root_relative=False):
                    out.append(Ref(relpath, lineno, m.group()))
            for m in ROOT_REF.finditer(line):
                if not _resolves(root, file_dir, m.group(), root_relative=True):
                    out.append(Ref(relpath, lineno, m.group()))
    return out


def memory_slugs(root: str) -> set[str]:
    """Leaf names (without .md) of every memory note -- the valid [[wikilink]] targets."""
    return {
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(root, MEMORY_GLOB), recursive=True)
        if os.path.basename(p) != "README.md"
    }


def dangling_wikilinks(root: str, files: list[str]) -> list[Ref]:
    slugs = memory_slugs(root)
    out: list[Ref] = []
    for relpath in files:
        with open(os.path.join(root, relpath), encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                for m in WIKILINK.finditer(line):
                    if m.group(1) not in slugs:
                        out.append(Ref(relpath, lineno, f"[[{m.group(1)}]]"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="repo root (default: auto-detect)")
    ap.add_argument("--wikilinks", action="store_true",
                    help="also report dangling [[wikilinks]] (warnings only)")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root) if args.root else repo_root()
    files = scan_files(root)

    broken = [ref for f in files for ref in broken_refs(root, f)]
    for ref in broken:
        print(f"BROKEN   {ref.file}:{ref.line}  {ref.text}")

    if args.wikilinks:
        for ref in dangling_wikilinks(root, files):
            print(f"dangling {ref.file}:{ref.line}  {ref.text}  "
                  f"(no such memory note -- ok if intentional)")

    if broken:
        print(f"\nFAIL: {len(broken)} broken reference(s) across {len(files)} files.")
        return 1
    print(f"OK: all path references resolve across {len(files)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
