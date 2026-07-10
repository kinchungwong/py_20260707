#!/usr/bin/env python3
"""
SPIKE: measure keypress -> audible-onset latency on the wired path, and find what
       dominates (audio blocksize / device latency vs queue vs envelope attack)

Question asked
--------------
The vision makes low input-to-sound latency a non-negotiable (../vision/). Now that
`playable_instrument` wires the whole path, WHAT is the latency and WHAT dominates?
Decompose the budget from a note-on to the first sample hitting the DAC:

    [physical key] ─(a)─▶ PyGame delivers event ─(b)─▶ dispatch+router+push
                    ─(c)─▶ next audio callback drains ─(d)─▶ device output buffer ─▶ [speaker]

  (a) OS/USB/PyGame front-end  -- NOT measurable in-process (needs a mic loopback);
                                  we use `pygame.event.wait()`, so there is no added
                                  input-POLL interval -- delivery wakes us immediately.
  (b) dispatch + queue push    -- microseconds (measured).
  (c) queue + BLOCK QUANTIZATION-- a keypress lands at a random phase in the audio
                                  block, so it waits 0..one block (~8.7 ms) for the
                                  next drain. Measured via the perf_counter stamp
                                  that already rides every NoteEvent.
  (d) DEVICE OUTPUT latency     -- drain -> DAC; sounddevice reports it and the
                                  callback's time_info gives it per-block. Only
                                  measurable with a REAL stream open.
  envelope attack (~6 ms)       -- rise time AFTER onset (perceived sharpness), NOT
                                  onset delay; reported separately, not added in.

What this does
--------------
`--selftest` (headless, no device): measures the software path -- push cost (b) and
the queue/block-quantization distribution (c) with a block-paced consumer -- asserts
(c) is bounded by one block, and writes a latency-budget PNG. The device term (d)
is explicitly NOT measured headless.

Default (real device): sweeps blocksize/latency-hint and reports each stream's
output latency (the lever), then runs an end-to-end measurement -- pushing note-ons
while a real OutputStream (PolySynth voicing) records per-event push->drain latency
(c) and device output latency (d) from time_info -- and prints the ranked budget.

Finding
-------
Numbers below are from a real-device run (pipewire/ALSA on the dev box).

- DEVICE OUTPUT latency (d) DOMINATES: ~11.4 ms mean (drain -> DAC). The queue /
  block-quantization (c) is next; the software glue (b) is ~0.1 us -- nothing.
- THE LEVER IS `latency='low'`, NOT a smaller requested blocksize. The sweep:
    latency='low'  -> stream.latency  8.62 ms  (95-frame blocks, ~2.15 ms)
    latency='high' -> 34.74 ms (383-frame)   <- this is also the DEFAULT (no hint)
    blocksize 128/256/512 (no hint) -> ALL ~34.83 ms   <-- block size did NOT
        change the latency; the output buffer is a fixed ~35 ms unless you ask
        for low latency. Requesting a small blocksize alone is a trap.
    blocksize 1024 -> 23.22 ms (backend quantization; non-monotonic -> yet another
        reason to use the hint, not hand-tuned block sizes).
- With `latency='low'`, the whole thing is responsive: onset (c)+(d) mean ~12.9 ms,
  p99 ~19 ms. And (c) collapses to ~1.5 ms mean because the blocks are ~2.15 ms
  (block-quantization ~= half a block), vs ~4.4 ms with the default 383-frame block.
- TAIL / the vision's "Python may pose inherent limits": (c) had a max of ~27.8 ms
  (mean 1.5, p99 7.9) -- occasional scheduling/GC jitter on the producer or drain.
  The typical case is great; the worst case is where CPython bites. Watch it under
  load; a dropped-frame budget lives in the tail, not the mean.
- Envelope attack (6 ms) is a rise time AFTER onset, separable from the onset delay.
- COMMITTED: open the OutputStream with `latency='low'` (applied to
  `playable_instrument`; the prior demo spikes still use the default and thus run
  ~4x slower on term (d)). Front-end (physical key -> PyGame event) stays unmeasured
  here -- it needs an external mic-loopback rig.

Run
---
    python claude/spikes/input_to_sound_latency.py             # REAL device: sweep + end-to-end
    python claude/spikes/input_to_sound_latency.py --selftest  # headless: queue budget + PNG
"""

from __future__ import annotations

import argparse
import statistics
import threading
import time

