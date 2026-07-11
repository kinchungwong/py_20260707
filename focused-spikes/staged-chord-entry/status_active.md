# status: active

- Started 2026-07-10 — the first focused spike.
- Origin design: `claude/ui-designs/staged-chord-entry-hud.md`
  (from `claude/discussions/2026-07-10/keyboard-and-input-surface.md`).

## Named debt — consolidate at graduation

Auditions use a lightweight `pygame.mixer` one-shot sine (`audition.py`) — a deliberate
SECOND acoustic authority, taken on knowingly to keep the spike simple. It is kept behind
`_audition()` in `staged_app.py` so it swaps in exactly one place. **Fold it into the
library's `PolySynth` when this spike graduates**, so there is a single authority for
acoustics.
