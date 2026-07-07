#!/usr/bin/env python3
"""
SPIKE: Headless FFT plots of the chord .wav files (matplotlib -> PNG)

Question asked
--------------
Can we render FFT (magnitude-spectrum) plots of the individual chord wav files
produced by the earlier spikes, entirely **headless** -- no GUI, no interactive
backend, no TTY -- and save them as PNG?

Answer: yes. Force matplotlib's non-interactive **Agg** backend *before* importing
pyplot; then `figure.savefig(...)` writes a PNG without ever opening a window.

What this does
--------------
For each single-chord wav (skips the multi-chord `*_sequence.wav`):
  * loads mono PCM via the stdlib `wave` module (no scipy),
  * takes a windowed sustain segment and computes an rfft magnitude spectrum,
  * plots spectrum (dB) 0-3000 Hz with the strongest partials labelled, plus a
    small zoomed waveform panel to show the piano-like attack/decay,
  * saves `fft_<stem>.png`.
Also saves `fft_triads_compare.png`: the five triads' spectra overlaid in the
240-440 Hz region, so the moving third (and aug/dim fifth) are visible at a glance.

Finding
-------
- Yes. Headless PNG rendering works with DISPLAY *and* WAYLAND_DISPLAY unset and
  stdin detached (`< /dev/null`). Proof: Agg's `required_interactive_framework`
  is None (it is not a GUI backend), and importing it pulls in NO
  tkinter/GTK/Qt/wx/X11/Wayland modules. It rasterizes in software and writes
  PNG via libpng -- the Linux window environment is never involved.
- The two rules that make it headless-safe:
    1. `matplotlib.use("Agg")` BEFORE `import matplotlib.pyplot`.
    2. Use `figure.savefig(...)`; never `plt.show()`.
  (Equivalent alternative: set env `MPLBACKEND=Agg`.)
- The plots confirm the theory visually: all five triads share the root (~262 Hz);
  thirds fan out 311 (dim/min) / 320 (neutral, dead centre) / 330 (maj/aug);
  fifths split 370 (dim) / 392 (perfect) / 416 (aug). Inharmonic partial spread
  is visible in the individual spectra.
- Gotcha (cosmetic): the three chord fundamentals sit close in Hz, so their peak
  labels crowd on the individual plots. Left as-is for a spike; a real plotter
  would stagger labels or widen min-separation.

Run
---
    python claude/spikes/fft_plots.py
"""

from __future__ import annotations

import glob
import os
import wave

import numpy as np

import matplotlib
matplotlib.use("Agg")          # headless: pick the non-interactive backend FIRST
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def load_wav(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        return pcm.astype(np.float64) / 32767.0, w.getframerate()


def spectrum(sig: np.ndarray, sr: int, start: float = 0.05,
             length: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """dB magnitude spectrum of a Hann-windowed sustain segment (skips attack)."""
    i0 = int(start * sr)
    seg = sig[i0: i0 + int(length * sr)]
    if len(seg) < 8:
        seg = sig
    seg = seg * np.hanning(len(seg))
    mag = np.abs(np.fft.rfft(seg))
    freq = np.fft.rfftfreq(len(seg), 1.0 / sr)
    db = 20.0 * np.log10(mag / (mag.max() + 1e-12) + 1e-12)
    return freq, db


def top_peaks(freq: np.ndarray, db: np.ndarray, fmax: float = 3000.0,
              n: int = 6, floor: float = -45.0, min_sep: float = 20.0) -> list[int]:
    """Indices of the n strongest local maxima above `floor`, spaced >= min_sep Hz."""
    m = (freq <= fmax) & (db > floor)
    peak = m.copy()
    peak[1:-1] &= (db[1:-1] >= db[:-2]) & (db[1:-1] >= db[2:])
    idx = np.where(peak)[0]
    idx = idx[np.argsort(db[idx])[::-1]]
    chosen: list[int] = []
    for i in idx:
        if all(abs(freq[i] - freq[j]) >= min_sep for j in chosen):
            chosen.append(i)
        if len(chosen) >= n:
            break
    return sorted(chosen, key=lambda i: freq[i])


def plot_one(path: str) -> str:
    sig, sr = load_wav(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    freq, db = spectrum(sig, sr)

    fig, (ax_s, ax_w) = plt.subplots(
        2, 1, figsize=(9, 5.5), gridspec_kw={"height_ratios": [3, 1]})

    ax_s.plot(freq, db, lw=0.9, color="#1f6feb")
    ax_s.set_xlim(0, 3000)
    ax_s.set_ylim(-80, 3)
    ax_s.set_xlabel("frequency (Hz)")
    ax_s.set_ylabel("magnitude (dB)")
    ax_s.set_title(f"{stem} — FFT magnitude spectrum")
    ax_s.grid(True, alpha=0.25)
    for i in top_peaks(freq, db):
        ax_s.annotate(f"{freq[i]:.0f}", (freq[i], db[i]),
                      textcoords="offset points", xytext=(0, 4),
                      ha="center", fontsize=8, color="#c9510c")
        ax_s.plot(freq[i], db[i], ".", color="#c9510c", ms=5)

    # small waveform panel: first 40 ms, to show the piano attack/decay shape
    n = int(0.040 * sr)
    t = np.arange(n) / sr * 1000.0
    ax_w.plot(t, sig[:n], lw=0.7, color="#555")
    ax_w.set_xlim(0, 40)
    ax_w.set_xlabel("time (ms)")
    ax_w.set_ylabel("amp")
    ax_w.grid(True, alpha=0.25)

    fig.tight_layout()
    out = os.path.join(HERE, f"fft_{stem}.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def plot_triads_compare(paths: list[str]) -> str | None:
    triads = {os.path.splitext(os.path.basename(p))[0].replace("triad_", ""): p
              for p in paths if os.path.basename(p).startswith("triad_")}
    order = [q for q in ("major", "minor", "augmented", "diminished", "neutral")
             if q in triads]
    if not order:
        return None

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = {"major": "#1f6feb", "minor": "#8250df", "augmented": "#c9510c",
              "diminished": "#1a7f37", "neutral": "#bf3989"}
    for q in order:
        sig, sr = load_wav(triads[q])
        freq, db = spectrum(sig, sr)
        ax.plot(freq, db, lw=1.2, label=q, color=colors.get(q))
    # reference lines: shared root C4, and the region where third/fifth move
    ax.axvline(261.6, ls=":", color="k", alpha=0.4)
    ax.annotate("root C4", (261.6, 1), fontsize=8, ha="center")
    ax.set_xlim(240, 440)
    ax.set_ylim(-60, 3)
    ax.set_xlabel("frequency (Hz)  —  third & fifth region")
    ax.set_ylabel("magnitude (dB)")
    ax.set_title("Five triads overlaid: shared root, moving third, aug/dim fifth")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    out = os.path.join(HERE, "fft_triads_compare.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main() -> None:
    wavs = sorted(glob.glob(os.path.join(HERE, "*.wav")))
    individual = [p for p in wavs if not p.endswith("_sequence.wav")]
    if not individual:
        raise SystemExit("no single-chord .wav files found — run the chord spikes first")

    print(f"backend: {matplotlib.get_backend()}  (headless, no GUI/TTY)")
    for p in individual:
        out = plot_one(p)
        print(f"wrote {os.path.relpath(out, HERE)}")

    cmp_out = plot_triads_compare(individual)
    if cmp_out:
        print(f"wrote {os.path.relpath(cmp_out, HERE)}")


if __name__ == "__main__":
    main()
