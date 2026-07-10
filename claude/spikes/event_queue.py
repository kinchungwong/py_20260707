#!/usr/bin/env python3
"""
SPIKE: hand the NoteEvent stream across the GUI -> audio thread boundary via a
       thread-safe, NON-BLOCKING queue (committed topology A)

Question asked
--------------
Fifth GUI spike, and the first to cross a thread boundary -- which the task flags
as the real risk. `input_integration` produces a reconciled `NoteEvent` stream on
the GUI thread. The audio side lives on a *different*, real-time thread: the
sounddevice `OutputStream` callback (see `outputstream_callback`). Under committed
**topology A**, that audio callback drains the event queue itself, every block.
So, with no audio wired up yet:

  * What thread-safe structure carries events GUI -> audio?
  * Can the producer (GUI) push WITHOUT EVER BLOCKING? A stall on the GUI thread
    is a dropped frame; worse, any back-pressure that reaches into the audio
    thread is an xrun.
  * Can the consumer (audio callback) drain NON-BLOCKING -- take whatever is
    present right now and get back to making samples, never wait?
  * With the producer able to outrun the block-paced consumer, is any event
    DROPPED or REORDERED?
  * Is transit latency (emit -> drain) BOUNDED, and by what?

No sound. We simulate the audio callback's *cadence* with a timer thread that
drains once per ~one-block period (BLOCK_FRAMES / SR, from the block size the
`outputstream_callback` spike actually observed). The drain logic here is exactly
what the real callback will call.

What this does
--------------
`EventQueue` wraps a `collections.deque`. `push()` (producer) is `append`;
`drain()` (consumer) pops everything currently present and returns it in FIFO
order, stopping at empty -- never waiting. deque is chosen over `queue.Queue`
precisely because its `append`/`popleft` are individually atomic under CPython:
no lock for the real-time audio thread to acquire (see Finding).

Three checks, each mapping to a claim, all with real threads (the whole point is
the cross-thread hand-off):
  T1  producer pushes 0..N-1 as fast as it can while a block-paced consumer
      drains -> received == list(range(N))  (no drop, no reorder, big backlog).
  T2  with NO consumer, push N and time every push -> all accepted, each push
      is microseconds (deque.append has no wait condition -> can't block).
  T3  a GUI-ish producer plays a melody through the *real* `InputRouter` and
      pushes each emitted `NoteEvent`; the block-paced consumer stamps arrival.
      Transit latency = drain_time - event.t; bounded by one drain interval.

Finding
-------
- Structure: `collections.deque`, NOT `queue.Queue`. Under CPython `deque.append`
  (producer) and `deque.popleft` (consumer) are each atomic, so the queue needs
  NO explicit lock. `queue.Queue` guards every put/get with a mutex + condition
  variable; the real-time audio callback would have to acquire that lock, and if
  the GUI thread holds it at that instant the audio thread blocks -> priority
  inversion -> xrun. deque sidesteps the lock entirely. This is the committed
  topology-A carrier.
- Producer never blocks (T2): with the consumer stopped, all 100000 pushes were
  accepted and every one returned in microseconds -- observed mean ~0.15 us, p99
  ~2 us, worst-case a single ~50-60 us outlier (GC/scheduling). Structural, not
  luck: `append` on an unbounded deque has no full/blocked state -- there is
  nothing to wait on.
- No drop, no reorder (T1): the producer dumped all 50000 events effectively
  instantly, so a large backlog sat in the deque; the block-paced consumer still
  drained them all, exactly once, in push order (`received == list(range(N))`).
  FIFO is guaranteed by append-right / popleft-left; the atomic ops mean an
  append racing a drain is simply seen on this drain or the next -- never lost,
  never duplicated, never reordered.
- Transit latency is bounded by ONE drain interval (T3). An event pushed at time
  t is delivered by the first drain at-or-after t, so latency <= the gap since
  the previous drain. Measured against the real InputRouter data path: max
  latency ~8.7 ms, p99 ~8.7 ms, median ~4.3 ms -- all tracking the ~8.7 ms
  block period, and provably <= the largest observed inter-drain gap (~9 ms).
  Lower latency = drain more often = smaller audio blocks (the usual latency vs.
  xrun-headroom trade, deferred to `input_to_sound_latency`).
- Unbounded vs. bounded: default `maxlen=None` never drops; our event rate (human
  input, a few/sec) is far below the drain rate (~115/sec at 383-frame blocks),
  so the backlog is normally 0-1 events and unbounded growth is a non-issue. A
  bounded ring (`maxlen=K`) also never blocks, but on overflow `append` silently
  discards the OLDEST event (T4) -- so a bound must be sized to never overflow in
  practice, or oldest-drop must be acceptable. We commit to unbounded.
- Topology A stands: the audio callback can safely own the drain. The worker-
  thread alternative (topology B, ../speculations/audio-consumer-worker-thread.md)
  stays parked -- nothing here forced a third thread.

Run
---
    python claude/spikes/event_queue.py             # verbose: correctness + latency stats
    python claude/spikes/event_queue.py --selftest  # headless asserts (CI-style)
"""

