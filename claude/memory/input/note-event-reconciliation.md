# Merge input sources with a reference-counting note router

How multiple input sources (keyboard, mouse, later MIDI) become ONE note-on/off
stream without doubled notes — from the `input_integration` spike
(`../../spikes/input_integration.py`).

## The event vocabulary

```python
class Source(Enum):   KEYBOARD = "keyboard"; MOUSE = "mouse"
class NoteKind(Enum): ON = "on"; OFF = "off"

@dataclass(frozen=True)
class NoteEvent:
    kind: NoteKind   # note-on | note-off (enum, not a bare string -- symmetric with Source)
    midi: int
    source: Source   # the source that caused THIS audible transition
    t: float         # time.perf_counter() when emitted
```

- The event is tagged with the source that caused the transition — **not** every
  source touching the note (see reconciliation below).
- The `perf_counter()` timestamp is captured at emit time. It rides the event
  through the [[event-queue]] and is what the latency spike measures against —
  capture it once, at the source, and never recompute it downstream.

## The router: reference-count by holder-set

A note **sounds while ≥ 1 source holds it**. Track, per MIDI note, the *set* of
sources currently holding it (drop the entry when it empties):

- `press(midi, source)` → emit a note-**on** only on the **0→1** transition;
  otherwise add the source and return `None` (reconciled — already sounding).
- `release(midi, source)` → emit a note-**off** only on the **1→0** transition;
  otherwise return `None` (still held by another source, or this source wasn't
  holding it).

Verified: keyboard **and** mouse both press C4 → exactly one note-on (keyboard,
first down) and one note-off (mouse, last up). The audio side never sees a doubled
note-on, no matter how the presses overlap.

## Why this shape

- **Sources stay decoupled.** Mouse keeps its single-active-note glissando,
  keyboard its multi-held model; neither knows about the other. The router is the
  only place they merge. A third source (MIDI, touch) is just another `Source`
  calling `press`/`release` — no other code changes.
- **The visual uses the reconciled held-set** (`router.held`), so a key stays lit
  until the last source releases it, and repaint happens only on emitted events —
  reconciled no-ops cost nothing.

## Related

- Clean per-source press/release come from [[key-events-note-on-off]] (keyboard)
  and [[mouse-hit-test-piano]] (mouse).
- [[event-queue]] pushes this `NoteEvent` stream across the thread boundary to
  the audio callback (committed topology A) — a lock-free, non-blocking deque.
