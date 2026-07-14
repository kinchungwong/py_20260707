# Speculation — isomorphic / hexagonal keyboard geometry as the microtonal endpoint

**Status: speculation, not a committed decision.**
**Committed baseline: the traditional 12-TET piano layout** — a 1D row of
white/black keys, as built in the staged-chord-entry spike
(`../../focused-spikes/staged-chord-entry/layout.py`) and mapped onto by the
computer keyboard. This file parks the *alternative* geometry so we revisit it
with the reasoning intact instead of re-deriving it.

## The idea

Keyboard **geometry** is a spectrum, and the piano sits at the far-left (least
capable) end. Moving right grants three things at once — the layout is the *root*
variable, not three separate problems:

| Layout | Dims | Keys uniform? | Transpositionally invariant? | Microtonal live play? | Examples |
|---|---|---|---|---|---|
| **Traditional piano (12-TET)** | 1D | ✗ (white/black) | ✗ | ✗ | acoustic piano — **our baseline** |
| Uniform chromatic row | 1D | ✓ | ✓ | ✓ but *too long* for big EDOs | one guitar string, single-row buttons |
| Square isomorphic | 2D square | ✓ | ✓ | partial (square "degeneration") | Jankó-ish grids |
| **Hexagonal isomorphic** | 2D hex | ✓ | ✓ | ✓ **(the sweet spot)** | Wicki-Hayden, Harmonic Table / Tonnetz, Lumatone |

**Established vocabulary** this pins down (so we stop using made-up terms):
- **Transpositional invariance** — a chord/interval has the *same shape* in every
  key. This is the property that dissolves the white/black-shift headache recorded
  in `../discussions/2026-07-13/chord-launcher-and-programming-modes.md`.
- **Diatonic transposition** (stay in key, no accidentals) + **circle-of-fifths**
  navigation (the fifth is the efficient coverage interval) — the structural
  "spatial access" axis.
- **Pitch bend** — the *expressive*, temporary, self-centering pitch move; a
  distinct axis from transposition (the "effect" idea).

**Key correction to keep honest:** transpositional invariance is *cheap* — even a
1D row of **uniform** keys (a guitar string) has it. The piano forfeits it not for
being 1D but because its keys aren't uniform. So hexagonal 2D is not the *simplest*
geometry that yields invariance; it is the *optimal* one for **microtonal live
play**, because (1) hex gives 6 adjacent neighbors vs. a square's 4 → more
intervals sit adjacent → compact chord shapes; (2) square lattices "degenerate"
(can't hold all isomorphic mappings) while hex can; (3) 2D keeps 31/41/53-EDO
reachable where a 1D piano "runs out of keys."

## Why we might want it later

- **It's the natural home for the microtonality vision** already discussed
  (`../discussions/2026-07-10/microtonality.md`): a freq-native synth with no
  assumption of 12 discrete keys is *already* pointed at this — the input surface
  is the missing half.
- **It retires several problems at once**: the semitone-shift-breaks-the-layout
  issue, transposition-changes-fingering, and "the piano runs out of keys for big
  EDOs" are all downstream of geometry.
- The synth core is frequency-native, so nothing downstream blocks it
  (`../discussions/2026-07-10/keyboard-and-input-surface.md`).

## Costs / trade-offs (why it isn't the baseline)

- **Hardware mismatch.** Our actual input device is a QWERTY keyboard — a
  piano-like non-uniform 1D surface. A hex isomorphic grid wants a hex button
  field (Lumatone-class) or a careful on-screen emulation; mapping it onto QWERTY
  re-introduces the very simultaneity/rollover ceiling that drove the
  programming-modes pivot.
- **Big redesign, far from current goals.** The app today is a 12-TET piano demo;
  chord-launcher + programming modes are the near-term work
  (`../plans/programming-modes-buildout.md`). Geometry is a much later question.
- **Learnability.** Isomorphic layouts trade "same shape everywhere" for an
  unfamiliar surface — a real onboarding cost for a newbie-facing tool.

## Trigger to revisit

Reopen this when **either**:
- **microtonal live play becomes a real goal** (beyond the parked microtonality
  discussion) — i.e. we actually want to *perform* in a non-12 tuning, not just
  render one; **or**
- the parked **note-entry shift redesign** (the white/black semitone-shift problem)
  is picked up for implementation — at that point "which geometry" is the framing
  question, and this is the menu.

## Related

- The problem that motivated the research:
  `../discussions/2026-07-13/chord-launcher-and-programming-modes.md` (semitone
  shift breaks the white/black row mnemonic).
- Earlier threads: `../discussions/2026-07-10/microtonality.md`,
  `../discussions/2026-07-10/keyboard-and-input-surface.md` (isomorphic layouts
  named as an option).
- Near-term work this is deliberately *not* part of:
  `../plans/programming-modes-buildout.md`.
- External references (2026-07): isomorphic keyboards & transpositional invariance
  — <https://en.wikipedia.org/wiki/Isomorphic_keyboard>,
  <https://grokipedia.com/page/Isomorphic_keyboard>; Wicki-Hayden (fifths axis) —
  <https://en.wikipedia.org/wiki/Wicki%E2%80%93Hayden_note_layout>; hex microtonal
  controllers — <https://www.lumatone.io/faq>,
  <https://www.starrlabs.com/product/microzone-u990/>; diatonic vs. chromatic
  transposition — <https://blog.flat.io/transpose-by-chromatic-diatonic-interval-music-theory/>;
  pitch bend vs. transpose — <https://homestudioguys.com/blog/understanding-midi-keyboard-pitch-bend-modulation-wheels/>.
