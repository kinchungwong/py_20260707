"""Thread-safe, non-blocking hand-off of the NoteEvent stream across the
GUI -> audio thread boundary (committed topology A: the audio callback drains it).

Promoted verbatim from the event_queue spike (the class, its docstring, and its
drain logic are unchanged); only the module-level constants and the spike's
cross-import were dropped -- constants now live in ``config``.
"""

from __future__ import annotations

from collections import deque


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
