"""StagedApp -- the focused spike: staged chord entry over the real pypiano_2607 chain.

Composes the library's InputRouter / EventQueue / PolySynth / keyboard geometry with a
spike-owned event loop, HUD, and a lightweight pygame.mixer audition. It does NOT edit
src/ and does NOT subclass PianoApp (whose dispatch/__init__ aren't extension points) --
it is a parallel shell that reuses the components.

Design decisions baked in (all "spike-simple"; see README.md / status_active.md):
  * feel-test slice, the sketch's shape only; ONE preset slot (key Z); keyboard-first
    (mouse drives only the HUD buttons, not the piano keys).
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
from pypiano_2607.gui import (
    build_keys, offset_keys, note_name,
    WHITE_QWERTY, BLACK_QWERTY, key_to_midi,
    WIDTH, HEIGHT, MARGIN,
)

import hud
from audition import Audition

HUD_H = 200
WIN_W = WIDTH + 2 * MARGIN
WIN_H = HUD_H + HEIGHT + MARGIN
FLASH_MS = 350


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

        # library components
        self.wk, self.bk = build_keys()
        offset_keys(self.wk + self.bk, MARGIN, HUD_H)      # keyboard below the HUD strip
        self.key_to_midi = key_to_midi(pygame)
        self.router = InputRouter(tuning=self._tuning)
        self.queue = EventQueue()
        factory = PianoVoice if voice == "piano" else SineVoice
        self.synth = PolySynth(self.queue, voice_factory=factory)

        # spike UI
        self.hud = hud.Hud(WIN_W, HUD_H, MARGIN)
        self._z_key = pygame.key.key_code("z")
        mapped = [m for _, m in WHITE_QWERTY + BLACK_QWERTY]
        self.audition = Audition(mapped, sr=SR)
        self._labels = {m: (ch.upper(), note_name(m)) for ch, m in WHITE_QWERTY + BLACK_QWERTY}
        self._key_font = pygame.font.Font(None, 22)
        self._name_font = pygame.font.Font(None, 18)

        # state
        self.mode = "live"                                 # 'live' | 'staged'
        self.staged: list[int] = []                        # pending midi, ordered
        self.preset: list[int] | None = None               # the single Z slot
        self._flash: dict[int, int] = {}                   # midi -> expiry (ticks ms)
        self._ringing: set[int] = set()                    # committed ids w/ no natural off
        self.hint = "Live mode. Tab to enter staged entry."

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
        self.router = InputRouter(tuning=self._tuning)     # keep the temperament
        if clear_staged:
            self.staged.clear()

    # --- staged-entry actions -------------------------------------------------

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
        if self.preset is not None:
            self.hint = "Preset Z is full - shift+Z to forget it first."
            return
        self.preset = list(self.staged)
        self.hint = "Saved to Z:  " + "  ·  ".join(note_name(m) for m in self.preset)
        self.staged.clear()

    def _release_staged(self) -> None:
        self.staged.clear()
        self.hint = "Released the pending chord."

    def _preset_fire(self) -> None:
        if not self.preset:
            self.hint = "Z is empty - stage a chord and Save it first."
            return
        for midi in self.preset:
            self._fire(midi)
        self.hint = "Z fired:  " + "  ·  ".join(note_name(m) for m in self.preset)

    def _preset_forget(self) -> None:
        if self.preset is not None:
            self.preset = None
            self.hint = "Forgot the chord on Z."

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
            shift = bool(event.mod & pygame.KMOD_SHIFT)
            if event.key == self._z_key:                   # preset: fire / (shift) forget
                self._preset_forget() if shift else self._preset_fire()
                return True
            if self.mode == "staged" and event.key == pygame.K_SPACE:
                self._play_chord()
                return True
            if event.key in self.key_to_midi:
                midi = self.key_to_midi[event.key]
                if self.mode == "live":
                    self._press(midi)
                elif shift:
                    self._stage_shift(midi)
                else:
                    self._stage_plain(midi)
            return True

        if event.type == pygame.KEYUP:
            if self.mode == "live" and event.key in self.key_to_midi:
                self._release(self.key_to_midi[event.key])  # staged mode: KEYUP ignored
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
        preset_names = [note_name(m) for m in self.preset] if self.preset else None
        self.hud.draw(self.screen, mode=self.mode, staged_names=staged_names,
                      preset_names=preset_names, tuning_label=self.tuning_label,
                      hint=self.hint)
        hud.draw_keyboard(
            self.screen, self.wk, self.bk,
            held=self.router.held, staged=set(self.staged), flashing=self._flashing(),
            labels=self._labels, key_font=self._key_font, name_font=self._name_font,
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
