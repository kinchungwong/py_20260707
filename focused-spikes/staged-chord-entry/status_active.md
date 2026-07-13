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

## Known bug — shared acoustic identity cuts a fired note short (low)

`sounder_id = midi` for BOTH a router-held live note and a fire-and-forget committed/preset
note. So if you hold a live key at a pitch that is also in a fired preset and then release
the live key, its note-off addresses the shared sounder and silences the still-ringing fired
note (and leaves a stale entry in `_ringing`, which is benign). Found + confirmed by the
Feature-1 adversarial review (2026-07-11). Pre-existing (not introduced by the input window),
low severity, confined to the deprioritized live mode. **Not fixed on purpose:** a real fix
means giving fired notes a distinct acoustic identity, which is the same acoustic-identity
rework the audition→`PolySynth` consolidation above already owns — do it there, not piecemeal.
(The sibling live-mode collision — two computer keys landing on one pitch after a shift — WAS
fixed, since the window introduced it and the fix is a local pitch-refcount in the KEYUP path.)
