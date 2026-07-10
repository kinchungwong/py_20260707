#!/usr/bin/env python3
"""
SPIKE: the first end-to-end PLAYABLE instrument -- wire every proven piece into
       one path: keyboard/mouse -> InputRouter -> EventQueue -> PolySynth -> audio

Question asked
--------------
Each prior spike proved one link in isolation. Do they COMPOSE into a responsive,
correct, playable instrument -- and are there integration surprises at the seams?
Concretely: the PyGame event loop (GUI thread) turns key/mouse input into
reconciled `NoteEvent`s and pushes them onto the thread-safe queue; the sounddevice
callback (audio thread) drains the queue and renders summed, enveloped, polyphonic
voices -- all at once, live.

What this does
--------------
Reuses, unmodified:
  * `piano_keyboard`  -- geometry, drawing, hit-test (the shared widget),
  * `InputRouter` + the QWERTY map (`input_integration` / `kbd_input`) -- merge
    keyboard + mouse into one deduplicated note-on/off stream,
  * `EventQueue` (`event_queue`) -- the lock-free, non-blocking topology-A carrier,
  * `PolySynth` (`polyphony_voices`) -- pooled voices, allocation/stealing, gate
    envelope (`realtime_envelope_release`), tanh headroom -- with the rich
    `PianoVoice` (`piano_voice`) swapped in by default via `voice_factory`
    (`--voice sine` falls back to the plain sine).

The only NEW code is the ~30-line glue: dispatch a PyGame event through the router
and, on each emitted event, (1) PUSH it to the queue (-> audio) and (2) repaint the
affected key from the reconciled held-set (-> visual). Producer = GUI thread;
consumer = audio callback. That's topology A, closed end to end for the first time.

Focus-loss safety: on `WINDOWFOCUSLOST` we all-notes-off (release everything, reset
input state) rather than ever grabbing the cursor -- the sanctioned alternative
from ../policy/input-policy.md.

Scope: monophonic-per-note pitch is 12-TET/MIDI; polyphony is the pool from
`polyphony_voices`. Latency is not yet measured -- that's `input_to_sound_latency`,
which needs exactly this wired path.

Finding
-------
- The pieces COMPOSE with no surprises. The whole instrument is: reuse four
  modules unmodified + ~30 lines of glue (route a router transition to the queue
  AND repaint the key). Nothing in piano_keyboard / InputRouter / EventQueue /
  PolySynth had to change -- the payoff of the shared-widget extraction and the
  clean `NoteEvent` vocabulary decided earlier.
- Threads: the GUI event loop is the PRODUCER, the audio callback the CONSUMER,
  bridged by the lock-free EventQueue (topology A) closed end to end for the first
  time. `pygame.event.wait()` keeps the GUI thread at 0% CPU while idle; the audio
  thread runs independently; they share no lock, only the deque.
- Keyboard + mouse merge through the ONE InputRouter, so a chord from both sources
  sounds exactly once -- verified C4 (keyboard) + G4 (mouse) -> 2 voices, both
  present, non-silent (peak 0.377), then released to 0.
- Focus-loss all-notes-off (the sanctioned non-grab response from the input
  policy) prevents stuck notes when the window loses focus -- verified: a held
  note goes silent on WINDOWFOCUSLOST.
- Verified headless by driving `synth.callback` manually after dispatching
  synthetic PyGame events through the SAME `dispatch()` used by the real loop; the
  audible real-window/real-device run is the default (human-verified separately).
- This is less a throwaway spike than the SEED of the real app -- the canonical
  signal chain now exists (map in ../memory/architecture/signal-chain.md).
- Next: `input_to_sound_latency` measures keypress->onset on exactly this path.

Run
---
    python claude/spikes/playable_instrument.py                # real window + audio (piano voice)
    python claude/spikes/playable_instrument.py --voice sine   # ... with the plain sine voice
    python claude/spikes/playable_instrument.py --selftest     # headless: drive the whole chain, PNG
"""