import numpy as np

from event_queue import EventQueue, SR, BLOCK_FRAMES, BLOCK_PERIOD, NoteEvent, NoteKind, Source
from realtime_envelope_release import note_event, ATTACK_MS
from polyphony_voices import PolySynth


def _pct(xs, p):
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] * (1 - (k - lo)) + s[hi] * (k - lo)


def _stats_ms(xs):
    return {
        "min": min(xs) * 1e3, "mean": statistics.fmean(xs) * 1e3,
        "p50": _pct(xs, 50) * 1e3, "p99": _pct(xs, 99) * 1e3, "max": max(xs) * 1e3,
    }


# --- (b) push cost ------------------------------------------------------------

def _measure_push_cost(n: int = 100_000) -> float:
    q = EventQueue()
    t0 = time.perf_counter()
    for i in range(n):
        q.push(i)
    return (time.perf_counter() - t0) / n


# --- (c) queue + block-quantization latency (headless, block-paced consumer) ---

def _measure_queue_latency(n: int = 300, push_gap: float = 0.007):
    """A producer pushes note-ons spaced ~7 ms (incommensurate with the ~8.68 ms
    block, so keypresses sweep every phase within a block); a consumer drains at
    the block cadence. Latency = drain_time - note.t."""
    q = EventQueue()
    latencies: list[float] = []
    drain_times: list[float] = []
    done = threading.Event()

    def producer():
        for i in range(n):
            q.push(note_event(NoteKind.ON, 60 + (i % 12)))
            time.sleep(push_gap)
        done.set()

    def consumer():
        deadline = time.perf_counter() + 30.0
        while not (done.is_set() and len(q) == 0):
            now = time.perf_counter()
            drain_times.append(now)
            for ev in q.drain():
                latencies.append(now - ev.t)
            if time.perf_counter() > deadline:
                break
            time.sleep(BLOCK_PERIOD)          # simulate the callback's drain cadence
        now = time.perf_counter()
        drain_times.append(now)
        for ev in q.drain():
            latencies.append(now - ev.t)

    c = threading.Thread(target=consumer, name="consumer")
    p = threading.Thread(target=producer, name="producer")
    c.start()
    p.start()
    p.join()
    c.join()

    assert len(latencies) == n, f"dropped events: {len(latencies)} of {n}"
    assert min(latencies) >= 0.0
    max_gap = max(b - a for a, b in zip(drain_times, drain_times[1:]))
    # Invariant: a keypress waits at most until the next drain -> <= one drain gap.
    assert max(latencies) <= max_gap + 0.003, \
        f"queue latency {max(latencies)*1e3:.2f} ms exceeded drain gap {max_gap*1e3:.2f} ms"
    return latencies


def _selftest() -> None:
    push_cost = _measure_push_cost()
    qlat = _measure_queue_latency()
    qs = _stats_ms(qlat)

    print("input->sound latency, SOFTWARE path (headless; device term measured in the real run):")
    print(f"  (b) dispatch + queue push : {push_cost*1e6:.3f} us  (negligible)")
    print(f"  (c) queue + block-quant   : min {qs['min']:.2f}  mean {qs['mean']:.2f}  "
          f"p99 {qs['p99']:.2f}  max {qs['max']:.2f} ms  "
          f"(ceiling = one block = {BLOCK_PERIOD*1e3:.2f} ms)")
    print(f"      envelope attack (rise, not onset delay): {ATTACK_MS:.1f} ms")
    print(f"  (d) device output latency : NOT measured headless -- run the default "
          f"mode on real hardware; it typically DOMINATES.")

    out_png = "claude/spikes/input_to_sound_latency_preview.png"
    _plot(qlat, push_cost, out_png)
    print(f"  wrote {out_png}")


