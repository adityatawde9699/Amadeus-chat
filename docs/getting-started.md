# Getting Started

This guide takes you from a clean machine to a working Amadeus installation and
your first few commands in about five minutes.

> **Prerequisites:** Python ≥ 3.12 and `git`. The optional LLM features also need
> a C toolchain (for `llama-cpp-python`) and a GGUF model file.

## 1. Install

The fastest path uses [`uv`](https://github.com/astral-sh/uv):

```bash
git clone https://github.com/adityatawde9699/Amadeus-chat.git
cd Amadeus-chat
uv sync
```

This installs the deterministic core. To add the optional local LLM:

```bash
uv sync --extra llm
```

> Prefer `pip`? See [installation.md](installation.md) for a `venv` + `pip`
> workflow and platform notes.

## 2. First Run

Run the daily dashboard. On first run, Amadeus creates `~/.amadeus/` with a
default `config.toml`, an empty `tasks.json`, and the supporting directories.

```bash
uv run amadeus start
```

You should see three sections: a system snapshot (RAM/CPU/Disk), today's tasks
(empty), and — if you configured project paths — per-project git status.

## 3. Track a Task

```bash
amadeus task add "Read the Amadeus architecture doc"
amadeus task list
amadeus task done 1
```

Tasks are stored as plain JSON in `~/.amadeus/tasks.json`.

## 4. Capture and Search Knowledge

```bash
# Create a note non-interactively
amadeus learn new "BM25 vs embeddings" \
  --no-edit \
  --body "# BM25 vs embeddings

BM25L is deterministic and dependency-light; embeddings need PyTorch."

# Search across all notes (deterministic BM25L ranking)
amadeus learn search "deterministic"

# Show a note
amadeus learn show bm25-vs-embeddings
```

Omitting `--no-edit` opens the note in `$EDITOR` (falling back to
`nano`/`vim`/`vi`).

## 5. (Optional) Enable the Local LLM

Amadeus auto-discovers a model. The simplest setup is to drop or symlink a GGUF
file into `~/.amadeus/models/`:

```bash
mkdir -p ~/.amadeus/models
ln -s /path/to/model.gguf ~/.amadeus/models/

# Confirm it was picked up
amadeus config | grep model.path
```

Now LLM-backed features activate automatically:

```bash
amadeus git commit            # writes a Conventional Commit message
amadeus research "rust ownership model"
```

See [ai.md](ai.md) for model selection, discovery order, and reasoning-model
behaviour.

## 6. Inspect Your Configuration

```bash
amadeus config          # show effective configuration
amadeus config --path   # print the config file path
```

Edit `~/.amadeus/config.toml` by hand to set your name, project paths, and model
tuning. See [configuration.md](configuration.md).

## What to Read Next

| If you want to… | Read |
| --- | --- |
| Understand how the pieces fit | [architecture.md](architecture.md) |
| See every command and flag | [cli.md](cli.md) |
| Tune behaviour | [configuration.md](configuration.md) |
| Run or write tests | [testing.md](testing.md) |
| Fix a problem | [troubleshooting.md](troubleshooting.md) |
| Browse worked examples | [examples.md](examples.md) |
