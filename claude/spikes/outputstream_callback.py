#!/usr/bin/env python3
"""
SPIKE: sounddevice OutputStream with a pull callback (mono, 5 s)

Question asked
--------------
Instead of ``sd.play`` (which hands the library one pre-rendered array), can we
drive audio the *streaming* way: open a ``sounddevice.OutputStream`` with a
callback, single channel, and generate exactly the number of wave samples the
callback asks for on each invocation? This is the shape the real app needs --
audio produced on demand, block by block, with no full buffer rendered up front.

What this does
--------------
Opens a mono ``OutputStream`` and, in the audio callback, synthesizes exactly
``frames`` samples of a continuous sine tone (440 Hz) -- the amount requested by
that callback, no more, no less. A running sample counter carried across calls
keeps the sine phase-continuous between blocks (the whole point: each callback
sees a *different* slice of the same never-ending waveform). The demo runs for
5 seconds of wall-clock time, then closes the stream cleanly.

Because the callback is invoked on a separate, real-time audio thread, it must
not allocate wildly, block, or throw -- so the generation here is a couple of
NumPy ops and an in-place write into the supplied ``outdata`` buffer.

Finding
-------
- Yes -- ``OutputStream(callback=...)`` pulls audio in variable-size blocks.
  ``frames`` is how many the device wants *this* call; generating exactly that
  many and writing them into ``outdata[:, 0]`` is all it takes for mono.
- ``outdata`` arrives shaped ``(frames, channels)`` and is NOT zeroed -- you own
  every sample; leaving it unfilled plays back stale garbage. Fill all of it.
- Phase continuity is on you: track an absolute sample index across callbacks and
  compute ``t`` from it. Restarting ``t`` at 0 each block clicks audibly.
- Block size, two separate lessons (this was the point of the spike):
    1. ``stream.blocksize`` on the stream object is NOT useful. It's just the
       value we *requested* -- with the default it reads back ``0`` ("let the
       backend decide"), which tells you nothing about the real block size.
    2. The real block size is the ``frames`` argument handed to the callback.
       Recording it is the only reliable way to know. Observed here: 575
       callbacks, each requesting exactly 383 frames (220225 samples over ~5 s).
- Constant-vs-varying block size: in this run ``frames`` was a steady 383, but
  that is NOT guaranteed. The API contract is "generate ``frames`` samples," and
  nothing promises ``frames`` stays constant for the life of the stream (device
  reconfig, backend/latency mode, xruns could all change it). So:
    * Always honor ``frames`` -- never hard-code a block length.
    * FUTURE POSSIBILITY: if our generator prefers a fixed work size (e.g. FFT
      frame, control-rate block) or block size ever does change mid-stream, we
      may need our own ring/queue buffer between the generator and the callback,
      so the callback just drains ``frames`` samples from our buffer regardless
      of what size it asks for. Not needed for this spike; noted for the app.
- Timing/threading gotchas:
    * The callback runs on a real-time thread. Print/allocate as little as
      possible; use ``sd.CallbackStop`` to end from inside, or just sleep in the
      main thread and close (done here).
    * ``status`` flags underruns -- worth watching; empty means the callback kept
      up with the device.
- The pull model (this spike) is what the app should build on; ``sd.play`` (the
  push model in piano_chord_major_minor.py) can't do open-ended, interactive audio.

Run
---
    python claude/spikes/outputstream_callback.py
"""

from __future__ import annotations

import time

import numpy as np
import sounddevice as sd

SR = 44100          # sample rate, Hz
FREQ = 440.0        # A4 -- a plain, unmistakable tone
AMP = 0.2           # keep it gentle on the ears
DURATION = 5.0      # seconds of wall-clock playback


def main() -> None:
    # Absolute count of samples emitted so far, carried across callbacks so the
    # sine stays phase-continuous. Boxed in a list because the callback closure
    # needs to mutate it (nonlocal would work too).
    frame_index = [0]

    # The `frames` value the device actually asked for on each callback. This is
    # the ONLY reliable source of truth for the block size -- see the finding.
    # A plain list append is fine here (amortized O(1), no reallocation storm).
    observed_blocksizes: list[int] = []

    def callback(outdata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            # Underrun/overrun etc. -- surface it but don't crash the audio thread.
            print(f"stream status: {status}", flush=True)

        observed_blocksizes.append(frames)

        # Generate EXACTLY `frames` samples -- the amount this callback requested.
        start = frame_index[0]
        n = np.arange(start, start + frames)
        wave = AMP * np.sin(2.0 * np.pi * FREQ * n / SR)

        # outdata is (frames, channels); this is a mono stream so channels == 1.
        outdata[:, 0] = wave.astype(np.float32)

        frame_index[0] += frames

    stream = sd.OutputStream(
        samplerate=SR,
        channels=1,          # single channel
        dtype="float32",
        callback=callback,
    )

    # NOTE: stream.blocksize here is just the value we *requested* (0 = "let the
    # backend decide"), NOT the size the callback will actually be handed. It
    # tells us nothing about the real block size -- only `frames` inside the
    # callback does. That's why we record `frames` above instead of trusting this.
    print(f"playing {FREQ:.0f} Hz for {DURATION:.0f}s via OutputStream callback "
          f"(requested blocksize={stream.blocksize}, latency={stream.latency:.4f}s) ...")
    with stream:
        time.sleep(DURATION)  # audio runs on its own thread while we wait here

    total = frame_index[0]
    print(f"done. callback emitted {total} samples "
          f"(~{total / SR:.2f}s of audio at {SR} Hz).")

    # Report the ACTUAL block sizes the callback observed.
    sizes = observed_blocksizes
    uniq = sorted(set(sizes))
    print(f"callbacks: {len(sizes)}")
    print(f"observed blocksize (frames) -- min={min(sizes)} max={max(sizes)} "
          f"distinct={uniq}")
    print(f"first few block sizes: {sizes[:8]}")
    if len(uniq) > 1:
        print("NOTE: block size varied across callbacks -- do not assume it's "
              "constant; on-our-side buffering may be needed (see finding).")


if __name__ == "__main__":
    main()
