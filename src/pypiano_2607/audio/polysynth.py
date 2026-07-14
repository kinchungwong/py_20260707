"""A fixed pool of voices summed and soft-limited in the audio callback.

Promoted from the polyphony_voices spike. The allocation / voice-stealing /
soft-limiting logic is unchanged; the structural changes are:

  * keyed on ``sounder_id`` (the opaque acoustic-object identity) instead of a
    MIDI number -- the synth NEVER converts MIDI; note-on carries ``ev.freq``
    directly (Hz), resolved by the caller via ``pitch``.
  * THE AMP-MOVE: voices now render pure timbre; the master ``AMP`` gain is
    applied ONCE here at the mix stage (``mix *= self.amp``) BEFORE the tanh
    limiter. ``sum(AMP*x_i) == AMP*sum(x_i)``, so the output is identical.
"""

from __future__ import annotations

import numpy as np

from ..config import MAX_VOICES, AMP
from ..events import NoteKind, NoteEvent
from ..queue import EventQueue
from .envelope import EnvStage
from .voice import SineVoice


class PolySynth:
    """A fixed pool of voices summed and soft-limited in the callback."""

    def __init__(self, queue: EventQueue, max_voices: int = MAX_VOICES,
                 voice_factory=None, *, amp: float = AMP):
        self.queue = queue
        factory = voice_factory or SineVoice          # swap in a richer voice here
        self.voices = [factory() for _ in range(max_voices)]
        self.voice_sounder: list[int | None] = [None] * max_voices   # which sounder each voice holds
        self.status_flags = 0
        self.amp = amp

    def active_count(self) -> int:
        return sum(1 for v in self.voices if v.env.stage is not EnvStage.IDLE)

    def _alloc(self, sounder_id: int) -> int:
        # 1. a voice already on this sounder (still sounding) -> retrigger it.
        for i, s in enumerate(self.voice_sounder):
            if s == sounder_id and self.voices[i].env.stage is not EnvStage.IDLE:
                return i
        # 2. a free (IDLE) voice.
        for i, v in enumerate(self.voices):
            if v.env.stage is EnvStage.IDLE:
                return i
        # 3. none free -> steal the QUIETEST voice (a releasing voice has the
        #    lowest level, so it naturally gets stolen before a held one).
        return min(range(len(self.voices)), key=lambda i: self.voices[i].env.level)

    def handle(self, ev: NoteEvent) -> None:
        if ev.kind is NoteKind.ON:
            assert ev.freq is not None, "ON events always carry a frequency"
            i = self._alloc(ev.sounder_id)
            self.voices[i].note_on(ev.freq)             # retune + gate attack (Hz directly)
            self.voice_sounder[i] = ev.sounder_id
        elif ev.kind is NoteKind.OFF:
            for i, s in enumerate(self.voice_sounder):
                if s == ev.sounder_id and self.voices[i].env.stage in (EnvStage.ATTACK, EnvStage.SUSTAIN):
                    self.voices[i].note_off()
                    break

    def render(self, frames: int, limit: bool = True) -> np.ndarray:
        mix = np.zeros(frames, dtype=np.float64)
        for i, v in enumerate(self.voices):
            if v.env.stage is not EnvStage.IDLE:
                mix += v.render(frames)
                if v.env.stage is EnvStage.IDLE:      # finished releasing this block
                    self.voice_sounder[i] = None
        mix *= self.amp                               # master gain, applied ONCE (AMP-MOVE)
        if limit:
            np.tanh(mix, out=mix)                      # soft clip: never > 1, ~linear when small
        return mix.astype(np.float32)

    def callback(self, outdata, frames: int, time_info, status) -> None:
        if status:
            self.status_flags += 1
        for ev in self.queue.drain():
            self.handle(ev)
        outdata[:, 0] = self.render(frames)
