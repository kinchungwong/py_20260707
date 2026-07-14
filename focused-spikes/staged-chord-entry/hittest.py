"""Coarse-to-fine mouse hit-test core (plan step 3 / dependency B).

The spike grew three separate point->gadget hit-tests: the HUD's `Hud.hit` (buttons ->
action string), the library's `gui.hit_test` (piano keys -> midi), and — not built —
launcher slots. The 2026-07-11 eval asked for ONE coarse-to-fine scaffolding underneath
them all, so a click resolves to `(region, gadget)` across the whole window: coarse (which
screen region) then fine (which gadget in it).

This module is JUST that resolver — pure geometry + delegation, no display, no app state,
no mouse *behaviour* (wiring clicks to audition/stage is step 4). It is deliberately tiny
and self-contained so it lifts to `focused-spikes/shared/` unchanged once the melody spike
(step 5 / D) needs it.

Model:
  * `Region`      — a region's *identity* (an enum.StrEnum: HUD, KEYBOARD, ...). The only
                    thing called "Region"; the identity name is used consistently.
  * `RegionSpec`  — `(region, rect, resolve)`: the identity, its coarse bounding box, and
                    `resolve(pos) -> payload | None` (the region's own fine hit-test).
  * `pick`        — walk the specs topmost-first; the FIRST whose coarse rect contains the
                    point claims it (opaque — no fall-through) and returns
                    `(region, resolve(pos))`. A `None` payload means "hit this region's
                    background" (HUD padding, a 1-px gap between keys).

Opaqueness and topmost-first are not load-bearing yet (today's coarse rects are y-disjoint),
but they are the rules a real pane stack needs, so the core commits to them now — the
deferred pane-modularization refactor inherits a resolver that already behaves correctly
when panes overlap.
"""
from __future__ import annotations

import enum
from typing import Callable, Protocol

Pos = tuple[int, int]
Payload = object  # region-specific: an action string (HUD), a midi int (keyboard), ...


class CollidePoint(Protocol):
    """The one slice of `pygame.Rect` this core uses: a point-in-rect test. Typing the
    coarse box structurally (not as `pygame.Rect`) keeps the module pygame-free while still
    giving an IDE / mypy a real shape to check against — unlike a bare `object`. Any
    `pygame.Rect` satisfies it (its `collidepoint` accepts a single `(x, y)` point)."""

    def collidepoint(self, pos: Pos, /) -> bool: ...


class Region(enum.StrEnum):
    """The identity of a coarse screen region. String-valued (project preference) so it
    prints/compares as its name and reads cleanly in logs."""
    HUD = "hud"
    KEYBOARD = "keyboard"


# A region entry: its identity, its coarse bounding box (anything with `collidepoint` — a
# `pygame.Rect` in practice), and its fine hit-test. Structural typing keeps this pygame-free.
RegionSpec = tuple[Region, CollidePoint, Callable[[Pos], Payload | None]]


def pick(pos: Pos, regions: list[RegionSpec]) -> tuple[Region, Payload | None] | None:
    """Resolve `pos` to `(region, payload)`, or `None` if it is outside every region.

    Coarse-to-fine: walk `regions` topmost-first; the first whose coarse `rect` contains
    `pos` CLAIMS the point (regions are opaque — no fall-through to one behind it) and
    returns `(region, resolve(pos))`. `payload` is that region's fine result and may be
    `None`, meaning the point hit the region's background rather than a gadget.
    """
    for region, rect, resolve in regions:
        if rect.collidepoint(pos):
            return (region, resolve(pos))
    return None
