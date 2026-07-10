"""Single source of truth; these were previously duplicated/scattered across the spikes.

Module-level constants ONLY. No numpy, no logic -- just the tuning/sizing numbers
that the spikes each redeclared. Import these from here instead of redefining them.
"""

import math

SR = 44100                       # sample rate (Hz)
BLOCK_FRAMES = 383               # reference block for HEADLESS driving only; a LIVE
                                 # OutputStream must honor the callback frames arg --
                                 # never hard-code block length in real streams
BLOCK_PERIOD = BLOCK_FRAMES / SR # ~8.68 ms -- the audio callback's drain cadence

AMP = 0.2                        # master output gain, applied ONCE at the mix stage (see AMP-MOVE)

ATTACK_MS = 6.0                  # linear attack ramp (anti-click, from the synth recipe)
RELEASE_MS = 20.0                # linear release fade (anti-click, from the synth recipe)

N_PARTIALS = 16                  # inharmonic partials per PianoVoice
INHARMONICITY = 4.0e-4           # B in f_k = k*f0*sqrt(1 + B*k^2)  (stiff-string model)
ROLLOFF = 1.2                    # partial amplitude ~ 1/k^ROLLOFF
TAU0 = 1.6                       # fundamental decay time constant (s)
TAU_DECAY = 0.25                 # higher partials die sooner: tau_k = TAU0 / (1 + TAU_DECAY*(k-1))

MAX_VOICES = 16                  # polyphony pool size; fixed => no per-block object allocation

TWO_PI = 2.0 * math.pi
