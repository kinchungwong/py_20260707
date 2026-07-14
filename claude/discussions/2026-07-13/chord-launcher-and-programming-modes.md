# Topic: chord launcher first — and staged entry as one of several programming modes

*A discussion note: current knowledge + the direction we're now committing to. Builds
on `../2026-07-10/keyboard-and-input-surface.md` (which named all the vocabulary and put
"one-key-to-many" on the table). Today's move is to **choose** it as the lead model.*

## The decision that sharpened

Hands-on use confirmed what the 2026-07-11 eval suspected: adding **more single-note
key bindings** — widening the computer-key → piano-key mapping ("width") — does **not**
address the real limitation. The limitation is the keyboard's **simultaneity ceiling**
(matrix rollover / jamming; see the 2026-07-10 note and
`../../retrospectives/2026-07-10-d.md`), which is a physical property of the hardware and
cannot be papered over in software.

**So: stop widening, go deep.** Lean hard into the **one-key-to-many** idea the
2026-07-10 discussion already named (chord mode / chord memory / "one-finger chord",
Archetype 5): **each computer-keyboard key auto-plays a whole saved chord.** One
keypress = one full chord, regardless of how many notes it holds — which sidesteps the
simultaneity ceiling entirely instead of fighting it.

This **promotes** saved chords from a side feature — today's single `Z` preset, or the
2026-07-11 eval's planned `z`–`m` preset slots
(`../../../focused-spikes/staged-chord-entry/README.md`) — to the **central interaction
model** of the mode. The keyboard becomes a **chord launcher**.

## Programming modes as a family (not just "staged mode")

The through-line: because live per-note playing is a hardware dead end, the app leans on
**non-real-time, programming-style entry**. Staged-chord-entry is **one** such mode, not
the whole story. Today names a **second** (see
[`melody-editing-mode.md`](melody-editing-mode.md)), and the frame going forward is a
**family of programming modes** that share machinery (audition, commit gestures, a
visualized buffer, mouse editing) rather than a single monolithic UI.

- **Staged / chord-launcher mode** — build chords (staged entry), bind them to keys,
  fire them one-press. Authoring path already anticipated in 2026-07-10's "build-once,
  trigger-fast" synthesis.
- **Melody-editing mode** — base-note contour entry + WYSIWYG per-note editing.
- (room for more later — the point is the plural.)

## Mouse is first-class, not a HUD afterthought

Today the mouse drives **only HUD buttons**, never the piano keys or gadgets
(`../../../focused-spikes/staged-chord-entry/staged_app.py`, README "v1 scope"). That's
too narrow. The mouse matters **inside** the programming modes themselves — chord
exploration (click keys to try/stage notes), preset management, and it is a **hard
prerequisite** for the melody mode's WYSIWYG editor. Building it out needs the
coarse-to-fine hit-test (`collidepoint`) scaffolding the 2026-07-11 eval already flagged.

Constraint that still governs all of it: **never confine the cursor or keyboard**
(`../../policy/input-policy.md`) — focus-loss ⇒ all-notes-off, never a grab.

## A music-theory snag worth recording

The **semitone-shift** feature (`q`/`\` slides the input window) **conflicts with Just
Intonation**: JI ratios are defined relative to a fixed tonic, so re-aiming the window
by a semitone breaks the intonation. **The current demo must stay 12-TET and disregard
`--tuning ji`.** This should graduate to `../../memory/musictheory/` as a decision, not
just live in this discussion.

## Open questions

*Resolved 2026-07-13 — decisions recorded in
[`../../plans/programming-modes-buildout.md`](../../plans/programming-modes-buildout.md)
(save-your-own; row-delimited `z–m` launcher zone; coexists with live mode; saved
chords fire at saved pitch). Kept below as the original framing.*

- **Where do a launcher key's chords come from?** A preloaded bank (e.g. diatonic
  triads of a key, out of the box) vs. save-your-own (generalize today's `Z`) vs. a
  mix (defaults you can overwrite).
- **Does the chord launcher replace live mode, or sit beside it** as a distinct mode?
  Does `q`/`\` now transpose whole chords rather than single notes?
- **How much machinery is genuinely shared** across programming modes vs. mode-specific
  — i.e. what belongs in the library at graduation vs. per-spike?