from __future__ import annotations

import argparse
import os
import time

from piano_keyboard import (
    build_keys, offset_keys, render_full, redraw_key, hit_test, note_name,
)
from input_integration import InputRouter, NoteEvent, NoteKind, Source, MARGIN, WIN_W, WIN_H
from kbd_input import WHITE_QWERTY, BLACK_QWERTY
from event_queue import EventQueue, SR, BLOCK_FRAMES
from polyphony_voices import PolySynth
from piano_voice import PianoVoice


# --- the glue: route one input event to BOTH the audio queue and the screen ----

def _emit(pygame, state, ev: NoteEvent | None) -> None:
    """A router transition (or None). Push it to the audio queue and repaint the
    affected key from the reconciled held-set."""
    if ev is None:
        return
    state["queue"].push(ev)                                  # -> audio thread
    rect = redraw_key(state["screen"], ev.midi, state["wk"], state["bk"],
                      state["router"].held)                  # -> visual
    if rect is not None:
        pygame.display.update(rect)


def _press(pygame, state, midi, source) -> None:
    _emit(pygame, state, state["router"].press(midi, source))


def _release(pygame, state, midi, source) -> None:
    _emit(pygame, state, state["router"].release(midi, source))


def _mouse_to(pygame, state, new_midi) -> None:
    """Move the single mouse-driven note to `new_midi` (or None), routing the old
    release and the new press through the router (glissando while dragging)."""
    old = state["m_note"]
    if new_midi == old:
        return
    if old is not None:
        _release(pygame, state, old, Source.MOUSE)
    if new_midi is not None:
        _press(pygame, state, new_midi, Source.MOUSE)
    state["m_note"] = new_midi


def _all_notes_off(pygame, state) -> None:
    """Release every sounding note and reset input state -- the sanctioned response
    to focus loss (never grab the cursor). Pushes a note-off per held note so the
    audio side frees the voices, then repaints the keyboard unpressed."""
    for midi in list(state["router"].held):
        state["queue"].push(NoteEvent(NoteKind.OFF, midi, Source.KEYBOARD, time.perf_counter()))
    state["router"] = InputRouter()
    state["m_down"] = False
    state["m_note"] = None
    render_full(state["screen"], state["wk"], state["bk"], set())
    pygame.display.flip()


def dispatch(pygame, event, state) -> bool:
    """Route one PyGame event through the router into the queue + screen. Returns
    False when we should quit. Same code path in the real loop and the selftest."""
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return False

    ktm = state["key_to_midi"]
    if event.type == pygame.KEYDOWN and event.key in ktm:
        _press(pygame, state, ktm[event.key], Source.KEYBOARD)
    elif event.type == pygame.KEYUP and event.key in ktm:
        _release(pygame, state, ktm[event.key], Source.KEYBOARD)
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        state["m_down"] = True
        _mouse_to(pygame, state, hit_test(event.pos, state["wk"], state["bk"]))
    elif event.type == pygame.MOUSEMOTION and state["m_down"]:
        _mouse_to(pygame, state, hit_test(event.pos, state["wk"], state["bk"]))
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        state["m_down"] = False
        _mouse_to(pygame, state, None)
    elif event.type == pygame.WINDOWFOCUSLOST:
        _all_notes_off(pygame, state)
    return True


