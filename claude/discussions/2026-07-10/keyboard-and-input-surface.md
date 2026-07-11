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

## Vocabulary from working musicians and synth-heads (2026-07-10)

Real terms that map onto ideas raised in this discussion — captured so we don't
reinvent names for concepts that already exist:

- **Voicing / comping / block chord vs. broken chord / arpeggio** — general
  chord-and-composition vocabulary; block vs. broken is the simultaneous-vs-staggered
  distinction, already named.
- **Rolled chord** — notation term for a chord *deliberately* played with a staggered
  onset (wavy-line notation). Staggered-but-intended-as-one-gesture is already a
  first-class musical idea, not just a hardware workaround.
- **Chord mode / chord memory / "one-finger chord"** (arranger-organ terminology,
  historically the **Chord Organ**) — one key/button sounds a full chord. **This is our
  "one key programmed to sound multiple notes" idea** — well-trodden synth ground, with
  existing UX conventions to borrow.
- **Layering / stacking** a patch (one key → multiple voices) vs. **unison** (one key →
  multiple voices, same note, detuned) — the synth-voice-mode vocabulary (**poly / mono
  / unison**) sits next to but distinct from "chord."
- **Hold / Latch** — the standard arpeggiator/synth button: trigger once, the note(s)
  sustain without holding the key, freeing hands to add more. This is the real product
  term for the "latch" idea already in this file's "Two directions in tension" section.
- **Split / Zone** — different key ranges bound to different sounds/behaviors.
- **Real-time (performance) recording vs. step-time / step entry ("step sequencing",
  often a literal mode called "Step Input")** — the term of art for "notes entered at
  different real-world times but meant as one musical instant": the transport is
  effectively frozen at a position while you build up everything that fires *at that
  instant*, one item at a time, then it plays back collapsed onto one place in musical
  time.
- **Quantize / quantization** — the softer cousin: real-time-but-slightly-staggered
  entry, snapped onto a shared grid after the fact.
- **Notation software's chord-tone entry** (select one rhythmic position, add pitches to
  it one at a time) — probably the cleanest analogy for typing around the keyboard
  ceiling with the *intent* of simultaneity.
- **Transport** (running vs. stopped) — the umbrella word for "is UI-now the same as
  music-now," i.e. the modality switch this discussion asked about.

## Where new exploratory code goes (open structural question)

`claude/spikes/` is confirmed **frozen** (`git diff claude/spikes` clean) and its test
harness (`../../../tools/run_spike_tests.py`) hardcodes the directory and an explicit
file list — new exploratory code (keyboard-interaction prototypes, etc.) needs a
**sibling directory**, not a place inside it.

**Decided (2026-07-10):** don't pre-reserve a `spikes2`-style directory now. When a new
exploratory arc actually starts, create **one sibling directory named for that arc's
topic** (e.g. `claude/spikes-keyboard-input/`), matching how individual spike files are
already named for the question they ask rather than a sequence number. Each future arc
(keyboard input, microtonality, maybe a pedagogy reconstruction) gets its own directory
when *it* begins — not all reserved up front. The convention itself gets written down in
that new directory's own README when it's created — deliberately **not** by editing
`claude/spikes/README.md`, to keep that directory's clean frozen-diff record intact.

## Archetype 5: chord-mode + staged entry (hybrid, 2026-07-10)

Combines both of the user's ideas: a key can be **programmed to fire a whole chord**
(chord-mode preset — expands total simultaneous notes without more physical keys)
**and/or** notes can be **entered into a pending chord over real time**, fired together
by an explicit **commit** gesture (staged/step entry). See the vocabulary section above
for the real terms this borrows from (chord mode, Hold/Latch, step input).

**Candidate commit gestures** (none chosen yet):

1. **Modifier-held, release-fires** — hold a dedicated key while tapping notes;
   releasing fires the assembled chord. Accordion/organ-chord-button feel.
2. **Explicit commit key** — tap notes into a silent buffer, a separate key fires it.
   Two clearly separated phases (build, then play).
3. **Timeout window (auto-commit)** — notes within ~100-150ms fire together, no
   gesture at all. Not really staged entry — **widened quantize** at the input layer;
   assisted simultaneity, no mode switch, but a hidden tolerance that could surprise.
4. **True mode toggle (transport-style)** — an explicit "staged" mode (mirrors a DAW's
   Step Input) with no time pressure, then flip back to "live" to fire. Most literal
   translation of the sequencer concept, and the most different from just playing.

**Synthesis worth keeping:** staged entry is a natural **authoring path for chord-mode
presets** — build a chord slowly once via staging, bind the result to a key for instant
one-press recall after. Mirrors how arranger keyboards let users program custom chord
buttons: build-once, trigger-fast.

**Open sub-axis:** feedback while staging — audition each note as it's added (typing-
echo feel) vs. silent buffer until commit (cleaner "chord" semantics, more surprising).

**What a first spike should actually test:** the mechanics above are all cheap to build;
the real unknown is **feel** — does any commit gesture play naturally, or does staged
entry always feel like "programming" rather than "playing"? A first
`claude/spikes-keyboard-input/` experiment (name TBD when started, see "Where new
exploratory code goes" above) should be scoped around *that* question, not around
picking one gesture in the abstract.

## Open questions

- Is the goal to make QWERTY *playable as an instrument*, or to *transcend* it —
  keyboard for structure/commands, pitch expression elsewhere?
- How far do we lean on **state / latching** versus real-time holding?
- Do **other input surfaces** (MIDI controllers, gamepads, touch, ribbons) belong in
  this conversation, or is each its own future spike?
- Constraint that shapes all of it: **never confine the cursor or keyboard**
  (`../../policy/input-policy.md`) — focus-loss ⇒ all-notes-off, never a grab.
