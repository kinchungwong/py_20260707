"""StagedApp -- the focused spike: staged chord entry over the real pypiano_2607 chain.

Composes the library's InputRouter / EventQueue / PolySynth / keyboard geometry with a
spike-owned event loop, HUD, and a lightweight pygame.mixer audition. It does NOT edit
src/ and does NOT subclass PianoApp (whose dispatch/__init__ aren't extension points) --
it is a parallel shell that reuses the components.

Design decisions baked in (all "spike-simple"; see README.md / status_active.md):
  * chord launcher: save-your-own chords bound to the bottom-row z..m zone (Save auto-picks
    the next empty slot); a launcher key fires its chord in BOTH modes at saved pitch.
    Mouse drives only the HUD buttons, not the piano keys (v1 scope).
  * input surface: a 3-octave keyboard with the computer keys mapped to a slidable window
    over it (layout.InputWindow); q/\\ slide it a semitone, re-aiming future input only, so a
    held note keeps its pitch (_held_key_midi releases the pitch pressed, not the new target,
    and refcounts by pitch so two keys landed on one note by a shift don't cut each other off).
  * live vs staged: a persistent toggle (Tab / Mode button). Staged staging is press-only
    (KEYUP ignored) -- clean because pygame doesn't auto-repeat KEYDOWN.
  * audition on stage: a pygame.mixer one-shot sine behind _audition() (library-free).
  * commit (Play chord / preset fire): fire-and-forget note-ons minted DIRECTLY onto the
    queue (sounder_id = midi, bypassing the router's held-model, no note-off), so they
    ring out on PianoVoice's natural decay. focus-loss silences them.
"""
from __future__ import annotations

import time

import pygame

from pypiano_2607.events import NoteEvent, NoteKind, Source
from pypiano_2607.queue import EventQueue
from pypiano_2607.router import InputRouter
from pypiano_2607.audio import PolySynth, PianoVoice, SineVoice
from pypiano_2607.pitch import midi_to_freq
from pypiano_2607.config import SR
from pypiano_2607.gui import offset_keys, note_name, MARGIN

import hud
import layout
import press
from audition import Audition

HUD_H = 200
WIN_W = layout.WIDTH + 2 * MARGIN
WIN_H = HUD_H + layout.HEIGHT + MARGIN
FLASH_MS = 350
SPACE_LONG_S = 0.20        # space-bar hold >= this => play + clear; below => audition (kept). Tune on device.


