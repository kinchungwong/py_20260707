# tools/

Repo **maintenance scripts** — small, reviewable tools for keeping the project
consistent. These are dev/CI utilities, distinct from the app itself and from the
`claude/` knowledge base. Each exits non-zero on failure, so they double as CI checks.

Run them with the project venv from the repo root:

## `check_docs_links.py`

Validates that every intra-repo path reference in `claude/**` and `README.md`
(`../memory/...`, `claude/vision/...`, etc.) resolves to a real file or directory.
Run it after moving or renaming any doc/spike/memory file.

```
.venv/bin/python tools/check_docs_links.py              # fails if any link is broken
.venv/bin/python tools/check_docs_links.py --wikilinks  # also list dangling [[wikilinks]]
```

Dangling `[[wikilinks]]` are reported only as warnings (a not-yet-written memory
note is allowed — see `claude/memory/README.md`); broken paths fail the run.

## `run_spike_tests.py`

Runs each spike's headless self-check (`--selftest` for the GUI spikes,
`--no-play` for the audio spikes) under the SDL dummy drivers, so regressions are
caught without a display. The invocation for each spike is listed explicitly in
the script; spikes with no safe headless mode are listed under `SKIP` with a reason.
(Named `run_spike_tests.py`, not `run_selftests.py`, to avoid confusion with the
pytest-based unit tests.)

```
.venv/bin/python tools/run_spike_tests.py            # run every check
.venv/bin/python tools/run_spike_tests.py -k input   # filter by filename substring
```

When you add a new spike, add it to the `CHECKS` (or `SKIP`) list in the script.
