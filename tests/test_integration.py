"""End-to-end input-layer integration.

Two things:
  * a router->queue->PolySynth path: keyboard + mouse on the SAME note reconcile to
    ONE sounding voice (the [[note-event-reconciliation]] behavior), and the freq the
    router MINTED (midi_to_freq) is what the synth sounds -- proving the router is the
    pitch->Hz resolution point;
  * the event_queue spike's T3 ported onto the promoted InputRouter + EventQueue: a
    GUI-ish producer plays a melody through the real router across a thread boundary,
    a block-paced consumer drains, and transit latency is bounded by one drain
    interval. Threaded => @pytest.mark.slow.

SDL dummy is set at the top: the reconciliation test drives the mouse source through
the widget's hit_test (which imports pygame lazily). The T3 test itself is pygame-free.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import threading
import time

import numpy as np
import pytest

from pypiano_2607.router import InputRouter
from pypiano_2607.events import NoteKind, Source
from pypiano_2607.pitch import midi_to_freq
from pypiano_2607.queue import EventQueue
from pypiano_2607.audio import PolySynth
from pypiano_2607.config import SR, BLOCK_FRAMES, BLOCK_PERIOD
from pypiano_2607.gui.keyboard import build_keys, hit_test, WHITE_W, WHITE_H


def _drive(synth, n_blocks):
    for _ in range(n_blocks):
        out = np.zeros((BLOCK_FRAMES, 1), dtype=np.float32)
        synth.callback(out, BLOCK_FRAMES, None, None)


def _dominant_freq(sig):
    w = np.hanning(len(sig))
    mag = np.abs(np.fft.rfft(sig * w))
    freqs = np.fft.rfftfreq(len(sig), 1.0 / SR)
    mag[0] = 0.0
    return float(freqs[int(np.argmax(mag))])


# --- router -> queue -> PolySynth: keyboard + mouse reconcile to one voice -----

def test_keyboard_and_mouse_reconcile_to_one_voice():
    import pygame
    pygame.init()
    try:
        white, black = build_keys()
        router = InputRouter()
        q = EventQueue()
        synth = PolySynth(q, max_voices=8)

        # keyboard presses C4 (60) -> a real note-on flows to the synth
        on = router.press(60, Source.KEYBOARD)
        assert on is not None and on.sounder_id == 60
        q.push(on)

        # mouse lands on the C4 white key -> hit_test resolves to 60 -> reconciled
        c4 = hit_test((WHITE_W // 2, WHITE_H - 10), white, black)
        assert c4 == 60
        assert router.press(c4, Source.MOUSE) is None       # no doubled note-on

        _drive(synth, 1)
        assert synth.active_count() == 1                     # exactly ONE voice

        # release keyboard -> mouse still holds it, no event, voice stays up
        assert router.release(60, Source.KEYBOARD) is None
        _drive(synth, 1)
        assert synth.active_count() == 1

        # release mouse -> the 1->0 transition -> note-off -> voice releases + frees
        off = router.release(60, Source.MOUSE)
        assert off is not None and off.kind is NoteKind.OFF and off.freq is None
        q.push(off)
        _drive(synth, 40)                                    # let the release fade finish
        assert synth.active_count() == 0
    finally:
        pygame.quit()


# --- the minted freq is what the synth sounds (pitch->Hz resolution point) -----

def test_router_minted_freq_is_sounded():
    router = InputRouter()
    q = EventQueue()
    synth = PolySynth(q, max_voices=8)

    on = router.press(69, Source.KEYBOARD)                   # A4
    assert on.freq == pytest.approx(midi_to_freq(69), rel=1e-9)  # ~440 Hz, minted here
    q.push(on)
    _drive(synth, 1)
    assert synth.active_count() == 1

    chunks = []
    while sum(len(c) for c in chunks) < 8192:
        chunks.append(synth.render(BLOCK_FRAMES, limit=False))
    sig = np.concatenate(chunks)[:8192]
    peak = _dominant_freq(sig)
    assert abs(peak - midi_to_freq(69)) < 6.0                # the synth sounds ~440 Hz


# --- event_queue T3 ported onto the promoted router + queue (threaded) --------

@pytest.mark.slow
def test_transit_latency_bounded():
    """Faithful data path: a GUI-ish producer plays a melody through the real
    InputRouter and pushes each emitted NoteEvent; a block-paced consumer drains
    and stamps arrival. Each note is pressed then released before the next, so no
    reconciliation suppression -> exactly one ON and one OFF per note. Transit
    latency (drain_time - event.t) must be bounded by one drain interval."""
    n_notes = 160
    q = EventQueue()
    router = InputRouter()
    produced = []
    received = []
    drain_times = []
    done = threading.Event()

    def producer():
        for i in range(n_notes):
            note = 48 + (i % 25)                    # wander over two octaves
            ev = router.press(note, Source.KEYBOARD)
            if ev is not None:
                produced.append(ev)
                q.push(ev)
            time.sleep(0.004 + (i % 3) * 0.001)     # ~4-6 ms note-on to note-off
            ev = router.release(note, Source.KEYBOARD)
            if ev is not None:
                produced.append(ev)
                q.push(ev)
            time.sleep(0.003)                        # ~3 ms before the next note
        done.set()

    def consumer():
        deadline = time.perf_counter() + 30.0
        while not (done.is_set() and len(q) == 0):
            evs = q.drain()
            now = time.perf_counter()
            drain_times.append(now)
            for e in evs:
                received.append((now, e))
            if time.perf_counter() > deadline:
                break
            time.sleep(BLOCK_PERIOD)
        now = time.perf_counter()
        drain_times.append(now)                      # record the final drain instant too
        for e in q.drain():
            received.append((now, e))

    c = threading.Thread(target=consumer, name="consumer")
    p = threading.Thread(target=producer, name="producer")
    c.start()
    p.start()
    p.join()
    c.join()

    # no drop / no reorder, on the real event objects
    assert len(received) == len(produced), \
        f"drop: got {len(received)} of {len(produced)} events"
    assert [e for _, e in received] == produced, "reorder or duplication detected"
    assert sum(e.kind is NoteKind.ON for _, e in received) == n_notes
    assert sum(e.kind is NoteKind.OFF for _, e in received) == n_notes

    latencies = [rt - e.t for rt, e in received]
    assert min(latencies) >= 0.0, "an event was 'received' before it was emitted"

    max_gap = max(b - a for a, b in zip(drain_times, drain_times[1:]))
    # An event waits at most until the next drain, so max latency cannot exceed the
    # largest gap between consecutive drains (+ a hair of slack for the final sweep).
    assert max(latencies) <= max_gap + 0.003, \
        f"latency {max(latencies) * 1e3:.2f} ms exceeded max drain gap " \
        f"{max_gap * 1e3:.2f} ms -- the bound does not hold"
