# Design — staged chord entry HUD

**Status: Sketch** · Grew out of
[`../discussions/2026-07-10/keyboard-and-input-surface.md`](../discussions/2026-07-10/keyboard-and-input-surface.md)
and
[`../discussions/2026-07-10/ui-affordance-and-feedback.md`](../discussions/2026-07-10/ui-affordance-and-feedback.md)
· Last iterated 2026-07-10.

A modality HUD combined with staged chord entry and chord-mode presets: a way to build
a chord out of keys pressed at different real-world times but fired together, plus a
way to save a built chord onto a single key for one-press recall later — the "chord
mode + staged entry" hybrid (archetype 5) from the keyboard-input discussion.

## What this is (and isn't)

This is a **UI/interaction sketch only** — no audio, no PyGame, no `InputRouter`. It ran
inside the conversation's own design-preview tool, iterated live across several rounds
of feedback, not in the real app. Its CSS leans on host-provided variables
(`--surface-1`, `--bg-accent`, `--text-accent`, `--bg-danger`, `--bg-success`,
`--border-accent`, `--radius`, etc.) and a bundled icon webfont that exist only inside
that preview tool — the reference source at the bottom is kept as an **exact behavioral
record**, not a deployable file. Opening it directly in a browser will not reproduce the
same look.

## What it demonstrates

1. Modality HUD basics: a tuning badge and a live/staged mode toggle.
2. Discoverability: on-screen keys labeled physical-key-over-note.
3. Staged chord entry, with three independent ways to remove one staged note.
4. Chord-mode presets: save a staged chord to a key, fire the whole chord from that one
   key afterward, in either mode.
5. One unified "forget" gesture (shift-click) applied to two different targets.
6. `Reset` as a distinct, broader action from `Release`.

## State model

