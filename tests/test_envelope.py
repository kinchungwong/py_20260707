"""Envelope shape + click-free assertions, ported from the realtime_envelope_release
spike _selftest (the envelope portion). Drives the Envelope directly, per block."""

from __future__ import annotations

import numpy as np

from pypiano_2607 import Envelope, EnvStage
from pypiano_2607.config import BLOCK_FRAMES


def _drive_env(env, n_blocks, frames=BLOCK_FRAMES):
    return np.concatenate([env.render(frames) for _ in range(n_blocks)])


def test_idle_is_exact_zero():
    env = Envelope()
    g = _drive_env(env, 3)
    assert env.stage is EnvStage.IDLE
    assert np.all(g == 0.0)


def test_sustain_is_exact_one():
    env = Envelope()
    env.note_on()
    g = _drive_env(env, 40)          # attack -> sustain (well past attack_samples)
    assert env.stage is EnvStage.SUSTAIN
    assert g[-1] == 1.0
    assert env.level == 1.0


def test_full_asr_shape_and_click_free():
    env = Envelope()
    n_pre, n_hold, n_rel = 2, 40, 6

    pre = _drive_env(env, n_pre)
    env.note_on()
    hold = _drive_env(env, n_hold)
    env.note_off()
    rel = _drive_env(env, n_rel)
    g = np.concatenate([pre, hold, rel])

    pre_end = n_pre * BLOCK_FRAMES
    off_idx = pre_end + n_hold * BLOCK_FRAMES

    # 1. IDLE is exactly silent.
    assert np.all(g[:pre_end] == 0.0), "idle envelope not zero"

    # 2. Attack rises from ~0, monotonically, to full.
    assert g[pre_end] < 0.02, f"onset not near zero: {g[pre_end]}"
    attack = g[pre_end:pre_end + env.attack_samples + 2]
    assert np.all(np.diff(attack) >= -1e-12), "attack not monotonic non-decreasing"
    assert g[:off_idx].max() >= 0.999, "attack never reached full level"

    # 3. Sustain is a flat plateau at exactly 1.0 while held.
    plateau = g[pre_end + env.attack_samples + 5:off_idx]
    assert plateau.min() == 1.0 and plateau.max() == 1.0, "sustain not flat at 1.0"

    # 4. Release ramps down monotonically, reaches 0, stays 0.
    release = g[off_idx:off_idx + env.release_samples + 2]
    assert np.all(np.diff(release) <= 1e-12), "release not monotonic non-increasing"
    assert np.all(g[off_idx + env.release_samples + 5:] == 0.0), "not silent after release"

    # 5. Click-free (envelope): no jump larger than a single ramp step.
    max_env_step = float(np.abs(np.diff(g)).max())
    assert max_env_step <= env.attack_step * 1.001, \
        f"envelope discontinuity: {max_env_step} > step {env.attack_step}"


def test_release_from_partial_level_spans_release_ms():
    # note_off mid-attack releases from the CURRENT level (click-free), not from 1.0.
    env = Envelope()
    env.note_on()
    env.render(3)                    # a few samples into the attack, level < 1
    assert env.stage is EnvStage.ATTACK
    partial = env.level
    env.note_off()
    assert env.stage is EnvStage.RELEASE
    g = _drive_env(env, 6)
    assert g.max() <= partial + 1e-9
    assert env.stage is EnvStage.IDLE and env.level == 0.0


def test_retrigger_mid_release_is_click_free():
    # note_on during a release re-attacks from the CURRENT level -> click-free
    # retrigger: the concatenated envelope has no jump at the retrigger seam.
    env = Envelope()
    env.note_on()
    _drive_env(env, 40)              # reach SUSTAIN at 1.0
    env.note_off()
    rel = _drive_env(env, 1)         # partway into the release
    assert env.stage is EnvStage.RELEASE
    mid = env.level
    assert 0.0 < mid < 1.0, f"expected mid-release level, got {mid}"
    env.note_on()                    # retrigger from current level
    assert env.stage is EnvStage.ATTACK
    att = _drive_env(env, 2)
    seam = np.concatenate([rel, att])
    max_step = float(np.abs(np.diff(seam)).max())
    assert max_step <= env.attack_step * 1.001, \
        f"retrigger discontinuity: {max_step} > step {env.attack_step}"
    assert env.stage is EnvStage.SUSTAIN
    assert att.max() >= 0.999          # climbs back to full


def test_note_off_when_idle_is_ignored():
    env = Envelope()
    env.note_off()                   # nothing sounding -> stays idle
    assert env.stage is EnvStage.IDLE


def test_timing_args_scale_ramp_lengths():
    slow = Envelope(sr=44100, attack_ms=12.0, release_ms=40.0)
    fast = Envelope(sr=44100, attack_ms=6.0, release_ms=20.0)
    # doubling the ms roughly doubles the sample counts (allow +-1 for rounding).
    assert abs(slow.attack_samples - 2 * fast.attack_samples) <= 1
    assert abs(slow.release_samples - 2 * fast.release_samples) <= 1
