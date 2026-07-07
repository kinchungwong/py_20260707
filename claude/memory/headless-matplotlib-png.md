# Headless matplotlib → PNG (no GUI, no X/Wayland, no TTY)

Rendering matplotlib figures to PNG on this project's Linux box works with **no
window environment at all** — proven by the FFT-plot spike
(`../spikes/fft_plots.py`). Use this whenever a spike/tool needs to emit plots
non-interactively (CI, headless runs, agent-driven runs).

## The two rules

1. Select the **Agg** backend *before* importing pyplot:
   ```python
   import matplotlib
   matplotlib.use("Agg")          # must precede the next line
   import matplotlib.pyplot as plt
   ```
   (Equivalent: set the environment variable `MPLBACKEND=Agg`.)
2. Write with `fig.savefig("out.png")`. **Never call `plt.show()`** — that's the
   only thing that would want an interactive/GUI backend.

## Why it's genuinely headless (verified)

- Agg is a pure software rasterizer → libpng. It is **not** a GUI backend:
  `FigureCanvasAgg.required_interactive_framework is None`.
- With `DISPLAY` and `WAYLAND_DISPLAY` both unset and stdin `< /dev/null`, it
  still produces valid PNGs, and importing it pulls in **no**
  tkinter/GTK/Qt/wx/X11/Wayland modules.

## Env facts (as of 2026-07-07)

- `matplotlib` 3.11.0 in the project venv. No scipy — load WAVs with the stdlib
  `wave` module (see [[piano-note-synthesis-recipe]]).
