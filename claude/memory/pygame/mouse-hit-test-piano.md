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

## Release-outside-the-window (confirmed: not a problem on Linux/SDL 2.28.4)

While a mouse button is held, **SDL2 implicitly captures the mouse**, so the app
keeps getting events even when the cursor is outside the window. Manually confirmed
on this machine:

- `MOUSEMOTION` continues to arrive with **out-of-window coordinates** → `hit_test`
  returns `None` → the note turns off the instant the cursor leaves the keyboard
  (same path as drag-to-empty). The highlight clears on exit.
- `MOUSEBUTTONUP` is still delivered when you release outside → **no stuck note**;
  releasing out there has no lingering effect. Keeping the button down and moving
  back in resumes glissando.

So `pygame.event.set_grab(True)` is **not needed here** — and in any case it is
**banned by project policy** (see `../../policy/input-policy.md`): confining or
grabbing the cursor is off limits. For any future platform/backend where implicit
capture doesn't hold, mitigate some other way (e.g. treat mouse-leave / focus-loss
as all-notes-off), never by grabbing.
(Env: pygame 2.6.1, SDL 2.28.4, Linux; confirmed 2026-07-09.)

## Related

- Clean note-on/off from the keyboard side: [[key-events-note-on-off]]. The
  `input_integration` spike merges mouse + keyboard into one event stream (mouse
  should dedupe against the same held-set, since both can target the same note).
- Headless visual verification: [[headless-render-to-png]].
