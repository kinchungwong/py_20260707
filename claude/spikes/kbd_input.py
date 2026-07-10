#!/usr/bin/env python3
"""
SPIKE: Computer-keyboard input -> highlight the played piano key (no audio)

Question asked
--------------
Second GUI spike. Can we map the computer (QWERTY) keyboard to piano notes, and
on ``KEYDOWN``/``KEYUP`` highlight the corresponding on-screen key while tracking
the set of currently-held notes? Two sub-questions the spike should settle:
  * Does PyGame give clean press/release *pairs* (one down, one up per physical
    key), or does key auto-repeat muddy the note-on/note-off semantics?
  * Can we redraw *only the changed key* instead of the whole keyboard?

Still no sound -- this is purely input -> visual. The held-note set and the
QWERTY->MIDI map defined here are what the later `event_queue` spike will turn
into note-on/note-off events.

What this does
--------------
Draws the two-octave keyboard (geometry/drawing now live in the shared
`piano_keyboard` module), but each key carries a MIDI note number. A QWERTY->MIDI
map (home row = white keys, the row above = black keys, one octave + the octave C)
lets you "play": pressing a mapped key highlights that piano key and adds it to the
held set; releasing un-highlights it. Unmapped drawn keys simply never light up (a
computer keyboard doesn't cover a whole piano -- that's honest, not a bug).
Note-on/note-off are also printed.

Redraw strategy: on each change we repaint only the affected key and call
``pygame.display.update(dirty_rect)`` -- NOT a full-keyboard redraw. The wrinkle
is that black keys overlap their white neighbours, so repainting a white key must
re-overlay any black key sitting on top of it (else the white paint erases it).
That logic lives in `piano_keyboard.redraw_key`.

Finding
-------
- Clean press/release pairs: YES. PyGame does NOT auto-repeat ``KEYDOWN`` unless
  you call ``pygame.key.set_repeat(...)``. With the default, a held key emits
  exactly one KEYDOWN and one KEYUP -- ideal note-on/note-off. Still dedupe on the
  held-set (``if midi in held: skip``) so the semantics survive if anyone ever
  turns repeat on. Distilled into ../memory/pygame/key-events-note-on-off.md.
- Redraw only the changed key: YES -- repaint just that key and call
  ``pygame.display.update(dirty_rect)`` instead of ``flip()``. The wrinkle worth
  remembering: black keys overlap their white neighbours, so repainting a white
  key must re-overlay any black key covering it (``rect.colliderect``), or the
  white paint erases the black. Verified in kbd_input_preview.png -- the lit white
  keys sit correctly *under* their intact black keys.
- QWERTY->MIDI map: home row ``a..k`` = C4..C5 (white), row above ``w e t y u`` =
  the 5 black keys of the lower octave; the unmapped ``r``/``i`` mirror the
  physical no-black-key gaps (E-F, B-C). 13 keys mapped; the drawn upper octave
  past C5 has no binding -- a computer keyboard just doesn't span a whole piano.
- ``pygame.event.wait()`` is STILL the right loop here: state changes only on
  discrete key events (no continuous animation), so it stays at 0% CPU idle. The
  spikes that animate (envelopes, level meters) are the ones that will need a
  polled, clock-driven loop instead.
- The held-note set + the QWERTY->MIDI map defined here are exactly what the
  `event_queue` spike will translate into note-on/note-off events.

Run
---
    python claude/spikes/kbd_input.py            # real window; play with the keys
    python claude/spikes/kbd_input.py --selftest # headless: simulate presses, save PNG
"""

from __future__ import annotations

import argparse
import os

from piano_keyboard import (
    WIDTH, HEIGHT, note_name, build_keys, render_full, redraw_key,
)

# --- QWERTY -> MIDI layout ---------------------------------------------------
# Home row = white keys of the lower octave (a..k = C4..C5); row above = the
# black keys (w e t y u = C#4 D#4 F#4 G#4 A#4). Gaps (no black at E-F, B-C) match
# the physical keyboard -- 'r' and 'i' are intentionally unmapped.
WHITE_QWERTY = [("a", 60), ("s", 62), ("d", 64), ("f", 65),
                ("g", 67), ("h", 69), ("j", 71), ("k", 72)]
BLACK_QWERTY = [("w", 61), ("e", 63), ("t", 66), ("y", 68), ("u", 70)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless: simulate key presses, save a preview PNG, no display")
    args = ap.parse_args()

    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("kbd_input spike — play with a..k / w e t y u, Esc to quit")

    white_keys, black_keys = build_keys()
    key_to_midi = {pygame.key.key_code(ch): midi for ch, midi in WHITE_QWERTY + BLACK_QWERTY}
    held: set[int] = set()

    render_full(screen, white_keys, black_keys, held)
    pygame.display.flip()

    if args.selftest:
        _run_selftest(pygame, screen, white_keys, black_keys, held, key_to_midi)
        return

    running = True
    while running:
        event = pygame.event.wait()   # state only changes on discrete key events -> wait() is fine
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key in key_to_midi:
                midi = key_to_midi[event.key]
                if midi in held:
                    continue          # already sounding (e.g. if key-repeat were on) -> no dup note-on
                held.add(midi)
                dirty = redraw_key(screen, midi, white_keys, black_keys, held)
                pygame.display.update(dirty)
                print(f"note-on  {note_name(midi):4s} (midi {midi})  held={sorted(held)}")
        elif event.type == pygame.KEYUP:
            if event.key in key_to_midi:
                midi = key_to_midi[event.key]
                held.discard(midi)
                dirty = redraw_key(screen, midi, white_keys, black_keys, held)
                pygame.display.update(dirty)
                print(f"note-off {note_name(midi):4s} (midi {midi})  held={sorted(held)}")

    pygame.quit()


def _run_selftest(pygame, screen, white_keys, black_keys, held, key_to_midi):
    """Headless: drive a scripted press/release sequence, assert held-set
    transitions, and save a preview PNG with a chord held down."""
    def down(ch):
        midi = key_to_midi[pygame.key.key_code(ch)]
        held.add(midi)
        redraw_key(screen, midi, white_keys, black_keys, held)
        return midi

    def up(ch):
        midi = key_to_midi[pygame.key.key_code(ch)]
        held.discard(midi)
        redraw_key(screen, midi, white_keys, black_keys, held)
        return midi

    # Play a C-major-ish shape plus a black key: a=C4, e=D#4, g=G4, j=B4.
    for ch in ("a", "e", "g", "j"):
        down(ch)
    assert held == {60, 63, 67, 71}, held

    out = "claude/spikes/kbd_input_preview.png"
    pygame.image.save(screen, out)

    up("e")
    assert held == {60, 67, 71}, held
    for ch in ("a", "g", "j"):
        up(ch)
    assert held == set(), held

    pygame.quit()
    names = " ".join(note_name(m) for m in (60, 63, 67, 71))
    print(f"selftest OK: mapped {len(key_to_midi)} QWERTY keys; "
          f"pressed [{names}] then released all; held-set returned to empty.")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