def _plot(qlat, push_cost, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    qms = np.array(qlat) * 1e3
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

    ax1.hist(qms, bins=40, color="C0", edgecolor="none")
    ax1.axvline(BLOCK_PERIOD * 1e3, color="red", ls="--", lw=1,
                label=f"one block = {BLOCK_PERIOD*1e3:.2f} ms")
    ax1.axvline(float(np.mean(qms)), color="C1", ls="--", lw=1,
                label=f"mean = {np.mean(qms):.2f} ms")
    ax1.set_title("(c) queue + block-quantization latency — ~uniform over one block")
    ax1.set_xlabel("latency (ms)")
    ax1.set_ylabel("count")
    ax1.legend(loc="upper right")

    labels = ["(b) dispatch+push", "(c) queue mean", "envelope attack\n(rise, not onset)"]
    vals = [push_cost * 1e3, float(np.mean(qms)), ATTACK_MS]
    ax2.barh(labels, vals, color=["C2", "C0", "C3"])
    ax2.set_title("software-path latency budget (device output latency stacks on top — real run)")
    ax2.set_xlabel("milliseconds")
    for i, v in enumerate(vals):
        ax2.text(v, i, f" {v:.2f} ms", va="center")

    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# --- real device: blocksize sweep + end-to-end measurement --------------------

def _sweep_blocksizes() -> None:
    import sounddevice as sd

    print("\nblocksize / latency-hint sweep (the audio-side latency lever):")
    print(f"  {'requested':>12}  {'hint':>5}  {'stream.latency':>15}  {'observed frames':>16}")
    configs = [(0, "low"), (0, "high"), (128, None), (256, None), (512, None), (1024, None)]
    for bs, hint in configs:
        seen: list[int] = []

        def cb(outdata, frames, time_info, status):
            seen.append(frames)
            outdata.fill(0)

        kwargs = dict(samplerate=SR, channels=1, dtype="float32", callback=cb, blocksize=bs)
        if hint is not None:
            kwargs["latency"] = hint
        try:
            with sd.OutputStream(**kwargs) as s:
                time.sleep(0.3)
                lat_ms = s.latency * 1e3
                frames = sorted(set(seen))
            print(f"  {bs:>12}  {str(hint):>5}  {lat_ms:>12.2f} ms  {str(frames):>16}")
        except Exception as exc:                      # some backends reject some sizes
            print(f"  {bs:>12}  {str(hint):>5}  {'(failed: ' + str(exc)[:30] + ')':>15}")


def _measure_realtime_endtoend() -> None:
    import sounddevice as sd

    q = EventQueue()
    synth = PolySynth(q)
    records: list[tuple[float, float]] = []           # (push->drain, device out latency)

    def cb(outdata, frames, time_info, status):
        now = time.perf_counter()
        out_lat = time_info.outputBufferDacTime - time_info.currentTime
        for ev in q.drain():
            records.append((now - ev.t, out_lat))
            synth.handle(ev)
        outdata[:, 0] = synth.render(frames)

    print("\nend-to-end measurement (real OutputStream, latency='low') ...")
    with sd.OutputStream(samplerate=SR, channels=1, dtype="float32",
                         callback=cb, latency="low") as s:
        stream_lat_ms = s.latency * 1e3
        for i in range(40):                            # 40 note-ons at ~human cadence
            q.push(note_event(NoteKind.ON, 60 + i % 12))
            time.sleep(0.05)
            q.push(note_event(NoteKind.OFF, 60 + i % 12))
            time.sleep(0.05)
        time.sleep(0.1)

    on_records = [(d, o) for d, o in records if True]
    drains = [d for d, _ in on_records]
    outs = [o for _, o in on_records]
    ds, os_ = _stats_ms(drains), _stats_ms(outs)
    total = [d + o for d, o in on_records]
    ts = _stats_ms(total)

    print(f"  stream.latency (reported)  : {stream_lat_ms:.2f} ms")
    print(f"  (c) queue + block-quant    : mean {ds['mean']:.2f}  p99 {ds['p99']:.2f}  max {ds['max']:.2f} ms")
    print(f"  (d) device output (->DAC)  : mean {os_['mean']:.2f}  p99 {os_['p99']:.2f}  max {os_['max']:.2f} ms")
    print(f"  onset (c)+(d)              : mean {ts['mean']:.2f}  p99 {ts['p99']:.2f}  max {ts['max']:.2f} ms")
    print(f"      envelope attack (rise) : {ATTACK_MS:.1f} ms  (after onset, not added)")
    dominant = "device output (d)" if os_["mean"] >= ds["mean"] else "queue/block-quant (c)"
    print(f"  DOMINANT term: {dominant}.")
    print("  NOTE: the OS/USB/PyGame front-end (physical key -> event) is NOT included; "
          "measuring it needs an external mic-loopback rig.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="headless: software-path (push + queue) budget + PNG, no device")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        _sweep_blocksizes()
        _measure_realtime_endtoend()


if __name__ == "__main__":
    main()
