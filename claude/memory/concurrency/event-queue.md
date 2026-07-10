# GUI→audio hand-off: a lock-free, non-blocking deque (topology A)

How the reconciled `NoteEvent` stream crosses from the GUI thread to the
real-time audio thread. Proven by the `event_queue` spike
(`../../spikes/event_queue.py`, no audio — the callback cadence is simulated by a
timer thread draining once per block). This is the committed **topology A**: the
audio callback drains the queue itself, every block.

## The decision: `collections.deque`, NOT `queue.Queue`

The carrier is a plain `deque`. Producer = `append` (GUI thread); consumer =
`popleft`-until-`IndexError` (audio callback). Both ops are individually **atomic
under CPython**, so the queue needs **no explicit lock**.

- `queue.Queue` was rejected: it guards every put/get with a mutex + condition
  variable. The real-time audio callback would have to acquire that lock, and if
  the GUI thread holds it at that instant the audio thread **blocks → priority
  inversion → xrun**. deque's atomic ops sidestep the lock entirely.

## The properties it must have — all verified

- **Producer never blocks.** `deque.append` on an unbounded deque has no
  full/blocked state — nothing to wait on. Measured: 100 000 pushes with the
  consumer stopped, all accepted, ~0.15 µs mean each (worst a single ~50–60 µs
  GC/scheduling outlier). A GUI-thread stall would be a dropped frame; this can't
  cause one.
- **Consumer drains non-blocking.** `drain()` pops whatever is present and stops
  at empty — never waits. Exactly what the audio callback calls before it renders
  its `frames` samples.
- **No drop, no reorder** even when the producer floods the queue (backlog builds
  between block-paced drains). FIFO is guaranteed by append-right/popleft-left;
  because the ops are atomic, an append racing a drain is simply seen on this
  drain or the next — never lost, duplicated, or reordered.
- **Transit latency is bounded by ONE drain interval.** An event pushed at time
  `t` is delivered by the first drain at-or-after `t`, so latency ≤ the gap since
  the previous drain. Measured on the real `InputRouter` data path: median
  ~4.3 ms, p99/max ~8.7 ms — all tracking the ~8.7 ms block period
  (383 frames @ 44100 Hz), provably ≤ the largest inter-drain gap. **Lower
  latency ⇒ drain more often ⇒ smaller audio blocks** (the usual latency vs.
  xrun-headroom trade — quantified later by `input_to_sound_latency`).

## Unbounded vs. bounded — commit to unbounded

- `maxlen=None` (committed): never drops. Human input is a few events/sec; the
  drain runs ~115×/sec, so the backlog is normally 0–1 events — unbounded growth
  is a non-issue.
- `maxlen=K`: a bounded ring, also never blocks, but on overflow `append`
  **silently discards the OLDEST** event (not the newest, not blocking). Only use
  if unbounded growth is a real worry, and size K so it never actually overflows.

## Consequences

- **Topology A stands** — nothing here forced a worker thread. The topology-B
  alternative (worker thread + snapshot) stays parked in
  `../../speculations/audio-consumer-worker-thread.md`; its revisit trigger
  (drain-and-apply causing xruns under realistic polyphony) was **not** hit by
  the queue mechanics alone, but real per-event work + summed voices is only
  measured later (`polyphony_voices`).
- This deque **is** the "our own buffer between generator and callback" hedge that
  [[blocksize]] left room for — here it buffers *events*, not samples.

## Related

- Upstream source of the events: [[note-event-reconciliation]] (the `InputRouter`
  that produces the single note-on/off stream this queue carries).
- The block cadence the consumer drains at comes from [[blocksize]] (honor the
  callback's `frames`; block size not knowable up front).
- Next consumers of the drained stream: `realtime_envelope_release` (sustain while
  held, click-free release) then `polyphony_voices`.
