#!/usr/bin/env python3
"""
SPIKE: Mouse input -> highlight the clicked/dragged piano key (no audio)

Question asked
--------------
Third GUI spike. Can we hit-test mouse events against the drawn key rects to
highlight and track the pressed key, and handle the awkward cases cleanly:
  * press-then-drag-off a key,
  * drag from one key onto another (glissando),
  * button released *outside* the window?

Model: while the left button is down, at most one mouse-driven note is active --
the key currently under the cursor (or none, over empty space). Moving the cursor
turns the old note off and the new one on; releasing turns the active note off.
This is the glissando behaviour a real touch/mouse instrument wants. No sound yet.

Reuse: the keyboard geometry, drawing, and note naming come from `kbd_input` (this
spike adds only the mouse hit-test + drag state machine). A small **margin** is
added around the keyboard so "drag onto empty space" is exercisable *inside* the
window, not only by leaving it.

Hit-test order matters: black keys are drawn on top of white keys, so they must be
tested FIRST -- a click in the overlap region belongs to the black key.

Finding
-------
- Hit-test order is the crux: **black keys must be tested before white keys**,
  because they're drawn on top and their rects overlap the white ones. Verified
  headlessly -- a point inside both C4's and C#4's rects resolves to C#4.
- Glissando drag works as a clean state machine with a single "active mouse note":
  MOUSEBUTTONDOWN sets it, MOUSEMOTION (while down) switches it (old note-off, new
  note-on), MOUSEBUTTONUP / drag-onto-empty clears it. Verified the full sequence
  press -> onto-black -> onto-white -> onto-margin(off) -> back-on -> release.
- The margin around the keyboard makes "drag onto empty space -> note-off"
  reachable *inside* the window; without it, every in-window point hits some white
  key and drag-off is only possible by leaving the window entirely.
- Button-released-outside-the-window: CONFIRMED fine on Linux/SDL 2.28.4. SDL2
  implicitly captures the mouse while a button is held, so (1) MOUSEMOTION keeps
  arriving with out-of-window coords -> the note turns off the moment the cursor
  leaves the keyboard, and (2) MOUSEBUTTONUP is still delivered on release -> no
  stuck note. ``pygame.event.set_grab(True)`` is NOT needed here -- and is BANNED by
  project policy anyway (../policy/input-policy.md: confining the cursor is off
  limits). For platforms lacking implicit capture, mitigate without grabbing (e.g.
  mouse-leave / focus-loss = all-notes-off). (Manually verified.)
- Reused kbd_input's geometry/drawing wholesale; only hit_test + the drag state
  machine are new. Every remaining GUI spike will want this same keyboard widget
  -- a shared `piano_keyboard.py` helper is starting to look worthwhile.

Run
---
    python claude/spikes/mouse_input.py            # real window; click & drag the keys
    python claude/spikes/mouse_input.py --selftest # headless: simulate drags, save PNG
"""

from __future__ import annotations

import argparse
import os

from kbd_input import (
    build_keys, render_full, redraw_key, note_name,
    WIDTH as KB_W, HEIGHT as KB_H,
)

MARGIN = 24
WIN_W, WIN_H = KB_W + 2 * MARGIN, KB_H + 2 * MARGIN


def hit_test(pos, white_keys, black_keys):
    """MIDI note under `pos`, or None. Black keys first (they sit on top)."""
    for bk in black_keys:
        if bk["rect"].collidepoint(pos):
            return bk["midi"]
    for wk in white_keys:
        if wk["rect"].collidepoint(pos):
            return wk["midi"]
    return None


def _set_active(pygame, screen, state, new_midi, white_keys, black_keys):
    """Make `new_midi` the single active mouse note (or None). Emits note-off for
    the old, note-on for the new, and repaints only the affected keys."""
    if new_midi == state["note"]:
        return
    held = state["held"]
    dirty = []
    old = state["note"]
    if old is not None:
        held.discard(old)
        r = redraw_key(screen, old, white_keys, black_keys, held)
        if r:
            dirty.append(r)
        print(f"note-off {note_name(old):4s} (midi {old})")
    if new_midi is not None:
        held.add(new_midi)
        r = redraw_key(screen, new_midi, white_keys, black_keys, held)
        if r:
            dirty.append(r)
        print(f"note-on  {note_name(new_midi):4s} (midi {new_midi})")
    state["note"] = new_midi
    if dirty:
        pygame.display.update(dirty)


