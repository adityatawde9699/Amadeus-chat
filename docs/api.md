# API Reference

> **Scope note:** Amadeus is a **command-line application**, not a web service.
> It exposes **no HTTP/REST/gRPC endpoints**, no network listener, and no
> authentication tokens. Consequently, this reference documents the two
> interfaces that actually exist:
>
> 1. The **CLI command surface** — the stable, user-facing "API".
> 2. The **internal Python API** — for embedding Amadeus in your own scripts.
>
> Where a conventional REST reference would list method/URL/status codes, the
> CLI equivalents (command, exit code) are given instead.

## CLI Command Surface

Each command is the analogue of an "endpoint". The full, flag-by-flag reference
lives in [cli.md](cli.md); this section is the quick contract table.

| Command | Purpose | Args | Exit codes |
| --- | --- | --- | --- |
| `amadeus start` | Daily dashboard | — | `0` |
| `amadeus task add <title>` | Create a task | `title` | `0`, `2` |
| `amadeus task list [--all]` | List tasks | `--all` | `0` |
| `amadeus task done <id>` | Complete a task | `id:int` | `0`, `1` |
| `amadeus task delete <id>` | Delete a task | `id:int` | `0`, `1` |
| `amadeus git status` | Smart status | — | `0`, `1` |
| `amadeus git commit` | Generate & commit | `-y`, `--no-stage`, `--default-type` | `0`, `1` |
| `amadeus learn new <title>` | Create a note | `--body`, `--no-edit`, `--force` | `0`, `1`, `2` |
| `amadeus learn list` | List notes | — | `0` |
| `amadeus learn search <query>` | BM25L search | `query` | `0`, `2` |
| `amadeus learn show <slug>` | Print a note | `slug` | `0`, `1` |
| `amadeus research <topic>` | Web research | `--no-llm` | `0`, `1`, `2` |
| `amadeus sys status` | Resource metrics | — | `0` |
| `amadeus sys clean` | Allow-listed cleanup | `--dry-run` | `0` |
| `amadeus config` | Show config | `--path` | `0` |

### Exit Code Contract

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Operation failed (not a repo, no results, ambiguous slug, missing id) |
| `2` | Usage error / missing required argument |
| `130` | Interrupted (Ctrl-C) |

### "Request/Response" Example

The CLI consumes argv and emits formatted text + an exit code:

```console
$ amadeus task add "Write API docs"
✓ Task #3 added: Write API docs
$ echo $?
0
```

Machine-readable consumers should prefer the underlying JSON files (see
[database.md](database.md)) or the Python API below, rather than scraping
rendered output.

### curl / SDK Equivalents

Not applicable — there is no HTTP endpoint to `curl` and no network SDK. To
script Amadeus, call the binary or import the package (next section).

```bash
# "SDK" usage is simply invoking the CLI:
amadeus learn search "rust" || echo "search failed with code $?"
```

## Internal Python API

Amadeus is a regular Python package and can be embedded. The public building
blocks are stable within a minor version.

### `amadeus.core.config`

```python
from amadeus.core.config import load_config, Config, config_to_dict

cfg: Config = load_config()          # reads ~/.amadeus/config.toml
print(cfg.user_name, cfg.model.path)
data = config_to_dict(cfg)           # TOML-friendly nested dict
```

| Symbol | Signature | Description |
| --- | --- | --- |
| `load_config` | `(path: Path | None = None) -> Config` | Load (and create defaults for) the config |
| `ensure_amadeus_home` | `(path: Path | None = None) -> Path` | Create the `~/.amadeus` tree idempotently |
| `config_to_dict` | `(cfg: Config) -> dict` | Serialize a `Config` |
| `Config` | dataclass | Typed config with derived path properties |

`Config` exposes derived paths: `config_path`, `tasks_path`,
`knowledge_base_dir`, `research_dir`, `indexes_dir`.

### `amadeus.core.storage`

```python
from amadeus.core import storage

storage.add_task(cfg.tasks_path, "Ship v0.2")
tasks = storage.load_tasks(cfg.tasks_path)
storage.complete_task(cfg.tasks_path, 1)

p = storage.create_note(cfg.knowledge_base_dir, "Title", body="# Title\n\n...")
meta = storage.parse_note_metadata(p)
```

| Symbol | Description |
| --- | --- |
| `slugify(text) -> str` | Kebab-case slug for filenames |
| `load_tasks/save_tasks/add_task/complete_task/delete_task` | Task CRUD over `tasks.json` |
| `list_notes/note_path/create_note/read_note/parse_note_metadata` | Note operations |
| `research_dir/save_research` | Research output |
| `load_index_cache/save_index_cache/file_md5` | BM25 index cache helpers |
| `_write_json` | Atomic JSON writer (temp file + `os.replace`) |

### `amadeus.utils.llm`

```python
from amadeus.utils.llm import llm_session, is_available, strip_think

if is_available(cfg):
    with llm_session(cfg) as llm:        # loads the model
        text = llm.chat([
            {"role": "system", "content": "Be terse. /no_think"},
            {"role": "user", "content": "Summarize: ..."},
        ])
    # model unloaded here; RAM released
clean = strip_think("<think>...</think>final")   # -> "final"
```

| Symbol | Description |
| --- | --- |
| `llm_session(cfg)` | Context manager; yields an `LLMWrapper` or `None` |
| `LLMWrapper.complete(prompt, …)` | Raw completion (think-stripped) |
| `LLMWrapper.chat(messages, …)` | Chat completion with the model's template (think-stripped) |
| `is_available(cfg) -> bool` | True if a model path and `llama-cpp-python` are present |
| `strip_think(text) -> str` | Remove reasoning blocks from output |

> Always prefer `chat()` over `complete()` for instruct models — it applies the
> chat template. See [ai.md](ai.md).

### `amadeus.cli`

```python
from amadeus.cli import main
exit_code = main(["task", "list", "--all"])   # programmatic dispatch
```

| Symbol | Description |
| --- | --- |
| `main(argv=None) -> int` | Parse, dispatch, return exit code |
| `build_parser() -> argparse.ArgumentParser` | Construct the full parser |

### Module command functions

Every feature module exposes `cmd_*(cfg, args) -> int` functions
(`tasks.cmd_add`, `notes.cmd_search`, `git_assist.cmd_commit`, …). They take a
`Config` and an argparse-style namespace and return an exit code, making them
easy to call directly in tests or scripts.

## Rate Limits

There are no application-level rate limits (no server). The only outbound
traffic is the research fetcher, which is bounded by `[research].max_pages` and
`[research].fetch_timeout`, with a polite inter-request delay. See
[configuration.md](configuration.md#research).

## Versioning & Stability

- The CLI command surface follows [Semantic Versioning](https://semver.org/).
  Breaking changes to commands/flags bump the major (post-1.0) or are called out
  in `CHANGELOG.md` pre-1.0.
- The internal Python API is stable within a minor version; private helpers
  (leading underscore) may change without notice.

## See Also

- [cli.md](cli.md) — exhaustive command/flag reference.
- [database.md](database.md) — on-disk formats for machine consumers.
- [ai.md](ai.md) — the LLM interface in depth.
