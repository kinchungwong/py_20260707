# PyGame KEYDOWN/KEYUP are clean note-on/note-off pairs (no auto-repeat by default)

For a keyboard-as-instrument, we need each physical key press to be exactly one
note-on and each release exactly one note-off. PyGame gives us this **for free** —
proven by the `kbd_input` spike (`../../spikes/kbd_input.py`).

## The fact

- By default PyGame does **not** repeat `KEYDOWN` while a key is held. A held key
  produces one `KEYDOWN` at press and one `KEYUP` at release — a clean pair, which
  is exactly the note-on/note-off shape we want. (The OS text-input key-repeat
  only kicks in if you explicitly call `pygame.key.set_repeat(...)`; leave it off.)
- Still **dedupe on a held-set**: `if midi in held: skip` before emitting note-on.
  It's belt-and-braces if repeat ever gets enabled, and it also cleanly handles two
  different inputs (e.g. a QWERTY key and a mouse click, later) landing on the same
  note — the second shouldn't re-trigger.

## Why it matters downstream

- The `event_queue` spike will turn these KEYDOWN/KEYUP events into semantic
  note-on/note-off events on the thread-safe queue. Because the pairs are clean,
  that translation is a direct 1:1 — no debouncing or repeat-filtering needed.
- The same held-set is what `polyphony_voices` will read to know how many voices
  are sounding.

## Related

- Verifying the visual side of these spikes headlessly: [[headless-render-to-png]].
- The incremental "redraw only the changed key" technique (and the black-over-white
  overlap wrinkle) is documented in the `kbd_input` spike header, not yet promoted
  to its own memory — lift it here if a later spike needs it again.
