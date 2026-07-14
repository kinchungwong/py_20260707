# focused spike — staged chord entry

**Status:** active (see `status_active.md`). The first focused spike.

## The question

Does staged chord entry play like *playing*, or like *programming*? The mechanics are
cheap to build; the real unknown is **feel**. Everything here is scoped to answer that —
not to pick a "best" commit gesture in the abstract.

Origin design: `claude/ui-designs/staged-chord-entry-hud.md`.

## Run

    .venv/bin/python focused-spikes/staged-chord-entry/main.py
    .venv/bin/python focused-spikes/staged-chord-entry/main.py --voice sine
    .venv/bin/python focused-spikes/staged-chord-entry/main.py --tuning ji --tonic A
    .venv/bin/python focused-spikes/staged-chord-entry/main.py --selftest   # headless, no device

Playing needs a real display + output device; `--selftest` opens neither (it drives the
chain headlessly and asserts a committed chord actually sounds and the HUD renders).

## Controls

- **Tab** — toggle live / staged (also the Mode button).
- **Note keys** — home row **a s d f g h j k l ; '** = the white keys (`a`..`j` span the
  middle octave C4..B4; `k l ; '` reach up), upper row **w e t y u o p** = the black keys
  between them. Live mode: press-and-hold to play. Staged mode: each key **stages** a note
  (a short sine audition fires); **Shift+key** toggles a staged note off ("forget").
- **q** / **\** — slide the input window down / up one semitone (either mode). It re-aims
  *future* input only; notes already held or committed keep their pitch. All three octaves
  are drawn; the blue bar marks where your keys currently point.
- **Space** (staged) — press-duration: a **short** tap **auditions** the staged chord (you
  hear it; it stays staged); **holding** it plays + **clears**. Sound fires on press. (The
  HUD **Play chord** button = play + clear.)
- **z x c v b n m** (bottom row) — the **chord launcher**: press a key to fire the saved
  chord bound to it (either mode, at its saved pitch); **Shift+key** — forget that slot.
- HUD buttons (mouse): **Play chord**, **Save chord** (binds the staged chord to the next
  empty launcher slot), **Release**.
- **Esc** / close window — quit. (Note: **q** shifts the window; it does **not** quit.)

Keyboard-first: the mouse drives only the HUD buttons, not the piano keys (v1 scope).

## What's baked in (spike-simple — the pinned decisions)

- **Feel-test slice + chord launcher**: persistent live⇄staged toggle + explicit Play-chord
  commit; **save-your-own chords across the bottom-row `z..m` launcher zone** (Save auto-picks
  the next empty slot; fires in both modes at saved pitch); no quasimode / timeout this round.
- **Input surface**: a 3-octave keyboard; the computer keys map to a slidable ~1.4-octave
  window over it (`layout.InputWindow`), moved a semitone at a time by `q`/`\` — the slide
  re-aims future input only, held/committed notes keep their pitch. (Added after the
  2026-07-11 eval; the library keyboard is fixed at 2 octaves, so the geometry is rebuilt in
  `layout.py` — `src/` stays untouched.)
- **Audition**: a `pygame.mixer` one-shot sine behind `_audition()` (library-free) — a
  deliberate second acoustic authority. Named debt: consolidate into `PolySynth` at
  graduation (see `status_active.md`).
- **Commit**: staged notes fire as fire-and-forget note-ons minted straight onto the
  `EventQueue` (`sounder_id = midi`, bypassing the router's held-model, no note-off) → they
  ring out on the piano voice's natural decay; focus-loss silences them.
- **Loop**: spike-owned `clock.tick(60)`; composes `pypiano_2607`, no edits to `src/`.

## Files

- `main.py` — entry, arg parsing, `--selftest`, and a short move-safe preamble that reaches
  the `shared/` trunk for the library-path bootstrap (`shared/bootstrap.py`).
- `staged_app.py` — state, mode-aware dispatch, the render loop, library wiring.
- `layout.py` — the 3-octave keyboard geometry + the slidable `InputWindow` (computer-key →
  midi mapping with the `q`/`\` shift).
- `hud.py` — the HUD strip (pygame-drawn) + multi-state keyboard painting.
- `audition.py` — the `pygame.mixer` one-shot audition (numpy + pygame only).

## Finding

### Human evaluation 2026-07-11_0648am, commit 18b5ae76

Overall, it feels consistent with spike objectives. However I cannot evaluate too deep into
it because as I mentioned my computer keyboard has too low simultaneity for a realistic
live mode input. In other words, we wouldn't get very far from programming mode anyway,
since the input hardware itself doesn't have good support for the playing mode.

I would like to prioritize a few next step improvements. The following improvements are
not sorted by priority; I will leave this to spike planning discussion.

I would like three octaves, with the computer keyboard row (asdf) assigned to the middle
of the displayed octaves. I would like to use the additional keys ("l", ";", "'", "o", "p")
to expand the set of piano keys I can use.

I would like to use "q" and "\" for shifting the computer key to piano key assignment;
each press shifts by one semitone.

As a reminder "Esc" is the application quit key, not "q"; worth writing down in end-user docs
(currently there's none).

For the staged mode, I would like to allow all third-row letter keys to be available,
mostly to overcome the simultaneity problem. That means from "z" to "m" will be available
as presets.

I would like to reserve the duration of keyboard key presses for something else. For now,
my initial ask is that, in staged mode, the length of space bar press can be used for
two intentions: very short press-and-release: audition the current chord without clearing;
when pressed for a longer time, it will play normally and also clears afterwards.

I would like to see a new HUD space where the history of chords can be seen, so that even
if I didn't save the chord, I can still restore (recall by mouse click) from the history.

Mouse hasn't been wired up for most things; going forward, we might need some coarse-to-fine
scaffolding for the mouse cursor hit test (collidepoint) for on-screen gadgets.

I also come to a realization as a music newbie. When recalling a tune or melody from my
memory, I tend to recall the melody contour, not sure whether it corresponds to the base
note or not. In terms of temporal data entry, one can be allowed to audition-commit the
base notes of a melody, which will be visualized, and then each note can be further
customized with chords, changes to start time and duration, etc.

Some of the ideas listed here belong to future spikes; our next spike discussion should
sort out what stays and what gets pushed to the next.

Look forward to evaluating again soon.

### Human evaluation 2026-07-13 — chord launcher

Evaluated the chord-launcher iteration (save-your-own chords across the `z–m` zone; Save
auto-picks the next empty slot; a launcher key fires its chord in both modes at saved pitch;
Shift+key forgets). Code tested headlessly (selftest green, piano + sine) and in a live
session.

- **Core question:** it starts to feel like it can play some *interesting chords* — a
  promising sign that one-key-to-many pulls this away from "programming".
- **Audition (staged mode) needs more work.** When short-vs-long press lands (the
  press-duration primitive, plan step 2), we'll need to verify it behaves correctly for
  *each type* of keyboard key — behaviour may differ from key to key.
- **Firing in both modes:** forgot to test this round — revisit next time.
- **Visibility of stored chords is the main gap.** Eventually we need a **mini-map / display
  surface** for the saved chords so *correcting mistakes* is easy: e.g. a 6-note chord with
  one wrong note currently takes real memory and effort to fix. A proper display area would
  also subsume the one-line-toast HUD limitation.
- **Parked tweak (fine-tune later, not urgent):** shorten the full note duration in staged
  mode to ~1.5 s.

Overall: the core mechanic feels right; the next pressures are audition / press-duration
correctness and on-screen visibility for editing.
