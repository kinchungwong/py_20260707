# Input & cursor policy (hard constraint)

**`pygame.event.set_grab(True)` is never allowed in this project. Off limits.**

This extends to any equivalent that confines, locks, warps, or captures the user's
mouse pointer or keyboard away from the rest of their system. Do not reach for it,
not even as a "temporary" or "fallback" measure.

## Why (settled — do not relitigate)

1. **It's hostile to the user.** Grabbing confines the cursor to our window. An
   instrument GUI must never trap the user's pointer or keyboard — they stay in
   control of their machine at all times.
2. **It's unnecessary for our use case.** The `mouse_input` spike confirmed that
   SDL2's *implicit* mouse capture already delivers out-of-window motion and the
   button-up during a drag, so releasing the mouse outside the window is handled
   correctly **without** grabbing. See
   `../memory/pygame/mouse-hit-test-piano.md`.

## What to do instead

- Rely on SDL2 implicit capture during a button-hold; treat out-of-window
  coordinates as "no key" (note-off via `hit_test == None`) and clear on button-up.
- If some future platform/backend ever fails to deliver those events, solve it
  another way — e.g. treat window mouse-leave or focus-loss as **all-notes-off** —
  **never** by grabbing or confining the cursor.