def _make_state(pygame, screen, queue) -> dict:
    wk, bk = build_keys()
    offset_keys(wk + bk, MARGIN, MARGIN)
    return {
        "router": InputRouter(),
        "queue": queue,
        "screen": screen,
        "wk": wk,
        "bk": bk,
        "key_to_midi": {pygame.key.key_code(ch): m for ch, m in WHITE_QWERTY + BLACK_QWERTY},
        "m_down": False,
        "m_note": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless: drive the full chain with scripted events, assert + PNG")
    ap.add_argument("--voice", choices=("piano", "sine"), default="piano",
                    help="timbre: 'piano' = rich inharmonic-partial voice with natural "
                         "decay (default); 'sine' = plain sine")
    args = ap.parse_args()

    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption(f"playable_instrument ({args.voice}) — QWERTY + mouse, Esc to quit")

    queue = EventQueue()
    # 'sine' -> PolySynth's default Voice; 'piano' -> the rich PianoVoice.
    voice_factory = PianoVoice if args.voice == "piano" else None
    synth = PolySynth(queue, voice_factory=voice_factory)
    state = _make_state(pygame, screen, queue)
    render_full(screen, state["wk"], state["bk"], state["router"].held)
    pygame.display.flip()

    if args.selftest:
        _run_selftest(pygame, state, synth)
        return

    import sounddevice as sd

    print(f"playable ({args.voice} voice)! home row = white keys, the row above = "
          "black keys; click/drag the mouse too. Esc to quit.")
    # latency='low' is the dominant lever: it cuts device output latency from
    # ~35 ms (default) to ~9 ms on this backend -- see input_to_sound_latency.
    with sd.OutputStream(samplerate=SR, channels=1, dtype="float32",
                         callback=synth.callback, latency="low"):
        running = True
        while running:
            event = pygame.event.wait()      # discrete events -> 0% CPU while idle
            running = dispatch(pygame, event, state)

    if synth.status_flags:
        print(f"note: {synth.status_flags} callback status flags (possible underruns).")
    pygame.quit()


def _key_center(keys, midi):
    for k in keys:
        if k.midi == midi:
            return k.rect.center
    raise KeyError(midi)


def _run_selftest(pygame, state, synth) -> None:
    import numpy as np

    frames = BLOCK_FRAMES

    def drive(n):
        peak = 0.0
        for _ in range(n):
            out = np.zeros((frames, 1), dtype=np.float32)
            synth.callback(out, frames, None, None)          # audio thread: drain + render
            peak = max(peak, float(np.abs(out[:, 0]).max()))
        return peak

    def kd(ch):
        dispatch(pygame, pygame.event.Event(pygame.KEYDOWN, key=pygame.key.key_code(ch)), state)

    def ku(ch):
        dispatch(pygame, pygame.event.Event(pygame.KEYUP, key=pygame.key.key_code(ch)), state)

    def md(pt):
        dispatch(pygame, pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pt, button=1), state)

    def mu(pt):
        dispatch(pygame, pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pt, button=1), state)

    g4 = _key_center(state["wk"], 67)

    # A chord from BOTH sources at once: C4 via keyboard, G4 via mouse.
    kd("a")                      # C4 -> router ON -> queue
    md(g4)                       # G4 -> router ON -> queue
    assert state["router"].held == {60, 67}, state["router"].held

    peak = drive(20)             # let the audio side drain + reach sustain
    assert synth.active_count() == 2, synth.active_count()
    assert {m for m in synth.voice_midi if m is not None} == {60, 67}, synth.voice_midi
    assert peak > 0.0, "chain produced no sound"

    out_png = "claude/spikes/playable_instrument_preview.png"
    pygame.image.save(state["screen"], out_png)              # C4 + G4 lit

    # Release both -> voices free.
    ku("a")
    mu(g4)
    assert state["router"].held == set(), state["router"].held
    drive(40)                    # past the 20 ms release
    assert synth.active_count() == 0, synth.active_count()

    # Focus-loss all-notes-off: hold a note, drop focus, it must go silent.
    kd("a")
    drive(3)
    assert synth.active_count() == 1
    dispatch(pygame, pygame.event.Event(pygame.WINDOWFOCUSLOST), state)
    drive(40)
    assert synth.active_count() == 0, "focus-loss did not release the held note"

    pygame.quit()
    print("selftest OK: kbd C4 + mouse G4 -> 2 queued note-ons -> 2 voices sounding "
          f"(peak {peak:.3f}); released -> 0. Focus-loss all-notes-off works.")
    print(f"  wrote {out_png}")


if __name__ == "__main__":
    main()
