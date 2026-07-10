"""PianoApp -- the playable instrument shell, wired over the promoted library.

Promotes the ``playable_instrument`` spike (the "seed of the real app") from a
procedural ``state`` dict into a class. It closes the full live signal chain:

    PyGame loop -> InputRouter -> EventQueue -> PolySynth -> sounddevice OutputStream

The GUI event loop is the PRODUCER (pushes reconciled ``NoteEvent``s onto the queue
and repaints the pressed key); the audio callback is the CONSUMER (drains the queue
and renders the summed, enveloped, polyphonic voices). They share only the lock-free
``EventQueue`` -- topology A, no worker thread. Canonical map: [[signal-chain]].

pygame and sounddevice are imported LAZILY (inside methods), so importing this module
stays headless: ``import pypiano_2607`` never opens a display or an audio device. The
runnable CLI (argparse, ``--voice``/``--selftest``, the live entry point) lives in
``examples/play_app.py``; this module is the reusable class.
"""

from __future__ import annotations

import time

from .events import NoteEvent, NoteKind, Source
from .queue import EventQueue
from .router import InputRouter
from .mouse import MouseGlissando
from .pitch import midi_to_freq
from .config import SR
from .audio import PolySynth, PianoVoice, SineVoice
from .gui import (
    build_keys, offset_keys, hit_test, render_full, redraw_key, key_to_midi,
    MARGIN, WIN_W, WIN_H,
)


class PianoApp:
    """A playable two-octave piano: QWERTY + mouse in, live audio out.

    Construct it (opens a window, builds the synth, paints the keyboard), then call
    ``run()`` to open the audio stream and enter the event loop -- or drive
    ``dispatch()`` directly (the tests do this headless). ``voice`` selects the
    timbre: ``"piano"`` (rich inharmonic ``PianoVoice``, default) or ``"sine"`` (plain
    ``SineVoice``). ``tuning`` selects the temperament: ``None`` => 12-TET, or pass a
    ``midi -> Hz`` callable (e.g. ``tuning.just_tuning(tonic)`` for Just Intonation).
    Call ``close()`` when done to release the window.
    """

    def __init__(self, *, voice: str = "piano", tuning=None):
        import pygame                    # lazy: importing this module stays headless
        self.pygame = pygame
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption(f"pypiano ({voice}) — QWERTY + mouse, Esc to quit")

        self.wk, self.bk = build_keys()
        offset_keys(self.wk + self.bk, MARGIN, MARGIN)
        self.key_to_midi = key_to_midi(pygame)

        self._tuning = tuning or midi_to_freq          # midi -> Hz; None => 12-TET
        self.router = InputRouter(tuning=self._tuning)
        self.queue = EventQueue()
        factory = PianoVoice if voice == "piano" else SineVoice
        self.synth = PolySynth(self.queue, voice_factory=factory)
        self.glissando = MouseGlissando()

        render_full(self.screen, self.wk, self.bk, self.router.held)
        pygame.display.flip()

    # --- the glue: route one router transition to BOTH the queue and the screen ---

    def emit(self, ev: NoteEvent | None) -> None:
        """Push a router transition to the audio queue and repaint the affected key.
        The router returns ``None`` on a *reconciled* (no audible change) press/release
        -- skip those entirely (no queue push, no repaint)."""
        if ev is None:
            return
        self.queue.push(ev)                                     # -> audio thread
        # ev.sounder_id == the pitch slot (MIDI) while the router mints it that way,
        # which is exactly what the MIDI-keyed redraw_key / router.held expect. (events
        # warns sounder_id is not a pitch in general; revisit here if that changes.)
        rect = redraw_key(self.screen, ev.sounder_id, self.wk, self.bk, self.router.held)
        if rect is not None:
            self.pygame.display.update(rect)                    # -> visual

    def _press(self, midi: int, source: Source) -> None:
        self.emit(self.router.press(midi, source))

    def _release(self, midi: int, source: Source) -> None:
        self.emit(self.router.release(midi, source))

    def _mouse(self, transitions: list[tuple[str, int]]) -> None:
        """Route MouseGlissando transitions through the router (Source.MOUSE)."""
        for kind, midi in transitions:
            if kind == "press":
                self._press(midi, Source.MOUSE)
            else:
                self._release(midi, Source.MOUSE)

    def all_notes_off(self) -> None:
        """Release every sounding note and reset input state -- the sanctioned
        response to focus loss (NEVER grab the cursor; see policy/input-policy.md).
        Pushes a note-off per held note so the audio side frees the voices, then resets
        the router + glissando and repaints the keyboard unpressed."""
        for midi in list(self.router.held):
            self.queue.push(NoteEvent(NoteKind.OFF, midi, None, Source.KEYBOARD,
                                      time.perf_counter()))
        self.router = InputRouter(tuning=self._tuning)   # keep the temperament across the reset
        self.glissando = MouseGlissando()
        render_full(self.screen, self.wk, self.bk, set())
        self.pygame.display.flip()

    def dispatch(self, event) -> bool:
        """Route one PyGame event through the router into the queue + screen. Returns
        ``False`` when we should quit. The SAME path runs live and under the tests."""
        pygame = self.pygame
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return False

        if event.type == pygame.KEYDOWN and event.key in self.key_to_midi:
            self._press(self.key_to_midi[event.key], Source.KEYBOARD)
        elif event.type == pygame.KEYUP and event.key in self.key_to_midi:
            self._release(self.key_to_midi[event.key], Source.KEYBOARD)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse(self.glissando.press(hit_test(event.pos, self.wk, self.bk)))
        elif event.type == pygame.MOUSEMOTION:
            # glissando.motion() no-ops unless the button is down (a bare hover is silent).
            self._mouse(self.glissando.motion(hit_test(event.pos, self.wk, self.bk)))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse(self.glissando.release())
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.all_notes_off()
        return True

    def run(self) -> None:
        """Open the audio stream and run the event loop until quit. ``latency='low'``
        is the committed lever (device output ~35 -> ~9 ms). ``pygame.event.wait()``
        keeps the GUI thread at 0% CPU while idle; the audio callback runs on its own
        thread, draining the queue each block (topology A)."""
        import sounddevice as sd          # lazy: no device import at module load

        with sd.OutputStream(samplerate=SR, channels=1, dtype="float32",
                             callback=self.synth.callback, latency="low"):
            running = True
            while running:
                event = self.pygame.event.wait()   # discrete events -> 0% CPU while idle
                running = self.dispatch(event)

        if self.synth.status_flags:
            print(f"note: {self.synth.status_flags} callback status flags (possible underruns).")

    def close(self) -> None:
        """Quit pygame (release the window). Safe to call more than once."""
        self.pygame.quit()
