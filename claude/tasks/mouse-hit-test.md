# Task sidecar — mouse hit-test core (plan step 3)

Granular checklist for **step 3** of
[`../plans/programming-modes-buildout.md`](../plans/programming-modes-buildout.md)
(dependency **B**: `[B. mouse hit-test core] → [C. mouse in staged mode] → [D. melody
mode WYSIWYG]`). Parent: [`current.md`](current.md) → Active. Work lands in
`../../focused-spikes/staged-chord-entry/` (no edits to `src/`).

## Status

**Code complete + selftest green (2026-07-14).** Built `hittest.py` (`Region` StrEnum,
`RegionSpec`, type-annotated `pick`), wired two regions (HUD + keyboard) into `StagedApp`,
and routed `MOUSEBUTTONDOWN` through `_on_click` → `_hit` → `pick`. **No behaviour change:**
HUD buttons act as before (the Save→slot / launcher click flows in the selftest exercise
the new routing end-to-end and still pass); a piano-key hit is resolved but is a documented
no-op **seam for step 4**. Selftest asserts the resolution (HUD button→action, HUD
background→None, staged-only button inert in live, white→midi, black-over-white order guard,
below-keyboard→None); piano + sine green, `tools/run_spike_tests.py` 14/14. **Next: step 4
(C) — mouse in staged mode.**

Design below; this step is **foundational — no user-visible mode / no behaviour change**.
It refactors the spike's three ad-hoc hit-test surfaces into one coarse-to-fine core and
proves it headlessly; wiring the mouse to *do* things (audition/stage, launcher management)
is **step 4 (C)**.

## Scope

Build the **coarse-to-fine `collidepoint` scaffolding** the 2026-07-11 eval flagged: a
small core that takes a screen point and resolves it to `(region, gadget)` across the
*whole* window, coarse (which screen region) then fine (which gadget in it). Unify the
two hit-tests that exist today and leave a clean seam for the rest. Keep it liftable to
`focused-spikes/shared/` (it is the long pole for the melody editor, step 5/D).

**Explicitly NOT in this step** (guard against scope creep): wiring mouse behaviour,
adding launcher-slot rects, and anything touching the deferred pane-modularization
refactor — see "Out of scope".

## Grounding (from the code)

Three gadget surfaces exist today, each with its own (or no) hit-test:

1. **HUD buttons** — `hud.py::Hud.hit(pos, mode)`: a flat linear scan over fixed rects
   (`mode_rect`, and in staged mode `play/save/release_rect`) → an **action string**
   (`"mode"|"play"|"save"|"release"`) or `None`.
2. **Piano keys** — the library's `gui.keyboard.hit_test(pos, white_keys, black_keys)`
   (`src/pypiano_2607/gui/keyboard.py:94`): **black keys first** (they overlap and draw
   on top of whites), then whites → **midi int** or `None`. Reuse verbatim.
3. **Launcher slots** — **no on-screen rects at all**: `layout.py::KeyZone.slot_of(keycode)`
   maps only *computer keycodes* → slot index. The launcher's on-screen presence is a
   one-line **text readout painted inside the HUD strip** (`hud.py::draw`, y≈148 <
   `HUD_H`=200). So a mouse click there currently lands in the HUD region.

Wiring today (`staged_app.py::dispatch`): `MOUSEBUTTONDOWN` button 1 →
`self.hud.hit(event.pos, self.mode)` → `_hud_action`. Comment: "mouse drives HUD buttons
only". Piano-key and launcher mouse are **unwired**.

Geometry constants for the coarse rects: `WIN_W = layout.WIDTH + 2*MARGIN`,
`HUD_H = 200`; keyboard is inset by `offset_keys(wk+bk, MARGIN, HUD_H)`, so its bounding
box is `Rect(MARGIN, HUD_H, layout.WIDTH, layout.HEIGHT)`.