- `mode`: `'live' | 'staged'` — a persistent toggle (see "A gesture choice, made
  implicitly" below).
- `tuning`: display-only badge, `'12-TET' | 'Just intonation · C'` — cosmetic in this
  sketch, not wired to anything real.
- `staged`: an ordered list of note names currently pending; only meaningful in staged
  mode.
- `presets`: a **fixed 4-slot array** (keys `Z`, `X`, `C`, `V`), each `null` or a list of
  notes. Index-stable — forgetting one slot never shifts the others, so `Save` can
  always target "the next `null` slot" without needing to know history.

## Controls and gestures

Every "click" below is shorthand for two physical actions this design treats
identically: clicking the on-screen key with a mouse, or typing the corresponding
physical key on a real keyboard — the sketch's on-screen buttons stand in for the real
app's PyGame key events.

| Control | Action | Why |
|---|---|---|
| Tuning badge | Click toggles the displayed value | Cosmetic placeholder for a real tuning indicator |
| Mode button | Click flips `live ⇄ staged`, clearing `staged` on either transition | Color-coded (accent when staged) — the mode-error mitigation named in `ui-affordance-and-feedback.md` |
| A key, live mode | Click gives a brief flash, simulating a played note | |
| A key, staged mode, plain click or type | Always adds the note to `staged` if absent (no-op if already staged), and plays a short **audition** beep (~0.1–0.2s) reminding the player what that key sounds like | Resolves the "feedback while staging" question left open below — audition wins over a silent buffer |
| A key, staged mode, shift-click or shift+type | Toggles: adds if absent, removes if present | The "forget" gesture, target 1 of 2 |
| Tray chip `×` | Removes that one staged note | A third, tray-based way to remove a single staged note |
| `Play chord` | Fires all staged notes together (visual only), then clears `staged` | The explicit-commit gesture |
| Space bar, staged mode | Same as clicking `Play chord`: fires all staged notes, then clears `staged` | Reaches for the near-universal space-bar-as-transport convention (DAW/media play/stop) — same reuse instinct as `Release`. What (if anything) space bar does outside staged mode is explicitly unclaimed — see open questions |
| `Save chord` | Binds `staged` to the next empty preset slot, then clears `staged`. Label previews the target live (`Save chord → Z`); softens to a muted `Presets full` — never `disabled` — when no slot is free | Staged entry as an authoring path for chord-mode presets; stays clickable when "full" so the reactive hint still fires |
| `Release` | Clears `staged` without playing | Named for the synth's own envelope `RELEASE` stage — see `../discussions/2026-07-10/terminology-policy.md` |
| Preset slot (`Z`/`X`/`C`/`V`), plain click | If bound: fires every member key together, in either mode. If empty: a neutral no-op flash | The "one key, many notes" chord-mode idea |
| Preset slot, shift-click | If bound: unbinds it in place — the slot stays at that index, doesn't shift. If empty: neutral no-op flash | The "forget" gesture, target 2 of 2 |
| `Reset` | Clears `staged` and unbinds all four presets, one action | Always visible, not staged-mode-only, since presets exist regardless of mode |

## A gesture choice, made implicitly

`keyboard-and-input-surface.md` named four candidate "commit" gestures and the choice
among them was explicitly left open ("Not ready to pick — keep discussing"). Building
this sketch quietly converged on **two of them combined**, without that being a
deliberate decision at the time:

- the **Mode button** is candidate 4, a **true persistent mode toggle** — not a
  self-cancelling quasimode;
- `Play chord` is candidate 2, an **explicit commit key**, layered inside that mode.

Candidate 1 (modifier-held, release-fires — a genuine quasimode) and candidate 3
(timeout-window auto-commit) were never tried here. **This sketch is not neutral
evidence about which commit gesture feels best** — it only demonstrates the
toggle-plus-explicit-commit combination. The mode-error risk that combination carries
is the reason for the accent-colored Mode button and the persistent key-highlighting
while staged (both from `ui-affordance-and-feedback.md`), not an accident.

## Open questions carried over

- Is the quasimode (modifier-held, release-fires) worth prototyping as an alternative
  to the persistent-toggle-plus-explicit-commit shape used here?
- Should `Save chord`'s slot targeting ever be user-chosen, rather than always
  next-available?
- What, if anything, should space bar do outside staged mode? Deliberately left
  unclaimed (2026-07-10) rather than designed now — a candidate for a future
  sustain/hold function, but not decided.
- None of this is wired to real audio, tuning, or `InputRouter`. A first real spike
  (see "Where new exploratory code goes" in `keyboard-and-input-surface.md`) would need
  to decide how much of this state model maps onto real input events versus being
  redesigned once actual key-event timing is in play.

## Reference source (exact behavior, not a deployable file)

```html
<div style="background: var(--surface-1); border-radius: 12px; border: 0.5px solid var(--border); padding: 1rem 1.25rem; max-width: 640px; margin: 0 auto;">
<h2 class="sr-only">Mockup of a modality HUD overlay on the piano app: a tuning badge, a live or staged mode toggle, on-screen keys showing the physical key mapped to its note, shift-click to toggle a staged key, a pending-chord tray with play chord, save chord and release actions, four chord-preset slots with a reset control, and shift-click on a slot to forget it.</h2>

<div style="display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px;">
  <button id="tuning-btn">Tuning: 12-TET</button>
  <button id="mode-btn" style="font-weight:500;">Mode: live</button>
</div>

<div id="keys" style="display:grid; grid-template-columns: repeat(8, minmax(0,1fr)); gap:6px; margin-bottom:12px;"></div>

<div style="margin-bottom:16px;">
  <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; gap:8px;">
    <p style="font-size:12px; color:var(--text-secondary); margin:0;">Chord presets <span style="color:var(--text-muted);">(shift-click a saved slot to forget it)</span></p>
    <button id="reset-btn" style="font-size:12px; padding:4px 10px;">Reset</button>
  </div>
  <div id="presets" style="display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:6px;"></div>
</div>

<div id="tray-wrap" style="border-top: 0.5px solid var(--border); padding-top:12px; display:none;">
  <p style="font-size:12px; color:var(--text-secondary); margin:0 0 8px;">Pending chord <span style="color:var(--text-muted);">(shift-click a staged key to remove it)</span></p>
  <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
    <div id="tray" style="display:flex; gap:6px; flex-wrap:wrap; flex:1; min-height:28px; align-items:center;"></div>
    <button id="commit-btn">Play chord</button>
    <button id="save-btn">Save chord</button>
    <button id="clear-btn">Release</button>
  </div>
</div>

<p id="hint" style="font-size:12px; color:var(--text-muted); margin: 12px 0 0;">Click a key to play it.</p>
</div>

<script>
(function(){
  var keysData = [
    {key:'A', note:'C4'}, {key:'S', note:'D4'}, {key:'D', note:'E4'}, {key:'F', note:'F4'},
    {key:'G', note:'G4'}, {key:'H', note:'A4'}, {key:'J', note:'B4'}, {key:'K', note:'C5'}
  ];
  var presetKeys = ['Z', 'X', 'C', 'V'];
  var presets = [null, null, null, null];

  var keysEl = document.getElementById('keys');
  keysData.forEach(function(k){
    var btn = document.createElement('button');
    btn.dataset.note = k.note;
    btn.style.cssText = 'display:flex; flex-direction:column; align-items:center; gap:2px; padding:10px 2px;';
    btn.innerHTML = '<span style="font-weight:500; font-size:13px;">'+k.key+'</span><span style="font-size:11px; color:var(--text-secondary);">'+k.note+'</span>';
    keysEl.appendChild(btn);
  });

  var presetsEl = document.getElementById('presets');
  presetKeys.forEach(function(k, i){
    var btn = document.createElement('button');
    btn.dataset.idx = i;
    btn.style.cssText = 'display:flex; flex-direction:column; align-items:center; gap:2px; padding:10px 2px;';
    btn.innerHTML = '<span style="font-weight:500; font-size:13px;">'+k+'</span><span class="preset-label" style="font-size:11px; color:var(--text-secondary);">—</span>';
    presetsEl.appendChild(btn);
  });

  var mode = 'live';
  var tuning = '12-TET';
  var staged = [];

  var modeBtn = document.getElementById('mode-btn');
  var tuningBtn = document.getElementById('tuning-btn');
  var trayWrap = document.getElementById('tray-wrap');
  var tray = document.getElementById('tray');
  var hint = document.getElementById('hint');
  var saveBtn = document.getElementById('save-btn');
  var resetBtn = document.getElementById('reset-btn');

  function renderMode(){
    if (mode === 'live') {
      modeBtn.textContent = 'Mode: live';
      modeBtn.style.background = '';
      modeBtn.style.color = '';
      modeBtn.style.borderColor = '';
      trayWrap.style.display = 'none';
      hint.textContent = 'Click a key to play it.';
    } else {
      modeBtn.textContent = 'Mode: staged';
      modeBtn.style.background = 'var(--bg-accent)';
      modeBtn.style.color = 'var(--text-accent)';
      modeBtn.style.borderColor = 'var(--border-accent)';
      trayWrap.style.display = 'block';
      hint.textContent = 'Click keys to add to the pending chord, then commit.';
    }
  }

  function renderTray(){
    tray.innerHTML = '';
    if (staged.length === 0) {
      var empty = document.createElement('span');
      empty.style.cssText = 'font-size:12px; color:var(--text-muted);';
      empty.textContent = 'Nothing staged yet';
      tray.appendChild(empty);
      return;
    }
    staged.forEach(function(note, i){
      var chip = document.createElement('span');
      chip.style.cssText = 'display:inline-flex; align-items:center; gap:4px; background:var(--bg-accent); color:var(--text-accent); font-size:12px; padding:3px 8px; border-radius: var(--radius);';
      var label = document.createElement('span');
      label.textContent = note;
      var remove = document.createElement('span');
      remove.textContent = '×';
      remove.style.cssText = 'cursor:pointer; font-weight:500;';
      remove.dataset.i = i;
      chip.appendChild(label);
      chip.appendChild(remove);
      tray.appendChild(chip);
    });
  }

  function renderKeyHighlights(){
    var buttons = keysEl.querySelectorAll('button');
    buttons.forEach(function(btn){
      var note = btn.dataset.note;
      if (mode === 'staged' && staged.indexOf(note) !== -1) {
        btn.style.background = 'var(--bg-accent)';
        btn.style.borderColor = 'var(--border-accent)';
      } else {
        btn.style.background = '';
        btn.style.borderColor = '';
      }
    });
  }

  function renderPresets(){
    var buttons = presetsEl.querySelectorAll('button');
    buttons.forEach(function(btn, i){
      var bound = presets[i];
      btn.querySelector('.preset-label').textContent = bound ? bound.join('+') : '—';
    });
  }

  function nextFreeSlot(){
    return presets.findIndex(function(p){ return p === null; });
  }

  function renderSaveButton(){
    var slotIndex = nextFreeSlot();
    if (slotIndex === -1) {
      saveBtn.textContent = 'Presets full';
      saveBtn.style.color = 'var(--text-muted)';
    } else {
      saveBtn.textContent = 'Save chord → ' + presetKeys[slotIndex];
      saveBtn.style.color = '';
    }
  }

  modeBtn.addEventListener('click', function(){
    mode = mode === 'live' ? 'staged' : 'live';
    staged = [];
    renderMode();
    renderTray();
    renderKeyHighlights();
  });

  tuningBtn.addEventListener('click', function(){
    tuning = tuning === '12-TET' ? 'Just intonation · C' : '12-TET';
    tuningBtn.textContent = 'Tuning: ' + tuning;
  });

  keysEl.addEventListener('click', function(e){
    var btn = e.target.closest('button');
    if (!btn) return;
    var note = btn.dataset.note;
    if (mode === 'live') {
      btn.style.background = 'var(--bg-accent)';
      setTimeout(function(){ renderKeyHighlights(); }, 180);
      return;
    }
    var idx = staged.indexOf(note);
    if (e.shiftKey && idx !== -1) {
      staged.splice(idx, 1);
      renderTray();
      btn.style.background = 'var(--bg-danger)';
      setTimeout(function(){ renderKeyHighlights(); }, 220);
      return;
    }
    if (idx === -1) {
      staged.push(note);
    }
    renderTray();
    renderKeyHighlights();
  });

  presetsEl.addEventListener('click', function(e){
    var btn = e.target.closest('button');
    if (!btn) return;
    var idx = Number(btn.dataset.idx);
    var bound = presets[idx];
    if (e.shiftKey && bound) {
      presets[idx] = null;
      renderPresets();
      renderSaveButton();
      hint.textContent = 'Forgot the chord on key ' + presetKeys[idx];
      btn.style.background = 'var(--bg-danger)';
      setTimeout(function(){ btn.style.background = ''; }, 300);
      return;
    }
    if (!bound) {
      btn.style.background = 'var(--surface-2)';
      setTimeout(function(){ btn.style.background = ''; }, 150);
      return;
    }
    bound.forEach(function(note){
      var keyBtn = keysEl.querySelector('button[data-note="'+note+'"]');
      if (keyBtn) keyBtn.style.background = 'var(--bg-success)';
    });
    btn.style.background = 'var(--bg-success)';
    hint.textContent = 'Chord mode: key ' + presetKeys[idx] + ' fired ' + bound.join(' · ') + ' together';
    setTimeout(function(){
      btn.style.background = '';
      renderKeyHighlights();
    }, 500);
  });

  tray.addEventListener('click', function(e){
    var i = e.target.dataset.i;
    if (i !== undefined) {
      staged.splice(Number(i), 1);
      renderTray();
      renderKeyHighlights();
    }
  });

  document.getElementById('commit-btn').addEventListener('click', function(){
    if (staged.length === 0) return;
    var notes = staged.slice();
    notes.forEach(function(note){
      var btn = keysEl.querySelector('button[data-note="'+note+'"]');
      if (btn) btn.style.background = 'var(--bg-success)';
    });
    hint.textContent = 'Played: ' + notes.join(' · ');
    staged = [];
    renderTray();
    setTimeout(function(){
      renderKeyHighlights();
      if (mode === 'staged') hint.textContent = 'Click keys to add to the pending chord, then commit.';
    }, 600);
  });

  saveBtn.addEventListener('click', function(){
    if (staged.length === 0) return;
    var slotIndex = nextFreeSlot();
    if (slotIndex === -1) {
      hint.textContent = 'All preset slots are full — shift-click one to forget it first.';
      return;
    }
    presets[slotIndex] = staged.slice();
    renderPresets();
    renderSaveButton();
    hint.textContent = 'Saved to key ' + presetKeys[slotIndex] + ': ' + staged.join(' · ');
    staged = [];
    renderTray();
    renderKeyHighlights();
    setTimeout(function(){
      if (mode === 'staged') hint.textContent = 'Click keys to add to the pending chord, then commit.';
    }, 1800);
  });

  document.getElementById('clear-btn').addEventListener('click', function(){
    staged = [];
    renderTray();
    renderKeyHighlights();
    hint.textContent = 'Released.';
    setTimeout(function(){
      if (mode === 'staged') hint.textContent = 'Click keys to add to the pending chord, then commit.';
    }, 1000);
  });

  resetBtn.addEventListener('click', function(){
    staged = [];
    presets = [null, null, null, null];
    renderTray();
    renderKeyHighlights();
    renderPresets();
    renderSaveButton();
    resetBtn.style.background = 'var(--bg-danger)';
    setTimeout(function(){ resetBtn.style.background = ''; }, 300);
    hint.textContent = 'Reset: all keys released, all chord presets forgotten.';
    setTimeout(function(){
      hint.textContent = mode === 'staged' ? 'Click keys to add to the pending chord, then commit.' : 'Click a key to play it.';
    }, 1800);
  });

  renderMode();
  renderTray();
  renderPresets();
  renderKeyHighlights();
  renderSaveButton();
})();
</script>
```
