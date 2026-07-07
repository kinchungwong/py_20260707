# Describe chords as cents above the root (not MIDI integers)

The clean way to represent chords in this project — proven by the microtonal
triad spike (`../spikes/microtonal_triads.py`) — is a list of **intervals in
cents above the root**, converted with `f = root_hz * 2**(cents/1200)`.

## Why this is the right primitive

- Cents are continuous, so a **neutral third (350 cents)** — which has no 12-TET
  name — is expressed exactly as easily as a major third (400). The synth needs
  zero changes; only the chord-definition layer moves off MIDI integers.
- This *is* the "pluggable frequency source" step toward the beyond-12-TET
  vision. MIDI/note-number thinking is the thing to avoid.

## The five triads (third, fifth) in cents above root

| quality     | third | fifth | built from                    |
|-------------|-------|-------|-------------------------------|
| major       | 400   | 700   | major 3rd + minor 3rd         |
| minor       | 300   | 700   | minor 3rd + major 3rd         |
| augmented   | 400   | 800   | two major thirds              |
| diminished  | 300   | 600   | two minor thirds              |
| neutral     | 350   | 700   | two neutral thirds (halfway)  |

Verified: neutral's third renders at ~320 Hz on C4, exactly between minor (311)
and major (330) — a real in-between interval, not a detuned one.

## Gotcha: equal-tempered vs. just neutral third

350 cents is the *equal-tempered* neutral third (literal halfway). The **just**
undecimal neutral third is `11/9 ≈ 347.4 cents`. If we later want just-intonation
color, cents should be derived from **frequency ratios**, not a fixed cent grid —
flagged as a future spike.

Builds on [[piano-note-synthesis-recipe]].
