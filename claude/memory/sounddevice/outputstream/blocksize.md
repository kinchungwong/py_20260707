# sounddevice OutputStream — block size is only knowable from the callback

Discovered by the pull-model spike
(`../../../spikes/outputstream_callback.py`, mono `OutputStream(callback=...)`,
5 s run). Two lessons about "how many samples do I generate per callback?" plus
one forward-looking consequence.

## Lesson 1 — `stream.blocksize` on the stream object is NOT useful

It only echoes the value we *requested*. With the default (`blocksize=0`,
"let the backend decide") it reads back `0`, which tells you nothing about the
real per-callback size. Don't drive any logic off `stream.blocksize`.

## Lesson 2 — the real block size is the `frames` argument to the callback

The `frames` value passed into the audio callback is the only reliable source of
truth. Generate exactly `frames` samples and write them into `outdata[:, 0]`
(mono). Observed in the spike: **575 callbacks, each requesting exactly 383
frames** (≈ 220225 samples over ~5 s at 44100 Hz). So on this machine the size
was *constant at 383*, even though `stream.blocksize` reported `0`.

## Consequence / future possibility — may need our own buffering

`frames` was steady at 383 in that run, but **nothing in the API guarantees it
stays constant** for the life of the stream (device reconfig, backend/latency
mode, or xruns could change it). The contract is just "produce `frames` samples,"
so:

- **Always honor `frames`.** Never hard-code a block length.
- **If our generator prefers a fixed work size** (FFT frame, control-rate block),
  **or if block size ever changes mid-stream**, we will likely want our own
  ring/queue buffer between the generator and the callback — the callback then
  just drains `frames` samples from our buffer regardless of the size asked for.
  Not needed yet; noted so the app design leaves room for it.

## Related

- Push model (whole array up front) via `sd.play`: see
  [[piano-note-synthesis-recipe]]. The pull model here is what open-ended /
  interactive audio should build on.
