# Current tasks

## Synthesis

- [x] Spike: prove piano major (C-E-G) vs minor (C-Eb-G) chord synthesis through
      sounddevice, no PyGame. → `../spikes/piano_chord_major_minor.py`;
      recipe in `../memory/piano-note-synthesis-recipe.md`.
- [x] Spike: extend to microtonal triads — major/minor/augmented/diminished/
      **neutral** via cents-above-root. → `../spikes/microtonal_triads.py`;
      approach in `../memory/chords-as-cents-above-root.md`. Confirms the
      cents-based frequency source generalizes the synth beyond 12-TET.
- [x] Spike: headless FFT plots of the chord wavs → PNG (matplotlib Agg, no
      GUI/X/Wayland/TTY). → `../spikes/fft_plots.py`; technique in
      `../memory/headless-matplotlib-png.md`. `fft_triads_compare.png` shows the
      shared root, moving third, and aug/dim fifth in one view.
- [ ] Promote the spike's `synth_note` / `synth_chord` into a real, tested module
      (pytest). Decide the module boundary before coding — likely a `Note` render
      function separate from mixing/normalization. Adopt cents-above-root as the
      chord API (see memory), not MIDI integers.
- [ ] Future spike: just-intonation color — derive cents from frequency ratios
      (e.g. neutral third 11/9 ≈ 347.4c) instead of a fixed cent grid.

## Notes

- Blocked/open: none yet. See `../vision/` for the latency and tuning constraints
  these tasks must respect.