from __future__ import annotations

import argparse
import statistics
import threading
import time
from collections import deque

# Reuse the canonical event vocabulary + reconciler from the integration spike.
# Both import pygame *lazily*, so pulling these in stays headless -- no display.
from input_integration import InputRouter, NoteEvent, NoteKind, Source

SR = 44100
BLOCK_FRAMES = 383                    # the steady block size observed in outputstream_callback
BLOCK_PERIOD = BLOCK_FRAMES / SR      # ~8.68 ms -- the audio callback's drain cadence


class EventQueue:
    """Single-producer / single-consumer hand-off across the GUI -> audio thread
    boundary (committed topology A: the audio callback drains it directly).

    Backed by ``collections.deque``. Under CPython, ``deque.append()`` (producer)
    and ``deque.popleft()`` (consumer) are each individually atomic, so:
      * ``push()`` never blocks and needs no lock -- append has no wait condition.
      * ``drain()`` never blocks -- it pops whatever is present, stops at empty.

    This is why we use a deque and NOT ``queue.Queue``: Queue guards every
    put/get with a mutex + condition variable that the real-time audio callback
    would have to acquire; if the GUI thread holds it at that moment the audio
    thread blocks = priority inversion = xrun. deque's atomic ops avoid the lock.

    ``maxlen=None`` (default) => unbounded: never drops. Our event rate (human
    input) is far below the drain rate, so the backlog stays tiny.
    ``maxlen=K`` => a bounded ring: on overflow ``append`` silently discards the
    OLDEST event -- still never blocks. Use only if unbounded growth is a real
    worry, and size K so it never actually overflows.
    """

    def __init__(self, maxlen: int | None = None):
        self._dq: deque = deque(maxlen=maxlen)

    def push(self, item) -> None:
        self._dq.append(item)          # producer (GUI thread). O(1), never blocks.

    def drain(self) -> list:
        """Consumer (audio callback). Take everything available right now and
        return it in FIFO (emit) order -- never wait."""
        out = []
        popleft = self._dq.popleft
        try:
            while True:
                out.append(popleft())
        except IndexError:
            pass                       # empty -> done, without ever blocking
        return out

    def __len__(self) -> int:
        return len(self._dq)


def _percentile(xs: list[float], pct: float) -> float:
    """Linear-interpolated percentile; xs need not be sorted."""
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] * (1.0 - frac) + s[hi] * frac


# --- T1: no drop, no reorder, even when the producer floods the queue ---------

def _test_no_drop_no_reorder(n: int = 50_000) -> None:
    q = EventQueue()
    received: list[int] = []
    done = threading.Event()

    def producer():
        for i in range(n):
            q.push(i)                  # dump all n effectively instantly
        done.set()

    def consumer():
        deadline = time.perf_counter() + 30.0
        while not (done.is_set() and len(q) == 0):
            received.extend(q.drain())
            if time.perf_counter() > deadline:
                break                  # safety: fail the assert instead of hanging
            time.sleep(BLOCK_PERIOD)   # drain at the audio-callback cadence
        received.extend(q.drain())     # final sweep for anything that just landed

    c = threading.Thread(target=consumer, name="consumer")
    p = threading.Thread(target=producer, name="producer")
    c.start()
    p.start()
    p.join()
    c.join()

    assert len(received) == n, f"drop: got {len(received)} of {n}"
    assert received == list(range(n)), "reorder or duplication detected"


# --- T2: the producer never blocks (structural + timed) -----------------------

