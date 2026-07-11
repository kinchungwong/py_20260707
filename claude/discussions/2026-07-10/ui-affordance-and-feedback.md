# Topic: UI affordance and modality feedback — a bit of WYSIWYG

*A discussion note: current knowledge + open questions. Not a decision, not a plan.*

## The need (2026-07-10)

As the instrument grows richer — multiple tunings, possible chord-mode presets,
staged/step entry with its own mode, mouse glissando alongside the keyboard — the
**display has to grow with it.** The shipped app so far is close to mode-free (12-TET
or JI, chosen at launch via `--tuning`), so it hasn't yet needed to tell the player
"here's what you can do" or "here's what's active right now." That changes as soon as
any of tonight's other ideas (chord mode, staged entry, alternate tunings mid-session)
land.

The display needs to do **two distinct jobs**:

1. **Discoverability** — give clues about what actions/gestures are available. A
   newbie (see `audience-and-accessibility.md`) can't use a gesture they don't know
   exists.
2. **Modality feedback** — make it unmissable **what mode is currently in effect**
   (active tuning, chord-mode on/off, staged-entry active or not, which commit gesture
   is bound).

"A bit of WYSIWYG" is the shorthand for both: **what you see should represent the
current playable state accurately**, so you never have to remember or infer it. This is
close to a well-established usability principle — **visibility of system status**
(keep the user informed, through appropriate feedback, of what's going on) — one of the
oldest, most standard usability heuristics; we're not inventing a new idea here, just
applying it to an instrument.

## Direct link to the keyboard/mode-error discussion

This is the **concrete mitigation** for the mode-error risk raised in
`keyboard-and-input-surface.md`: a **quasimode** is inherently self-signaling (you can
feel your finger holding the key), but a **persistent mode** (a true toggle) is only
safe with a strong, glanceable modality indicator. If the "true mode toggle" commit
gesture is ever prototyped, this topic is what makes it survivable for a newbie.

## Concrete surface ideas (discussion-starters, not commitments)

- A small **legend/HUD** showing the active tuning and any active modifiers.
- **On-screen key highlighting** on hover/press, so the mapping from physical key to
  pitch/action is always visible, not memorized.
- A **mode indicator** (icon or text) for staged-entry state — on/off, and what's
  currently staged.
- A **visual preview of a pending chord** while it's being staged, before commit —
  turning an invisible buffer into something you can see and correct.

## Connections to the other topics

- **Keyboard/input** (`keyboard-and-input-surface.md`) — the mode-error mitigation
  above, and giving visible form to a staged/pending chord.
- **Microtonality** (`microtonality.md`) — a non-12 layout (isomorphic grid, ribbon,
  N-EDO keyboard) needs far more visual scaffolding than a standard piano: labeling
  degrees, showing the active tuning system, since there's no learned "white/black key"
  intuition to fall back on.
- **Pedagogy** (`pedagogical-products.md`) — a good WYSIWYG UI is itself a teaching
  tool; seeing the system's state is a way of learning the system, independent of any
  written material.
- **Audience** (`audience-and-accessibility.md`) — this and terminology
  (`terminology-policy.md`) are the two concrete mechanisms identified tonight for
  making the app actually low-friction and forgiving — you can't correct a mistake you
  didn't know you'd made, and you can't use an affordance you can't see.

## A live sketch (2026-07-10, in-chat only — not persisted as a file)

Tried a clickable inline mockup combining this topic with archetype 5 from
`keyboard-and-input-surface.md`: a tuning badge, a live/staged mode toggle
(color-coded, since a persistent mode needs an unmissable signal), on-screen keys
labeled physical-key-over-note (the discoverability half), and a pending-chord tray
where staged notes can be removed individually or cleared entirely before an explicit
commit (the low-friction-correction half of `audience-and-accessibility.md`). Confirmed
by interacting with it: the mode-color-change genuinely helps track state, and an empty
tray needs an explicit "nothing staged yet" placeholder or it reads as broken rather
than idle.

**Graduated to a captured design (2026-07-10):** after several more rounds (save-as-preset,
a unified shift-click "forget" gesture, relabeled controls), the full spec — states,
every control and gesture, reasoning, and the reference source — now lives in
[`../../ui-designs/staged-chord-entry-hud.md`](../../ui-designs/staged-chord-entry-hud.md),
no longer in-chat-only.

## Open questions

- How much of this is **general-purpose chrome** (works for any mode) versus
  **mode-specific display** (a JI HUD looks nothing like a chord-mode HUD)?
- Does discoverability risk **clutter** — how do we show "what's possible" without
  overwhelming a first-time player?
- Is there a **spike-sized** first question here (e.g. "does a simple on-screen legend
  measurably reduce mode-error mistakes?") — or is this necessarily bundled into
  whatever the first keyboard-input spike ends up being?
