# Input→sound latency: `latency='low'` is the lever; device output dominates

Measured end to end on the wired instrument path by the `input_to_sound_latency`
spike (`../../../spikes/input_to_sound_latency.py`, real device: pipewire/ALSA on
the dev box). Serves the vision's low-latency non-negotiable.

## The budget (keypress → first sample at the DAC)

| term | what | measured |
|---|---|---|
| (b) dispatch + queue push | GUI thread work | ~0.1 µs — negligible |
| (c) queue + block-quantization | wait for next callback drain | ~half a block |
| (d) **device output latency** | drain → DAC | **~11.4 ms mean — DOMINANT** |
| envelope attack | rise time *after* onset | 6 ms (not an onset delay) |

With `latency='low'`: onset (c)+(d) ≈ **12.9 ms mean, ~19 ms p99**. (c) collapses
to ~1.5 ms because the blocks are tiny (~2.15 ms), vs ~4.4 ms with the default
383-frame block.

## The one actionable decision: open the stream with `latency='low'`

The blocksize/latency sweep (the whole point of the spike):

| requested | hint | stream.latency | block |
|---|---|---|---|
| 0 | **low** | **8.62 ms** | 95 frames (~2.15 ms) |
| 0 | high | 34.74 ms | 383 |
| 0 | *(default = no hint)* | ≈ high ≈ 35 ms | 383 |
| 128 / 256 / 512 | none | **all ~34.83 ms** | as requested |
| 1024 | none | 23.22 ms | 1024 |

- **Requesting a small blocksize does NOT lower latency** — 128 and 512 both sat at
  ~34.83 ms. The output buffer is a fixed ~35 ms unless you pass `latency='low'`.
  Hand-tuning blocksize is a trap (and 1024 was non-monotonic — backend quantization).
- So: **`latency='low'` is committed** for the app's OutputStream — a ~4× cut on the
  dominant term (~35 → ~9 ms). Applied to `playable_instrument`; the earlier demo
  spikes still use the default and thus run ~4× slower on (d).
- Don't hard-code the resulting block size: `latency='low'` yielded 95-frame blocks
  here, but it's backend-chosen and variable — honor the callback's `frames` (see
  [[blocksize]]).

## Caveats

- **Tail = where CPython bites.** (c) had a max ~27.8 ms (mean 1.5, p99 7.9) from
  occasional scheduling/GC jitter. The mean is great; the worst case is the risk
  the vision flags about Python. Watch it under load / polyphony.
- **Front-end unmeasured.** Physical key → PyGame delivers the event (OS/USB/SDL)
  is *not* in these numbers; measuring it needs an external mic-loopback rig. Note
  we use `pygame.event.wait()`, so there's no added input-*poll* interval.

## Related

- Block cadence + "honor `frames`, don't hard-code": [[blocksize]] (sibling fact).
- The path these terms are measured across: [[signal-chain]]; the (c) term is the
  [[event-queue]] transit latency, framed as an input-latency budget.
- The `perf_counter()` stamp measured against is captured at emit: [[note-event-reconciliation]].
