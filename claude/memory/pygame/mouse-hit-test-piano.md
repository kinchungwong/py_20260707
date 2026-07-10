# Mouse-on-piano: hit-test black keys first, and the drag/release gotchas

How to turn mouse events into piano-note events, from the `mouse_input` spike
(`../../spikes/mouse_input.py`). Reuse when wiring mouse (or touch) input to the
keyboard widget.

## Hit-test order (confirmed)

Black keys are drawn on **top** of white keys and their rects **overlap** the
white neighbours. So hit-testing must check **black keys first**, then white:

```python
def hit_test(pos, white_keys, black_keys):
    for bk in black_keys:           # on top -> first
        if bk["rect"].collidepoint(pos): return bk["midi"]
    for wk in white_keys:
        if wk["rect"].collidepoint(pos): return wk["midi"]
    return None
```

Testing white-first would steal clicks in the overlap region from the black keys.

## Drag model (confirmed): one "active mouse note"

While the left button is down, at most one mouse-driven note is active — the key
under the cursor, or none over empty space:

- `MOUSEBUTTONDOWN` → active = hit_test(pos)
- `MOUSEMOTION` while down → if hit changed: note-off old, note-on new (glissando)
- `MOUSEBUTTONUP` / cursor over empty space → active = None (note-off)

Add a **margin** around the keyboard so "drag onto empty space → note-off" is
reachable inside the window; otherwise every in-window point hits some white key.

## Release-outside-the-window (⚠ needs manual confirmation)

Clear the note on **any** `MOUSEBUTTONUP` regardless of cursor position — but that
only helps if the event is delivered. Whether SDL delivers `MOUSEBUTTONUP` when
the button is released **fully outside** the window is platform-dependent; if it
isn't delivered, the note sticks. Robust fix: `pygame.event.set_grab(True)` for the
duration of a drag (confines the cursor so the release always lands in-window).
*Status: not yet confirmed on this machine — verify with a real window, then update
this note.*

## Related

- Clean note-on/off from the keyboard side: [[key-events-note-on-off]]. The
  `input_integration` spike merges mouse + keyboard into one event stream (mouse
  should dedupe against the same held-set, since both can target the same note).
- Headless visual verification: [[headless-render-to-png]].