def _test_producer_never_blocks(n: int = 100_000) -> dict:
    q = EventQueue()                   # no consumer at all -> nothing draining
    durations: list[float] = []
    worst = 0.0
    for i in range(n):
        t0 = time.perf_counter()
        q.push(i)
        dt = time.perf_counter() - t0
        durations.append(dt)
        if dt > worst:
            worst = dt

    assert len(q) == n, "push silently dropped events (unbounded deque should not)"
    # The structural guarantee (append has no wait condition) is the real proof;
    # this loose ceiling just catches a pathological stall.
    assert worst < 0.05, f"a single push blocked for {worst * 1e3:.3f} ms"
    return {
        "mean_us": statistics.fmean(durations) * 1e6,
        "p99_us": _percentile(durations, 99) * 1e6,
        "max_us": worst * 1e6,
    }


# --- T3: transit latency is bounded by one drain interval ---------------------

def _test_transit_latency_bounded(n_notes: int = 160) -> dict:
    """Faithful data path: a GUI-ish producer plays a melody through the real
    InputRouter and pushes each emitted NoteEvent; a block-paced consumer drains
    and stamps arrival. Each note is pressed then released before the next, so no
    reconciliation suppression -> exactly one ON and one OFF per note."""
    q = EventQueue()
    router = InputRouter()
    produced: list[NoteEvent] = []
    received: list[tuple[float, NoteEvent]] = []
    drain_times: list[float] = []
    done = threading.Event()

    def producer():
        for i in range(n_notes):
            note = 48 + (i % 25)       # wander over two octaves
            ev = router.press(note, Source.KEYBOARD)
            if ev is not None:
                produced.append(ev)
                q.push(ev)
            time.sleep(0.004 + (i % 3) * 0.001)   # ~4-6 ms note-on to note-off
            ev = router.release(note, Source.KEYBOARD)
            if ev is not None:
                produced.append(ev)
                q.push(ev)
            time.sleep(0.003)          # ~3 ms before the next note
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
        drain_times.append(now)        # record the final drain instant too
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
    # The invariant: an event waits at most until the next drain, so max latency
    # cannot exceed the largest gap between consecutive drains (+ a hair of slack
    # for the measurement edge on the final sweep).
    assert max(latencies) <= max_gap + 0.003, \
        f"latency {max(latencies) * 1e3:.2f} ms exceeded max drain gap " \
        f"{max_gap * 1e3:.2f} ms -- the bound does not hold"

    return {
        "events": len(received),
        "drains": len(drain_times),
        "min_ms": min(latencies) * 1e3,
        "p50_ms": _percentile(latencies, 50) * 1e3,
        "p99_ms": _percentile(latencies, 99) * 1e3,
        "max_ms": max(latencies) * 1e3,
        "max_gap_ms": max_gap * 1e3,
    }


# --- T4: a bounded ring drops the OLDEST on overflow, never blocks -------------

def _test_bounded_ring_drops_oldest() -> None:
    q = EventQueue(maxlen=4)           # no consumer; push past capacity
    for i in range(10):
        q.push(i)                      # never blocks even when full
    assert len(q) == 4, f"ring not capped: len={len(q)}"
    assert q.drain() == [6, 7, 8, 9], "overflow should drop the OLDEST, keep newest"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless asserts (CI-style); otherwise a verbose demo")
    args = ap.parse_args()

    # Same code path either way; --selftest just keeps the output terse.
    _test_no_drop_no_reorder()
    print("T1 OK: producer flooded the queue; block-paced consumer drained every "
          "event once, in order (no drop, no reorder).")

    push = _test_producer_never_blocks()
    print(f"T2 OK: 100000 pushes with NO consumer, all accepted, never blocked -- "
          f"mean={push['mean_us']:.3f}us p99={push['p99_us']:.3f}us "
          f"max={push['max_us']:.3f}us.")

    lat = _test_transit_latency_bounded()
    print(f"T3 OK: {lat['events']} events over {lat['drains']} drains via the real "
          f"InputRouter path -- latency min={lat['min_ms']:.2f} "
          f"p50={lat['p50_ms']:.2f} p99={lat['p99_ms']:.2f} "
          f"max={lat['max_ms']:.2f} ms; bounded by max drain gap "
          f"{lat['max_gap_ms']:.2f} ms.")

    _test_bounded_ring_drops_oldest()
    print("T4 OK: bounded ring (maxlen=4) never blocked on overflow; dropped the "
          "OLDEST, kept the newest.")

    if not args.selftest:
        print(f"\nblock period simulated = {BLOCK_PERIOD * 1e3:.2f} ms "
              f"({BLOCK_FRAMES} frames @ {SR} Hz). Topology A holds: the audio "
              f"callback can own a non-blocking deque drain.")


if __name__ == "__main__":
    main()