class StagedApp:
    def __init__(self, *, voice="piano", tuning=None, tuning_label="12-TET"):
        # mixer params BEFORE pygame.init() -> boot-time audio (verified clean coexistence
        # with the sounddevice stream when the mixer comes up first).
        pygame.mixer.pre_init(SR, -16, 1, 256)
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption(
            "pypiano staged-chord-entry spike — Tab: live/staged, Esc: quit")

        self._tuning = tuning or midi_to_freq              # midi -> Hz; None => 12-TET
        self.tuning_label = tuning_label

        # library components + the 3-octave keyboard (built here; the library's build_keys is
        # fixed at two octaves -- see layout.py).
        self.wk, self.bk = layout.build_keyboard()
        offset_keys(self.wk + self.bk, MARGIN, HUD_H)      # keyboard below the HUD strip
        self.window = layout.InputWindow()                 # computer keys -> midi, slidable
        self.router = InputRouter(tuning=self._tuning)
        self.queue = EventQueue()
        factory = PianoVoice if voice == "piano" else SineVoice
        self.synth = PolySynth(self.queue, voice_factory=factory)

        # spike UI
        self.hud = hud.Hud(WIN_W, HUD_H, MARGIN)
        self.launcher = layout.default_launcher_zone()     # bottom row z..m -> chord slots
        self._shift_down_key = pygame.key.key_code("q")    # slide the input window down/up
        self._shift_up_key = pygame.key.key_code("\\")
        self.audition = Audition(range(layout.MIN_MIDI, layout.MAX_MIDI + 1), sr=SR)
        self._labels = self.window.labels()                # midi -> (char, name); recomputed on shift
        self._key_font = pygame.font.Font(None, 22)
        self._name_font = pygame.font.Font(None, 18)

        # state
        self.mode = "live"                                 # 'live' | 'staged'
        self.staged: list[int] = []                        # pending midi, ordered
        self.slots: list[list[int] | None] = [None] * len(self.launcher)  # z..m chord slots
        self._flash: dict[int, int] = {}                   # midi -> expiry (ticks ms)
        self._ringing: set[int] = set()                    # committed ids w/ no natural off
        self._held_key_midi: dict[int, int] = {}           # live keycode -> midi it pressed
        self.hint = "Live mode. Tab to enter staged entry."
        self.press = press.PressTimer(SPACE_LONG_S)        # space short/long classifier
        self._now = time.perf_counter                      # injectable clock (headless tests)

    # --- audio helpers --------------------------------------------------------

    def _audition(self, midi: int) -> None:
        """THE seam to swap when consolidating auditions onto PolySynth (status marker)."""
        self.audition.play(midi)

    def _fire(self, midi: int) -> None:
        """Fire-and-forget committed note: mint a note-on directly (bypass the router), no
        note-off -> rings out on the voice's natural decay; tracked so focus-loss can
        silence it."""
        self.queue.push(NoteEvent(NoteKind.ON, midi, self._tuning(midi),
                                  Source.KEYBOARD, time.perf_counter()))
        self._ringing.add(midi)
        self._flash[midi] = pygame.time.get_ticks() + FLASH_MS

    def _press(self, midi: int) -> None:
        ev = self.router.press(midi, Source.KEYBOARD)
        if ev is not None:
            self.queue.push(ev)

    def _release(self, midi: int) -> None:
        ev = self.router.release(midi, Source.KEYBOARD)
        if ev is not None:
            self.queue.push(ev)

    def _all_notes_off(self, *, clear_staged: bool) -> None:
        for midi in list(self.router.held):
            self.queue.push(NoteEvent(NoteKind.OFF, midi, None, Source.KEYBOARD,
                                      time.perf_counter()))
        for sid in list(self._ringing):
            self.queue.push(NoteEvent(NoteKind.OFF, sid, None, Source.KEYBOARD,
                                      time.perf_counter()))
        self._ringing.clear()
        self._held_key_midi.clear()
        self.press.cancel()                                # drop any in-flight space press
        self.router = InputRouter(tuning=self._tuning)     # keep the temperament
        if clear_staged:
            self.staged.clear()

    # --- staged-entry actions -------------------------------------------------

    def _shift_window(self, delta: int) -> None:
        """Slide the input window (q/\\). Re-aims future input only; held/committed notes keep
        their pitch (the held-key map releases the pitch actually pressed, not the new one)."""
        self.window.shift(delta)
        self._labels = self.window.labels()
        lo, hi = self.window.span
        self.hint = (f"Input keys now {note_name(lo)}..{note_name(hi)} "
                     f"(window shift {self.window.offset:+d}).")

    def _toggle_mode(self) -> None:
        self._all_notes_off(clear_staged=True)             # release held/committed; clear pending
        self.mode = "staged" if self.mode == "live" else "live"
        self.hint = ("Staged entry. Tap keys to stage (auditioned); space = Play chord."
                     if self.mode == "staged"
                     else "Live mode. Tab to enter staged entry.")

    def _stage_plain(self, midi: int) -> None:
        if midi not in self.staged:
            self.staged.append(midi)
        self._audition(midi)                               # reminder even if already staged

    def _stage_shift(self, midi: int) -> None:             # toggle == "forget" gesture
        if midi in self.staged:
            self.staged.remove(midi)
        else:
            self.staged.append(midi)
            self._audition(midi)

    def _fire_staged(self) -> None:
        """Fire the staged notes so they sound (fire-and-forget), WITHOUT clearing them --
        the audio for a space press, short or long. Sound happens on KEYDOWN."""
        for midi in self.staged:
            self._fire(midi)

    def _play_chord(self) -> None:
        if not self.staged:
            return
        names = [note_name(m) for m in self.staged]
        for midi in self.staged:
            self._fire(midi)
        self.staged.clear()
        self.hint = "Played:  " + "  ·  ".join(names)

    def _save_chord(self) -> None:
        if not self.staged:
            return
        try:
            idx = self.slots.index(None)                   # next empty slot (auto-pick)
        except ValueError:
            self.hint = "Launcher full - shift+key to forget a slot first."
            return
        self.slots[idx] = list(self.staged)
        self.hint = (f"Saved to {self.launcher.char(idx)}:  "
                     + "  ·  ".join(note_name(m) for m in self.slots[idx]))
        self.staged.clear()

    def _release_staged(self) -> None:
        self.staged.clear()
        self.hint = "Released the pending chord."

    def _launcher_fire(self, slot: int) -> None:
        chord = self.slots[slot]
        if not chord:
            self.hint = f"{self.launcher.char(slot)} is empty - stage a chord and Save it first."
            return
        for midi in chord:
            self._fire(midi)
        self.hint = (f"{self.launcher.char(slot)} fired:  "
                     + "  ·  ".join(note_name(m) for m in chord))

    def _launcher_forget(self, slot: int) -> None:
        if self.slots[slot] is not None:
            self.slots[slot] = None
            self.hint = f"Forgot the chord on {self.launcher.char(slot)}."

    def _hud_action(self, action: str) -> None:
        if action == "mode":      self._toggle_mode()
        elif action == "play":    self._play_chord()
        elif action == "save":    self._save_chord()
        elif action == "release": self._release_staged()

    # --- event dispatch -------------------------------------------------------

    def dispatch(self, event) -> bool:
        """Route one pygame event; return False to quit. Mode-aware: live-mode note
        handling is the base instrument; staged-mode note handling is press-only staging."""
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.WINDOWFOCUSLOST:
            self._all_notes_off(clear_staged=True)         # input policy: focus-loss = all-off
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_TAB:
                self._toggle_mode()
                return True
            if event.key == self._shift_down_key:          # slide the input window (either mode)
                self._shift_window(-1)
                return True
            if event.key == self._shift_up_key:
                self._shift_window(+1)
                return True
            shift = bool(event.mod & pygame.KMOD_SHIFT)
            slot = self.launcher.slot_of(event.key)        # launcher zone: fire / (shift) forget
            if slot is not None:
                self._launcher_forget(slot) if shift else self._launcher_fire(slot)
                return True
            if self.mode == "staged" and event.key == pygame.K_SPACE:
                self.press.key_down(pygame.K_SPACE, self._now())   # sound now; short/long on release
                self._fire_staged()
                names = "  ·  ".join(note_name(m) for m in self.staged)
                self.hint = f"Auditioning:  {names}" if self.staged else "Nothing staged yet."
                return True
            midi = self.window.resolve(event.key)
            if midi is not None:
                if self.mode == "live":
                    self._press(midi)
                    self._held_key_midi[event.key] = midi  # remember the pitch, for a stuck-free off
                elif shift:
                    self._stage_shift(midi)
                else:
                    self._stage_plain(midi)
            return True

        if event.type == pygame.KEYUP:
            if self.mode == "staged":                       # staged: only space uses KEYUP (press-duration)
                if event.key == pygame.K_SPACE:
                    kind = self.press.key_up(pygame.K_SPACE, self._now())
                    if kind == "long":                      # play + clear (notes already sounding)
                        names = "  ·  ".join(note_name(m) for m in self.staged)
                        self.staged.clear()
                        self.hint = f"Played + cleared:  {names}" if names else "Nothing staged."
                    elif kind == "short":                   # audition: keep the staged chord
                        self.hint = "Auditioned - staged kept. Hold space longer to play + clear."
                return True
            midi = self._held_key_midi.pop(event.key, None)
            # Release the pitch this key pressed (not the window's current target -- a shift may
            # have moved it), and only once NO other held key still targets that pitch. A shift
            # can land two keys on one pitch, and the router dedups by pitch, so an eager off
            # would cut a note still held by the other key.
            if midi is not None and midi not in self._held_key_midi.values():
                self._release(midi)
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self.hud.hit(event.pos, self.mode)
            if action is not None:
                self._hud_action(action)                    # mouse drives HUD buttons only
            return True

        return True

    # --- render + loop --------------------------------------------------------

    def _flashing(self) -> set[int]:
        now = pygame.time.get_ticks()
        for m in [m for m, t in self._flash.items() if t <= now]:
            del self._flash[m]
        return set(self._flash)

    def render(self) -> None:
        self.screen.fill(hud.BG)
        staged_names = [note_name(m) for m in self.staged]
        slot_labels = [(self.launcher.char(i),
                        [note_name(m) for m in chord] if chord else None)
                       for i, chord in enumerate(self.slots)]
        slots_full = all(c is not None for c in self.slots)
        lo, hi = self.window.span
        window_label = f"keys {note_name(lo)}-{note_name(hi)}  (q/\\ shift {self.window.offset:+d})"
        self.hud.draw(self.screen, mode=self.mode, staged_names=staged_names,
                      slot_labels=slot_labels, slots_full=slots_full,
                      tuning_label=self.tuning_label, hint=self.hint, window_label=window_label)
        hud.draw_keyboard(
            self.screen, self.wk, self.bk,
            held=self.router.held, staged=set(self.staged), flashing=self._flashing(),
            labels=self._labels, key_font=self._key_font, name_font=self._name_font,
            bound=self.window.bound_midis(),
        )

    def run(self) -> None:
        import sounddevice as sd
        with sd.OutputStream(samplerate=SR, channels=1, dtype="float32",
                             callback=self.synth.callback, latency="low"):
            clock = pygame.time.Clock()
            running = True
            while running:
                for event in pygame.event.get():
                    if not self.dispatch(event):
                        running = False
                        break
                if not running:
                    break
                self.render()
                pygame.display.flip()
                clock.tick(60)
        if self.synth.status_flags:
            print(f"note: {self.synth.status_flags} audio callback status flags "
                  "(possible underruns).")

    def close(self) -> None:
        pygame.quit()
