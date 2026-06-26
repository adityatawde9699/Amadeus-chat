# Troubleshooting

A practical guide to the problems you are most likely to hit, grouped by area.
Each entry lists the **symptom**, the **cause**, and the **fix**.

## Quick Diagnostics

Run these first; they reveal most configuration problems:

```bash
amadeus --version                 # confirms the package is installed
amadeus config                    # shows effective config, incl. model.path
amadeus config --path             # confirms the config file location
uv run python -m compileall amadeus   # confirms the source imports cleanly
uv run pytest -q                   # confirms a healthy install
```

## Installation Issues

### `amadeus: command not found`
- **Cause:** the virtual environment is not active, or the package was not
  installed with an entry point.
- **Fix:** `source .venv/bin/activate`, or invoke via `uv run amadeus …`. Verify
  with `pip show amadeus-chat`.

### `pip install -e .` produces no usable command
- **Cause:** you are on a pre-0.1.0 checkout where the `amadeus` package did not
  exist.
- **Fix:** update to 0.1.0+ (`git pull`), then reinstall.

### `ModuleNotFoundError: No module named 'requests'` (or `bs4`)
- **Cause:** base dependencies were not installed (partial environment).
- **Fix:** `uv sync` (or `pip install -e .`). These are required, not optional.

## Dependency Conflicts

### `llama-cpp-python` fails to build
- **Symptom:** a long C/C++ compiler error during install.
- **Cause:** missing build toolchain.
- **Fix:** install build tools, then retry:

  | Platform | Command |
  | --- | --- |
  | Debian/Ubuntu | `sudo apt install build-essential` |
  | Fedora | `sudo dnf groupinstall "Development Tools"` |
  | macOS | `xcode-select --install` |
  | Windows | Install "Desktop development with C++" (VS Build Tools) |

  Then `uv sync --extra llm`.

### Heavy/old packages reappear (`torch`, `sentence-transformers`)
- **Cause:** an environment resolved against a stale `requirements.txt`.
- **Fix:** `pyproject.toml` is the source of truth — `uv lock && uv sync`. The
  legacy RAG stack is no longer a dependency.

### Wrong Python version
- **Symptom:** `tomllib`/syntax errors, or `requires-python` resolution failures.
- **Cause:** Python < 3.12.
- **Fix:** use Python 3.12+ (`uv python install 3.12`); `.python-version` pins it.

## Data / Storage Issues

### `tasks.json` looks empty after a crash
- **Cause:** rare, but a previous version could leave partial writes. Current
  versions write atomically.
- **Fix:** check for stray `.tasks.json.*.tmp` files in `~/.amadeus/` (safe to
  delete). Restore from a backup if needed (see [database.md](database.md#backup-restore--migration)).

### A note will not open / wrong note shown
- **Symptom:** `learn show <slug>` says ambiguous, or showed an unexpected note.
- **Cause:** prefix matched multiple notes (older behaviour) — now Amadeus
  prefers an exact slug and warns on ambiguity.
- **Fix:** use the full slug shown by `amadeus learn list`.

### `learn new` refuses to create a note
- **Symptom:** `Note already exists`.
- **Cause:** a note with that slug exists; overwrite is guarded.
- **Fix:** pass `--force` to overwrite, or pick a different title.

## Docker Issues

### Data does not persist between runs
- **Cause:** no volume mounted at the container's home.
- **Fix:** mount it: `-v "$HOME/.amadeus:/root/.amadeus"`. See
  [deployment.md](deployment.md#docker).

### Image is enormous
- **Cause:** a multi-GB model baked into the image.
- **Fix:** keep models on a mounted volume, not in the image layer.

## Research Issues

### `No search results found.`
- **Cause:** no network, or DuckDuckGo's HTML markup changed.
- **Fix:** verify connectivity; raise `[research].fetch_timeout`; retry later.
  Research depends on external markup and can break when sites change.

### `Could not extract usable text from any source.`
- **Cause:** result pages were JS-heavy or blocked the request.
- **Fix:** try a more specific topic; some pages cannot be parsed without a
  browser. Use `--no-llm` to at least capture raw excerpts.

### Research is slow
- **Cause:** fetching up to `max_pages` pages with a polite delay, plus LLM load.
- **Fix:** lower `[research].max_pages`, or use `--no-llm` for a fast,
  deterministic report.

## LLM / AI Issues

### Commit message is a generic template
- **Symptom:** `chore: update <files>` instead of a descriptive message.
- **Cause:** no model discoverable, **or** a reasoning model exhausted its token
  budget thinking and produced nothing after `strip_think`.
- **Fix:**
  - Confirm discovery: `amadeus config | grep model.path`.
  - Ensure `llama-cpp-python` is installed: `uv sync --extra llm`.
  - For reasoning models, the commit prompt already sends `/no_think`; if it
    still truncates, raise `[model].max_tokens`.

### `is_available` is false but I have a model
- **Cause:** the path does not point at an existing file, or `llama-cpp-python`
  is not importable.
- **Fix:** check the path resolves (`amadeus config`), and that the `llm` extra
  is installed.

### Model output looks like garbage
- **Cause:** using raw completion on an instruct model without its chat template.
- **Fix:** Amadeus uses the chat API internally; if you embed `LLMWrapper`, call
  `chat()` (not `complete()`) for instruct models. See [ai.md](ai.md#prompt-construction).

### Out of memory while loading a model
- **Cause:** model too large for available RAM.
- **Fix:** use a smaller Q4_K_M model (1.5B), lower `n_ctx`. See
  [performance.md](performance.md) and [ai.md](ai.md#tuning-for-low-ram-machines).

## System Maintenance Issues

### `sys clean` freed nothing
- **Cause:** targets already clean, not on the allow-list, or insufficient
  privileges for apt/journald cleaners.
- **Fix:** run `amadeus sys clean --dry-run` to see what *would* be freed; ensure
  targets are recognized categories; run privileged cleaners with appropriate
  rights. See [security.md](security.md#system-cleanup).

### `sys clean` skipped my path
- **Cause:** the path is not a recognized category (allow-list enforced even if
  you added it to config).
- **Fix:** only the supported categories are cleaned by design.

## Common Runtime Errors

| Message | Likely cause | Fix |
| --- | --- | --- |
| `Not inside a git repository.` | `git` command run outside a repo | `cd` into a repo |
| `No task with id=N.` | Wrong/removed task id | `amadeus task list --all` |
| `Query has no usable tokens…` | Query was all stopwords | Use distinctive terms |
| `Knowledge base is empty.` | No notes yet | `amadeus learn new …` |
| `Skipping unrecognised target…` | Clean path not allow-listed | Use a supported category |

## Performance Bottlenecks

- **Slow note search on a large corpus:** the index cache should make repeats
  fast; if every search is slow, the cache may be unwritable — check permissions
  on `~/.amadeus/indexes/`.
- **Repeated LLM commands feel slow:** each pays the model load cost by design.
  Batch them; a persistent backend is on the [roadmap](../ROADMAP.md).

## Still Stuck?

- Re-run with Python logging enabled (see [monitoring.md](monitoring.md#internal-logging)).
- Search existing [issues](https://github.com/adityatawde9699/Amadeus-chat/issues).
- Open a new issue with your OS, Python version, exact command, and full output.
