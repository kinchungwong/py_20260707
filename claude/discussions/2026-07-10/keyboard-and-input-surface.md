# Topic: the computer keyboard — living with its limits, and going beyond

*A discussion note: current knowledge + open questions. Not a decision, not a plan.*

## The hard fact we're reconciling with

Playing the finished app on real hardware surfaced a **physical ceiling** in commodity
computer keyboards (recorded in the milestone retro,
`../../retrospectives/2026-07-10-d.md`):

- Simultaneous-key registration is **limited and uneven.** Some combinations register
  up to ~6 keys at once; but **specific 3-key combinations**, once held, block *any*
  further key from registering.
- This is **keyboard-matrix rollover / jamming** — it depends on the exact set of keys
  and **varies from keyboard to keyboard**. It cannot be papered over in software.

**Consequence:** the QWERTY keyboard is **not a reliable polyphonic/chordal surface.**
Which notes can sound together depends on the physical wiring of the particular
keyboard, and some combinations are simply unreachable.

## What we already have to build on

- **`InputRouter` is multi-source by design** — it reconciles note-on/off from more
  than one input and mints Hz at the edge, so new input surfaces are architecturally
  anticipated, not bolted on (`../../memory/architecture/synth-core-library.md`).
- **Mouse glissando already gives continuous pitch** (`MouseGlissando`) — a working
  input path that owes nothing to the key matrix.
- **The synth is frequency-native** — nothing downstream assumes 12 keys, or even that
  pitches are discrete, so the input surface is free to be almost anything.

## Two directions in tension (both on the table)

**A. "Despite" — make the keyboard usable within its ceiling.** Discussion-starters,
not recommendations:
- **Note latching / hold modes**, so you don't have to physically hold every key.
- **One-key-to-many**: a key triggers a whole chord, an arpeggio, or a scale degree
  rather than a single pitch — sidestepping the simultaneity limit.
- **Per-keyboard calibration**: detect a given keyboard's dead combinations and remap
  around them.
- **Spacebar-as-sustain** and other "pedal" analogs — expression without adding
  simultaneous keys.

**B. "Supercharge" — make the surface *more* expressive than a naive piano mapping.**
- Treat the keyboard as a **command / gesture surface**, not a 1:1 piano — modal
  layers, key *sequences* as gestures, timing → velocity.
- Because we're freq-native, keys can map to **scale degrees, ratios, or isomorphic
  layouts** instead of 12-TET semitones — which ties straight into the microtonality
  topic (`microtonality.md`).
- Put **continuous expression on a different surface** (mouse now; other controllers
  later) and let the keyboard do what it's genuinely good at: discrete, reliable
  triggering.

## Open questions

- Is the goal to make QWERTY *playable as an instrument*, or to *transcend* it —
  keyboard for structure/commands, pitch expression elsewhere?
- How far do we lean on **state / latching** versus real-time holding?
- Do **other input surfaces** (MIDI controllers, gamepads, touch, ribbons) belong in
  this conversation, or is each its own future spike?
- Constraint that shapes all of it: **never confine the cursor or keyboard**
  (`../../policy/input-policy.md`) — focus-loss ⇒ all-notes-off, never a grab.