**Prior art (reuse, don't reinvent):** the `mouse_input` spike already settled the
piano-side mouse model — memory `../memory/pygame/mouse-hit-test-piano.md`:
black-first hit-test (now the library `hit_test`); the **drag model** (one active mouse
note; `MOUSEMOTION` while down re-hit-tests → note-off old / note-on new = glissando;
button-up or empty space → note-off); and that **SDL2 implicit capture** delivers
out-of-window motion + the button-up, so **no `set_grab`** is needed (also banned by
`../policy/input-policy.md`). That drag model is **step 4's** material — step 3 only
builds the point→gadget resolver it will sit on.

## Design (the core)

A new `hittest.py` in the spike (liftable to `shared/`), independent of staged-specific
state — pure geometry + delegation:

- **`Region`** — the region *identity*, a closed set → an `enum.StrEnum`
  (`Region.HUD`, `Region.KEYBOARD`, …) per the project's string-enum preference, not
  bare literals. This is the ONLY thing called "Region"; the identity name is used
  consistently everywhere (no `name`-vs-`region` drift).
- **`RegionSpec`** = a `(region, rect, resolve)` tuple: the identity, its coarse
  bounding box, and `resolve(pos) -> payload | None` (the region's fine hit-test). The
  `regions` argument to `pick` is a `list[RegionSpec]`.
- **`pick(pos, regions) -> tuple[Region, object | None] | None`** (return **type-annotated**)
  — walk the specs **topmost-first**; the **first** whose `rect.collidepoint(pos)` is true
  **claims** the click and returns `(region, resolve(pos))`. The loop variable and the
  returned first element are both named `region` (a `Region`). The second element
  (`payload`) may be `None` = "hit this region's background" (HUD padding, a 1-px gap
  between keys). Regions are **opaque**: no fall-through to a region behind a claiming
  one. (Coarse rects are y-disjoint today, so order is not yet load-bearing — but define
  the topmost-first rule now, since panes will overlap once the deferred refactor lands.)

  ```python
  class CollidePoint(Protocol):               # the one slice of pygame.Rect used here;
      def collidepoint(self, pos: Pos, /) -> bool: ...   # keeps this module pygame-free

  RegionSpec = tuple[Region, CollidePoint, Callable[[Pos], Payload | None]]

  def pick(pos: Pos, regions: list[RegionSpec]) -> tuple[Region, Payload | None] | None:
      for region, rect, resolve in regions:   # topmost-first
          if rect.collidepoint(pos):
              return (region, resolve(pos))    # opaque: claim even if payload is None
      return None
  ```

  The coarse box is typed as a `CollidePoint` **Protocol** (structural — any `pygame.Rect`
  satisfies it), not `object` and not `pygame.Rect`: it reads clearly in an IDE / mypy yet
  keeps the core free of a `pygame` import so it lifts to `shared/` unencumbered.
- **Two regions wired this step**, built from the values above:
  - `(Region.HUD, Rect(0, 0, WIN_W, HUD_H), lambda p: self.hud.hit(p, self.mode))`
  - `(Region.KEYBOARD, Rect(MARGIN, HUD_H, layout.WIDTH, layout.HEIGHT),
    lambda p: gui.hit_test(p, self.wk, self.bk))`
- **Payload is polymorphic by region** (action-string for HUD, midi-int for keyboard).
  That is fine for a tagged `(name, payload)` tuple because the caller switches on
  `name` anyway; a `Hit` dataclass is unnecessary ceremony at two regions. Revisit if a
  third region makes the switch unwieldy.

**dispatch integration (behaviour-preserving):** `MOUSEBUTTONDOWN` button 1 routes
through `pick`. `Region.HUD` payload → `_hud_action` (**byte-for-byte the same** as
today). `Region.KEYBOARD` (and any `None`) → a **documented no-op seam** for step 4.
Net user-visible change: **none** — that's the point of this step.

**Launcher stays out.** Its readout sits *inside* the HUD strip, so mouse-clickable
launcher slots mean either new geometry or promoting the readout to its own pane — the
latter is exactly the **deferred pane-modularization** territory. Step 3 leaves the
launcher as a documented future region; step 4 (or the pane refactor) adds it.

## Checklist

- [x] **`hittest.py`** — `Region` (`StrEnum` identity), `RegionSpec` = `(region, rect,
  resolve)`, and `pick(pos, regions) -> tuple[Region, object | None] | None`
  (type-annotated), topmost-first, opaque, `None` payload = region-background. Pure
  geometry, no display, no staged state → headless-testable and liftable to `shared/`.
- [x] **Build the two regions** in `StagedApp` (HUD + keyboard) from the existing
  `hud.hit` and library `gui.hit_test` — no duplicated hit-test logic.
- [x] **Route `MOUSEBUTTONDOWN` through `pick`** — via `_on_click`/`_hit`; HUD payload →
  `_hud_action` (unchanged); keyboard/`None` → an explicit **no-op seam** commented for
  step 4. HUD buttons behave identically (Save→slot / launcher click flows still green).
- [x] **`--selftest`** — headless (`pygame.Rect` needs no display): asserts sample points
  resolve to the right `(region, payload)` — HUD button → action; white key → its midi;
  a **black-over-white** point → the black key's midi (order guard); HUD padding →
  `(HUD, None)`; below the keyboard → `None`.
- [x] Ran `main.py --selftest` (piano + sine, green) + `tools/run_spike_tests.py` (14/14);
  updated spike README + `status_active.md` (no new controls — foundational only).
- [ ] Record any durable gotcha in `../memory/` before closing (candidate: the
  coarse-to-fine / opaque-region rule if it proves load-bearing) — pending; the rule is
  documented in `hittest.py`'s module docstring for now.

## Design questions — resolved (2026-07-14)

1. **Payload shape → tagged tuple.** `pick` returns `tuple[Region, object | None] | None`
   (not a `Hit` dataclass); the caller switches on `region`. Revisit only if a third
   region makes callers ugly. Note from review: **annotate the return type**, and use the
   identity name `region` consistently (the enum is `Region`; the triple is `RegionSpec` —
   no `name`-vs-`region` drift). Folded into "Design" above.
2. **Location → build in the spike, lift later.** Author
   `focused-spikes/staged-chord-entry/hittest.py` now; promote to `shared/` when the
   melody spike (D) needs it (matches decision Q5 "lift opportunistically"). Keeps
   `src/`/`shared/` untouched until the API stabilises against a real second caller.
3. **`None`-payload → opaque.** The first region whose bbox contains the point claims the
   click and returns `(region, None)`; **no fall-through**. Matches a real pane stack and
   avoids surprises once panes overlap after the deferred refactor.

## Out of scope (defer, do not pull in)

- **Any mouse *behaviour*** — click-to-audition/stage, glissando drag, launcher
  management → **step 4 (C)**. Step 3 resolves points; it does not act on them.
- **Launcher-slot rects / clickable slots** — entangled with the HUD strip; needs the
  pane refactor or step 4. Documented future region only.
- **The stored-chord visibility/editing surface & UI-pane-modularization refactor** —
  **deferred, needs its own architecture review** (plan "Deferred"). **Do not start.**
- **Editing `src/`** — the library `hit_test` is reused as-is; the spike does not edit
  `src/`.
