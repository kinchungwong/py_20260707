"""Linear attack/sustain/release GATE envelope, advanced per audio block.

Promoted verbatim from the realtime_envelope_release spike (the state machine and
its click-free ramp-from-current-level render()); the only change is that the
timing (sr / attack_ms / release_ms) is now taken as constructor arguments,
defaulting to the values in ``config``, instead of module globals.
"""

from __future__ import annotations

from enum import Enum

import numpy as np

from ..config import SR, ATTACK_MS, RELEASE_MS


class EnvStage(Enum):
    IDLE = "idle"
    ATTACK = "attack"
    SUSTAIN = "sustain"
    RELEASE = "release"


class Envelope:
    """Linear attack/sustain/release GATE envelope, advanced per block.

    Key property: both transitions ramp from the CURRENT level, so an event
    landing at any sample never produces a jump:
      * note_off -> RELEASE from the current level down to 0 over ~RELEASE_MS.
      * note_on  -> ATTACK from the current level up to 1 (click-free retrigger).
    render() may cross a stage boundary in the middle of a block; it processes the
    block in per-stage segments until `frames` samples are produced.
    """

    def __init__(self, *, sr: int = SR, attack_ms: float = ATTACK_MS,
                 release_ms: float = RELEASE_MS):
        self.stage = EnvStage.IDLE
        self.level = 0.0
        self.attack_samples = max(1, round(attack_ms / 1000.0 * sr))
        self.release_samples = max(1, round(release_ms / 1000.0 * sr))
        self.attack_step = 1.0 / self.attack_samples      # gain per sample, ramping up
        self.release_step = 1.0 / self.release_samples    # placeholder; set on note_off

    def note_on(self) -> None:
        self.stage = EnvStage.ATTACK          # from current level -> click-free retrigger

    def note_off(self) -> None:
        if self.stage in (EnvStage.ATTACK, EnvStage.SUSTAIN):
            if self.level <= 0.0:
                self.stage = EnvStage.IDLE
            else:
                # Ramp from the current level to 0 over release_samples, so the
                # release always spans ~RELEASE_MS regardless of where it starts.
                self.release_step = self.level / self.release_samples
                self.stage = EnvStage.RELEASE

    def render(self, frames: int) -> np.ndarray:
        gain = np.empty(frames, dtype=np.float64)
        pos = 0
        while pos < frames:
            if self.stage is EnvStage.IDLE:
                gain[pos:] = 0.0
                self.level = 0.0
                pos = frames
            elif self.stage is EnvStage.SUSTAIN:
                gain[pos:] = 1.0
                self.level = 1.0
                pos = frames
            elif self.stage is EnvStage.ATTACK:
                step = self.attack_step
                n_to_full = max(1, int(np.ceil((1.0 - self.level) / step)))
                seg = min(frames - pos, n_to_full)
                ramp = self.level + step * np.arange(1, seg + 1)
                np.clip(ramp, 0.0, 1.0, out=ramp)
                gain[pos:pos + seg] = ramp
                self.level = float(ramp[-1])
                pos += seg
                if self.level >= 1.0 - 1e-12:
                    self.level = 1.0
                    self.stage = EnvStage.SUSTAIN
            else:  # RELEASE
                step = self.release_step
                n_to_zero = max(1, int(np.ceil(self.level / step)))
                seg = min(frames - pos, n_to_zero)
                ramp = self.level - step * np.arange(1, seg + 1)
                np.clip(ramp, 0.0, None, out=ramp)
                gain[pos:pos + seg] = ramp
                self.level = float(ramp[-1])
                pos += seg
                if self.level <= 1e-12:
                    self.level = 0.0
                    self.stage = EnvStage.IDLE
        return gain
