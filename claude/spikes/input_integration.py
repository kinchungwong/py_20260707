#!/usr/bin/env python3
"""
SPIKE: Unify keyboard + mouse into ONE reconciled note-on/off event stream

Question asked
--------------
Fourth GUI spike. The keyboard spike and the mouse spike each produce their own
note-on/note-off actions. Downstream (the audio side) wants a *single* stream of
semantic events, and must not care which input produced them -- nor should it get
a doubled note-on if the same note is triggered by both at once. Can we put one
abstraction in front of both inputs that:
  * emits a single note-on/note-off stream, each event tagged with its source, and
  * reconciles held-state across sources -- a note sounds while >=1 source holds
    it, so overlapping presses collapse to exactly one note-on and one note-off?

Still no sound. The `NoteEvent` stream defined here is exactly what the next spike
(`event_queue`) will push onto the thread-safe queue.

What this does
--------------
`InputRouter` reference-counts each note by the *set of sources* currently holding
it. `press(midi, source)` emits a note-on only on the 0->1 transition; `release`
emits a note-off only on the 1->0 transition; overlapping presses/releases from the
other source return None (no audible change). The emitted `NoteEvent` carries the
source that caused the transition and a `perf_counter()` timestamp.

Both inputs feed the one router in a single window: computer keyboard (a..k /
w e t y u, from kbd_input's map) and mouse glissando (from mouse_input's drag
model). The keyboard highlight reflects the *reconciled* held-set, so a note stays
lit until the last source releases it. The console prints the emitted stream and,
tellingly, the *suppressed* (reconciled) actions.

Finding
-------
- The abstraction that works: `InputRouter` reference-counts each note by the SET
  of sources holding it. note-on fires only on the 0->1 transition, note-off only
  on 1->0; overlapping presses/releases from the other source return None. Verified:
  keyboard + mouse both on C4 -> exactly ONE note-on (keyboard, first down) and ONE
  note-off (mouse, last up). The audio side never sees a doubled note.
- Event vocabulary: ``NoteEvent(kind, midi, source, t)`` -- tagged with the source
  that caused the audible transition and stamped with ``time.perf_counter()``. This
  is exactly the stream the `event_queue` spike will push onto the thread-safe
  queue, and the timestamp is what `input_to_sound_latency` will measure against.
- The keyboard highlight tracks the RECONCILED held-set (``router.held``), so a
  note stays lit until the last source releases it. Confirmed visually (chord from
  two sources; dropping one source leaves the note lit).
- The two inputs stay decoupled: mouse keeps its single-active-note glissando,
  keyboard its multi-held model, and neither knows about the other -- the router is
  the only thing that merges them. Adding a third source (e.g. MIDI) later is just
  another `Source` calling press/release.
- Repaint happens only on emitted events (0->1 / 1->0); reconciled no-ops cost no
  redraw because the key is already in the correct visual state.
- Distilled into ../memory/input/note-event-reconciliation.md.

Run
---
    python claude/spikes/input_integration.py            # real window; play kbd + mouse together
    python claude/spikes/input_integration.py --selftest # headless: router + integration asserts
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from enum import Enum

from piano_keyboard import (
    WIDTH as KB_W, HEIGHT as KB_H,
    note_name, build_keys, render_full, redraw_key, hit_test, offset_keys,
)
from kbd_input import WHITE_QWERTY, BLACK_QWERTY

MARGIN = 24
WIN_W, WIN_H = KB_W + 2 * MARGIN, KB_H + 2 * MARGIN


class Source(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"


class NoteKind(Enum):
    ON = "on"
    OFF = "off"


@dataclass(frozen=True)
class NoteEvent:
    kind: NoteKind     # note-on or note-off
    midi: int
    source: Source     # the source that caused this audible transition
    t: float           # time.perf_counter() when emitted


class InputRouter:
    """Reconciles note presses from multiple sources into one deduplicated
    note-on/note-off stream. A note sounds while >= 1 source holds it.

    press() emits a note-on only on the 0->1 transition; release() emits a
    note-off only on the 1->0 transition; anything else returns None.
    """

    def __init__(self):
        self._holders: dict[int, set[Source]] = {}   # midi -> sources holding it (never empty)

    @property
    def held(self) -> set[int]:
        return set(self._holders)

    def sources(self, midi: int) -> set[Source]:
        return set(self._holders.get(midi, ()))

    def press(self, midi: int, source: Source) -> NoteEvent | None:
        holders = self._holders.get(midi)
        if holders is None:
            self._holders[midi] = {source}
            return NoteEvent(NoteKind.ON, midi, source, time.perf_counter())
        holders.add(source)          # already sounding -> reconciled, no event
        return None

    def release(self, midi: int, source: Source) -> NoteEvent | None:
        holders = self._holders.get(midi)
        if not holders or source not in holders:
            return None              # this source wasn't holding it
        holders.discard(source)
        if not holders:
            del self._holders[midi]
            return NoteEvent(NoteKind.OFF, midi, source, time.perf_counter())
        return None                  # still held by another source -> reconciled


# --- glue: apply a router result to the screen + console + event log ----------

def _apply_press(pygame, screen, state, midi, source, wk, bk):
    router = state["router"]
    ev = router.press(midi, source)
    if ev is not None:
        state["emitted"].append(ev)
        pygame.display.update(redraw_key(screen, ev.midi, wk, bk, router.held))
        print(f"note-on  {note_name(midi):4s} ({source.value})")
    else:
        holders = {s.value for s in router.sources(midi)}
        print(f"  . {source.value} +{note_name(midi)} reconciled (already sounding; holders={holders})")


def _apply_release(pygame, screen, state, midi, source, wk, bk):
    router = state["router"]
    ev = router.release(midi, source)
    if ev is not None:
        state["emitted"].append(ev)
        pygame.display.update(redraw_key(screen, ev.midi, wk, bk, router.held))
        print(f"note-off {note_name(midi):4s} ({source.value})")
    else:
        holders = {s.value for s in router.sources(midi)}
        if holders:
            print(f"  . {source.value} -{note_name(midi)} reconciled (still held; holders={holders})")


def _mouse_to(pygame, screen, state, new_midi, wk, bk):
    """Move the single mouse-driven note to `new_midi` (or None), routing the
    release of the old and the press of the new through the router."""
    old = state["m_note"]
    if new_midi == old:
        return
    if old is not None:
        _apply_release(pygame, screen, state, old, Source.MOUSE, wk, bk)
    if new_midi is not None:
        _apply_press(pygame, screen, state, new_midi, Source.MOUSE, wk, bk)
    state["m_note"] = new_midi


def handle_event(pygame, screen, event, state, wk, bk) -> bool:
    """Dispatch one event through the router. Returns False when we should quit."""
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return False

    key_to_midi = state["key_to_midi"]
    if event.type == pygame.KEYDOWN and event.key in key_to_midi:
        _apply_press(pygame, screen, state, key_to_midi[event.key], Source.KEYBOARD, wk, bk)
    elif event.type == pygame.KEYUP and event.key in key_to_midi:
        _apply_release(pygame, screen, state, key_to_midi[event.key], Source.KEYBOARD, wk, bk)
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        state["m_down"] = True
        _mouse_to(pygame, screen, state, hit_test(event.pos, wk, bk), wk, bk)
    elif event.type == pygame.MOUSEMOTION and state["m_down"]:
        _mouse_to(pygame, screen, state, hit_test(event.pos, wk, bk), wk, bk)
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        state["m_down"] = False
        _mouse_to(pygame, screen, state, None, wk, bk)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless: router unit asserts + integration asserts, save a PNG")
    args = ap.parse_args()

    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("input_integration — keyboard + mouse, Esc to quit")

    white_keys, black_keys = build_keys()
    offset_keys(white_keys + black_keys, MARGIN, MARGIN)
    state = {
        "router": InputRouter(),
        "key_to_midi": {pygame.key.key_code(ch): m for ch, m in WHITE_QWERTY + BLACK_QWERTY},
        "m_down": False,
        "m_note": None,
        "emitted": [],
    }

    render_full(screen, white_keys, black_keys, state["router"].held)
    pygame.display.flip()

    if args.selftest:
        _run_selftest(pygame, screen, state, white_keys, black_keys)
        return

    running = True
    while running:
        event = pygame.event.wait()   # discrete events only -> wait() stays 0% CPU
        running = handle_event(pygame, screen, event, state, white_keys, black_keys)

    pygame.quit()


def _test_router():
    """Pure reconciliation logic -- no pygame needed."""
    r = InputRouter()
    on = r.press(60, Source.KEYBOARD)
    assert on.kind is NoteKind.ON and on.source == Source.KEYBOARD
    assert r.press(60, Source.MOUSE) is None            # overlapping press -> reconciled
    assert r.held == {60}
    assert r.release(60, Source.KEYBOARD) is None        # still held by mouse
    off = r.release(60, Source.MOUSE)
    assert off.kind is NoteKind.OFF and off.source == Source.MOUSE
    assert r.held == set()
    # independent notes from the two sources
    assert r.press(64, Source.KEYBOARD).kind is NoteKind.ON
    assert r.press(67, Source.MOUSE).kind is NoteKind.ON
    assert r.held == {64, 67}
    assert r.release(64, Source.KEYBOARD).kind is NoteKind.OFF
    assert r.release(67, Source.MOUSE).kind is NoteKind.OFF
    # releasing a note nobody holds is a no-op
    assert r.release(99, Source.MOUSE) is None
    print("router OK: overlapping presses reconcile to one on + one off; "
          "independent notes pass through.")


def _run_selftest(pygame, screen, state, wk, bk):
    _test_router()

    def kd(ch): handle_event(pygame, screen,
                             pygame.event.Event(pygame.KEYDOWN, key=pygame.key.key_code(ch)),
                             state, wk, bk)

    def ku(ch): handle_event(pygame, screen,
                             pygame.event.Event(pygame.KEYUP, key=pygame.key.key_code(ch)),
                             state, wk, bk)

    def md(pos): handle_event(pygame, screen,
                              pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1),
                              state, wk, bk)

    def mu(pos): handle_event(pygame, screen,
                              pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1),
                              state, wk, bk)

    router = state["router"]

    # --- Part A: a chord from two different sources at once -------------------
    kd("a")               # C4 via keyboard
    md((174, 254))        # E4 via mouse (lower white region of E4)
    assert router.held == {60, 64}, router.held
    out = "claude/spikes/input_integration_preview.png"
    pygame.image.save(screen, out)      # C4 (keyboard) + E4 (mouse) both lit
    mu((174, 254))
    ku("a")
    assert router.held == set(), router.held

    # --- Part B: SAME note from both sources -> reconciled to one on/off ------
    base = len(state["emitted"])
    kd("a")               # C4 keyboard -> note-on
    md((54, 254))         # C4 mouse    -> reconciled (already sounding)
    ku("a")               # release kbd -> reconciled (mouse still holds)
    assert router.held == {60}, router.held        # still sounding via mouse
    mu((54, 254))         # release mouse -> note-off
    assert router.held == set(), router.held
    part_b = [(e.kind, e.source) for e in state["emitted"][base:]]
    assert part_b == [(NoteKind.ON, Source.KEYBOARD), (NoteKind.OFF, Source.MOUSE)], part_b

    pygame.quit()
    print("integration OK: two sources on C4 produced exactly one note-on "
          "(keyboard, first down) and one note-off (mouse, last up).")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
