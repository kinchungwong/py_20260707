"""Tests for pypiano_2607.queue.EventQueue.

Ported from the assertions in claude/spikes/event_queue.py::_selftest:
  * T4 -- a bounded ring (maxlen=K) drops the OLDEST on overflow, never blocks
          (fast, deterministic).
  * T1 -- no drop / no reorder when the producer floods an unbounded queue while
          a block-paced consumer drains (real threads -> @pytest.mark.slow,
          deadline-guarded so a hang fails instead of wedging CI).
  * T2 -- the producer never blocks: an unbounded deque accepts all N pushes with
          NO consumer draining (structural, fast); plus a LOOSE per-push timing
          ceiling under @pytest.mark.perf.

T3 (transit-latency via the real InputRouter) is NOT ported -- InputRouter is a
deferred module, so that data path does not exist in the library yet.
"""

from __future__ import annotations

import threading
import time

import pytest

from pypiano_2607.config import BLOCK_PERIOD
from pypiano_2607.queue import EventQueue


# --- basic contract sanity (fast, deterministic) ------------------------------

def test_drain_empty_returns_empty_list():
    q = EventQueue()
    assert q.drain() == []
    assert len(q) == 0


def test_push_then_drain_is_fifo():
    q = EventQueue()
    for i in range(5):
        q.push(i)
    assert len(q) == 5
    assert q.drain() == [0, 1, 2, 3, 4]
    # drain consumed everything; the queue is now empty
    assert len(q) == 0
    assert q.drain() == []


# --- T4: a bounded ring drops the OLDEST on overflow, never blocks -------------

def test_bounded_ring_drops_oldest():
    q = EventQueue(maxlen=4)           # no consumer; push past capacity
    for i in range(10):
        q.push(i)                      # never blocks even when full
    assert len(q) == 4, f"ring not capped: len={len(q)}"
    assert q.drain() == [6, 7, 8, 9], "overflow should drop the OLDEST, keep newest"


# --- T2: the producer never blocks (structural, fast) -------------------------

def test_producer_never_blocks_structural():
    """With NO consumer draining, an unbounded deque accepts every push -- there
    is no full/blocked state for append to wait on, so nothing is dropped."""
    n = 100_000
    q = EventQueue()                   # unbounded -> should never drop
    for i in range(n):
        q.push(i)
    assert len(q) == n, "push silently dropped events (unbounded deque should not)"
    # and the whole backlog drains back out intact, in order
    assert q.drain() == list(range(n))


# --- T1: no drop, no reorder, even when the producer floods the queue ----------

@pytest.mark.slow
def test_no_drop_no_reorder():
    """Real threads: the producer dumps all n events effectively instantly (large
    backlog), while a block-paced consumer drains at the audio-callback cadence.
    Everything must come back exactly once, in push order."""
    n = 50_000
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


# --- T2 (perf): the producer never blocks -- loose per-push timing ceiling ------

@pytest.mark.perf
def test_producer_never_blocks_timing():
    """The structural guarantee (append has no wait condition) is the real proof;
    this loose ceiling just catches a pathological stall."""
    n = 100_000
    q = EventQueue()                   # no consumer at all -> nothing draining
    worst = 0.0
    for i in range(n):
        t0 = time.perf_counter()
        q.push(i)
        dt = time.perf_counter() - t0
        if dt > worst:
            worst = dt

    assert len(q) == n, "push silently dropped events (unbounded deque should not)"
    assert worst < 0.05, f"a single push blocked for {worst * 1e3:.3f} ms"
