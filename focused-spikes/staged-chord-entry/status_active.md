# status: active

- Started 2026-07-10 — the first focused spike.
- Origin design: `claude/ui-designs/staged-chord-entry-hud.md`
  (from `claude/discussions/2026-07-10/keyboard-and-input-surface.md`).

## Progress

- **Chord launcher implemented (2026-07-13)** — step 1 of
  `../../claude/plans/programming-modes-buildout.md`. The single `Z` preset is generalized
  into save-your-own chords across the bottom-row `z..m` launcher zone: Save auto-picks the
  next empty slot; a launcher key fires its chord in **both** modes at saved absolute pitch;
  Shift+key forgets. `layout.KeyZone` adds the row-delimited zone model. `--selftest` covers
  save→next-slot, both-mode fire, and forget. HUD shows a one-line slot readout — a fuller
  status area is deferred (see the task sidecar's known limitation).
- **Press-duration primitive (2026-07-13)** — step 2. A reusable, clock-injectable
  `PressTimer` (`press.py`) classifies key holds short vs long; wired to the staged-mode
  space bar: short = audition (keeps staged), long = play + clear, with the sound firing on
  KEYDOWN. Threshold `SPACE_LONG_S` (default 0.2 s) confirmed "good enough for now" in a live
  session. `--selftest` covers both branches via an injected clock. Liftable to `shared/`
  when the melody spike reuses it. **Extended to staged NOTE keys** (user feedback): a short
  tap auditions only, a long hold auditions + stages — one idiom (short = trial, long =
  commit) across the trial→record flow.
- **Mouse hit-test core (2026-07-14)** — step 3 (dependency **B**). A coarse-to-fine
  `(region, gadget)` resolver (`hittest.py`): `pick(pos, regions)` walks topmost-first
  `RegionSpec`s and the first whose coarse rect contains the point claims it (opaque, no
  fall-through), returning `(Region, payload)` — an action string for HUD, a midi for the
  keyboard, or `None` for region background. Two regions wired (HUD honours mode via its
  closure; KEYBOARD reuses the library's black-first `hit_test`); the `MOUSEBUTTONDOWN`
  path now routes through it. **Structural only — no behaviour change:** HUD buttons act as
  before; a piano-key hit is resolved but is a documented no-op **seam for step 4**.
  Launcher-slot clickability stays out (its readout sits inside the HUD strip — step 4 /
  pane refactor). `--selftest` asserts resolution: HUD button→action, HUD background→None,
  a staged-only button inert in live mode, white→midi, black-over-white order guard, and
  below-keyboard→None. Liftable to `shared/` when the melody spike (step 6) needs it.
- **Mouse in staged mode (2026-07-14)** — step 4 (dependency **C**), the **last piece in
  scope for this spike**. Fills step 3's `Region.KEYBOARD` seam: the mouse now drives the
  piano keys in both modes via the `mouse_input` glissando drag model (one active mouse
  note). **Live** = sustained play through the router (down = press, drag = glissando,
  empty/up = off). **Staged** = audition on button-down, **stage on button-up iff the
  gesture ends on the key it began on** (a drag away cancels; the down-audition is the
  feedback); **Shift+click** toggles/forgets (auditions when it stages). Never `set_grab`;
  focus-loss clears any in-flight gesture too. Launcher-slot clicking is **deferred to step
  5 (F)** (Save/Play/Release stay on the HUD buttons). `--selftest` covers live glissando
  (incl. drag-to-empty and back) and staged click-stage / drag-cancel / drag-out-and-back /
  shift-toggle; piano + sine green, `run_spike_tests.py` 14/14, mypy + pyright clean. Sidecar:
  **[`../../claude/tasks/mouse-in-staged.md`](../../claude/tasks/mouse-in-staged.md)**.
- **Resting point (2026-07-14).** Chord launcher + press-duration are feel-evaluated
  (positive verdict); the mouse hit-test core + mouse-in-staged (step 4, C) are built and
  selftest-green. **C is code-complete and selftest-green but pending the human gate**
  (manual test on a real device + manual review, then commit) per
  [`../../claude/memory/process/c-review-and-merge-handoff.md`](../../claude/memory/process/c-review-and-merge-handoff.md).
  With C done, this spike is complete; everything after is a new spike: **editing saved
  chords** (the stored-chord visibility / editing surface) is folded into **UI pane
  modularization**, sequenced as **plan step 5 (F)** between C and D, then **melody mode
  (step 6, D)**. Per-key-type press-duration check on real hardware still open.

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