def process_event(pygame, screen, event, state, white_keys, black_keys) -> bool:
    """Handle one event. Returns False when the app should quit."""
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return False

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        state["down"] = True
        _set_active(pygame, screen, state, hit_test(event.pos, white_keys, black_keys),
                    white_keys, black_keys)
    elif event.type == pygame.MOUSEMOTION and state["down"]:
        _set_active(pygame, screen, state, hit_test(event.pos, white_keys, black_keys),
                    white_keys, black_keys)
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        state["down"] = False
        # Clear regardless of cursor position: if this event arrives at all, the
        # note must release. (Whether it arrives when released OUTSIDE the window
        # is platform-dependent -- see finding.)
        _set_active(pygame, screen, state, None, white_keys, black_keys)
    return True


def _offset_into_margin(white_keys, black_keys):
    for k in white_keys + black_keys:
        k["rect"] = k["rect"].move(MARGIN, MARGIN)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless: simulate a drag sequence, save a preview PNG, no display")
    args = ap.parse_args()

    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("mouse_input spike — click & drag the keys, Esc to quit")

    white_keys, black_keys = build_keys()
    _offset_into_margin(white_keys, black_keys)
    state = {"down": False, "note": None, "held": set()}

    render_full(screen, white_keys, black_keys, state["held"])
    pygame.display.flip()

    if args.selftest:
        _run_selftest(pygame, screen, state, white_keys, black_keys)
        return

    running = True
    while running:
        event = pygame.event.wait()   # only react to events (no animation) -> wait() stays 0% CPU
        running = process_event(pygame, screen, event, state, white_keys, black_keys)

    pygame.quit()


def _run_selftest(pygame, screen, state, white_keys, black_keys):
    def step(etype, **attrs):
        ev = pygame.event.Event(etype, **attrs)
        process_event(pygame, screen, ev, state, white_keys, black_keys)

    # --- hit-test ordering (black over white) --------------------------------
    # (80, 90): inside white C4's rect AND inside black C#4's rect -> must be C#4.
    assert hit_test((80, 90), white_keys, black_keys) == 61, "black must win in overlap"
    assert hit_test((54, 254), white_keys, black_keys) == 60, "lower white region -> C4"
    assert hit_test((5, 5), white_keys, black_keys) is None, "margin -> no key"

    # --- drag state machine (the three awkward cases) ------------------------
    step(pygame.MOUSEBUTTONDOWN, pos=(54, 254), button=1)   # press C4
    assert state["note"] == 60, state
    step(pygame.MOUSEMOTION, pos=(80, 90))                  # drag up onto black C#4
    assert state["note"] == 61, state

    out = "claude/spikes/mouse_input_preview.png"
    pygame.image.save(screen, out)                          # capture: C#4 active

    step(pygame.MOUSEMOTION, pos=(114, 254))                # drag onto white D4
    assert state["note"] == 62, state
    step(pygame.MOUSEMOTION, pos=(5, 5))                    # drag onto empty margin -> off
    assert state["note"] is None, state
    step(pygame.MOUSEMOTION, pos=(54, 254))                 # drag back onto C4 -> on
    assert state["note"] == 60, state
    step(pygame.MOUSEBUTTONUP, pos=(54, 254), button=1)     # release -> off
    assert state["note"] is None and state["held"] == set(), state

    # --- button released OUTSIDE the window still clears (if it's delivered) --
    step(pygame.MOUSEBUTTONDOWN, pos=(54, 254), button=1)
    assert state["note"] == 60, state
    step(pygame.MOUSEBUTTONUP, pos=(-5, -5), button=1)      # out-of-bounds release
    assert state["note"] is None and state["held"] == set(), state

    pygame.quit()
    print("selftest OK: hit-test order (black>white) verified; glissando drag, "
          "drag-to-empty, drag-back, and out-of-bounds release all cleared correctly.")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
