# Speculation — dedicated worker thread between the event queue and the audio callback

**Status: speculation, not a committed decision.**
**Committed baseline: topology A** — the audio callback drains the event queue
directly (proven by the `event_queue` spike; see
[`event-queue`](../memory/concurrency/event-queue.md)). This file records the
*alternative* we chose not to build, so we can revisit it deliberately.

## The idea (topology B)

Insert a third thread between the GUI and the audio device:

```
PyGame loop ──events──▶ queue ──drain──▶ worker thread ──publishes──▶ voice-state snapshot
 (producer)                              (consumer, does the                    │
                                          heavy processing)                     ▼
                                                              audio callback reads snapshot,
                                                              renders `frames` samples (no draining)
```

The worker thread owns the queue and all per-event work (voice allocation,
envelope setup, anything non-trivial). It maintains a **voice-state snapshot** and
publishes it atomically. The real-time audio callback never touches the queue —
it only reads the latest snapshot and turns it into samples.

## Why we might want it later

- **Keeps the real-time thread cheap.** Under topology A, the audio callback does
  drain + apply + render every block. If per-event processing grows (complex voice
  stealing, effect-graph reconfiguration, allocation-heavy work), that work starts
  competing with sample generation on the real-time thread and risks underruns.
  Topology B moves all of it off the callback.
- **This is where the "may need our own buffering" note from
  [`blocksize`](../memory/sounddevice/outputstream/blocksize.md) actually cashes
  out.** The snapshot / double-buffer between worker and callback *is* that
  buffer — it decouples the callback's block cadence from event processing.

## Costs / trade-offs (why it isn't the default)

- **Extra latency.** A second hand-off (worker → snapshot → callback) adds delay
  on top of GUI → queue. That works against the low-latency vision non-negotiable,
  so it must earn its keep.
- **Snapshot publication is its own hard problem.** The callback must never see a
  half-updated snapshot — needs an atomic swap / double-buffer / lock-free publish,
  or a lock the callback briefly takes (itself a real-time hazard).
- **More moving parts.** Three threads and two hand-offs to reason about instead
  of two threads and one.

## Trigger to revisit

The `event_queue` spike proved the *queue mechanics* are cheap (a non-blocking
deque drain, latency bounded by one block), so the hand-off itself does not force
topology B. Reopen this if **either**:

- the callback's drain-**and-apply** work (voice allocation + summed-voice render,
  measured later in `polyphony_voices`, not the queue drain) causes underruns /
  missed deadlines under realistic polyphony, **or**
- per-event processing grows beyond trivial (heavy voice allocation, effects,
  anything that allocates or blocks) and no longer belongs on the audio thread.

## Related

- Committed approach & the queue mechanics: `event_queue` spike (to be written),
  and [`blocksize`](../memory/sounddevice/outputstream/blocksize.md).
