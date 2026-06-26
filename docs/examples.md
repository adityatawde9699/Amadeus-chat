# Examples

Practical, copy-pasteable recipes that combine Amadeus commands into real
workflows. Commands assume `amadeus` is on your `PATH` (or prefix with
`uv run`).

## Installation & Setup

```bash
# Clone and install (base + optional LLM)
git clone https://github.com/adityatawde9699/Amadeus-chat.git
cd Amadeus-chat
uv sync --extra llm

# First run creates ~/.amadeus and shows the dashboard
uv run amadeus start
```

## Configuration

```bash
# Find and edit your config
amadeus config --path                 # -> ~/.amadeus/config.toml
${EDITOR:-nano} "$(amadeus config --path)"

# Set your name and project paths, then verify
amadeus config
```

Minimal personalized `config.toml`:

```toml
[user]
name = "Ada"

[paths]
projects = ["~/projects/amadeus", "~/work/api"]
```

## Running Locally — A Morning Routine

```bash
amadeus start                         # dashboard: system + tasks + git
amadeus task add "Finish CLI docs"
amadeus task add "Review PR #42"
amadeus task list                     # see what's open
```

## Task Management

```bash
amadeus task add "Write tests for notes module"
amadeus task list
amadeus task done 1                   # complete task #1
amadeus task list --all               # include completed
amadeus task delete 2                 # remove task #2
```

## Knowledge Base

```bash
# Create notes (non-interactively)
amadeus learn new "Rust Ownership" --no-edit --body "# Rust Ownership

Rust uses ownership and a borrow checker to guarantee memory safety
without a garbage collector."

amadeus learn new "Python GIL" --no-edit --body "# Python GIL

The global interpreter lock serializes bytecode execution per process."

# Search and read
amadeus learn list
amadeus learn search "memory safety"
amadeus learn show rust-ownership
```

Capture a note interactively (opens `$EDITOR`):

```bash
EDITOR=vim amadeus learn new "Design notes: caching"
```

## Git Workflow

```bash
cd ~/projects/amadeus

# Inspect changes
amadeus git status

# Generate and accept a Conventional Commit message
amadeus git commit -y

# Override the fallback type when no model is available
amadeus git commit --default-type feat

# Generate a message but keep your own staging
amadeus git commit --no-stage
```

## Web Research

```bash
# Full pipeline with LLM summary (if a model is configured)
amadeus research "rust ownership model"

# Deterministic, fast, no model
amadeus research "rust ownership model" --no-llm

# Read the saved report
cat ~/.amadeus/research/rust-ownership-model/report.md
```

## System Maintenance

```bash
amadeus sys status                    # CPU / RAM / disk / battery / top procs
amadeus sys clean --dry-run           # preview — deletes nothing
amadeus sys clean                     # perform allow-listed cleanup
```

## Enabling the Local LLM

```bash
# Option 1: drop/symlink a model into the discovery directory
mkdir -p ~/.amadeus/models
ln -s /path/to/qwen2.5-1.5b-instruct-q4_k_m.gguf ~/.amadeus/models/

# Option 2: point at a model via environment variable
export AMADEUS_MODEL_PATH=/models/qwen2.5-1.5b-instruct-q4_k_m.gguf

# Verify discovery, then use it
amadeus config | grep model.path
amadeus git commit
```

## Environment Setup for CI / Scripts

```bash
# Headless, deterministic invocation (no editor, no LLM)
amadeus learn new "ci-note" --no-edit --body "generated in CI"
amadeus research "topic" --no-llm
amadeus sys status >/dev/null && echo "amadeus healthy"
```

## Docker Deployment

```bash
# Build (see docs/deployment.md for the Dockerfile)
docker build -t amadeus:0.1.0 .

# Run any command with host-persistent data
docker run --rm -v "$HOME/.amadeus:/root/.amadeus" amadeus:0.1.0 start
docker run --rm -v "$HOME/.amadeus:/root/.amadeus" amadeus:0.1.0 task list
```

## Scheduled (Unattended) Research

```cron
# crontab -e — weekday mornings, deterministic, logged
30 6 * * 1-5 /home/me/amadeus/.venv/bin/amadeus research "ai infra news" --no-llm \
  >> /home/me/.amadeus/logs/cron.log 2>&1
```

## Scripting with the Python API

```python
from amadeus.core.config import load_config
from amadeus.core import storage

cfg = load_config()
storage.add_task(cfg.tasks_path, "Created from a script")
for t in storage.load_tasks(cfg.tasks_path):
    print(t["id"], "✓" if t["done"] else "·", t["title"])
```

Generating text directly (when a model is available):

```python
from amadeus.core.config import load_config
from amadeus.utils.llm import llm_session, is_available

cfg = load_config()
if is_available(cfg):
    with llm_session(cfg) as llm:
        print(llm.chat([
            {"role": "system", "content": "Be terse. /no_think"},
            {"role": "user", "content": "One-line summary of BM25."},
        ]))
```

## Backup & Restore

```bash
# Back up everything
tar czf amadeus-$(date +%F).tar.gz -C "$HOME" .amadeus

# Restore
tar xzf amadeus-2026-06-26.tar.gz -C "$HOME"
```

## See Also

- [cli.md](cli.md) — every command and flag.
- [getting-started.md](getting-started.md) — the guided first run.
- [deployment.md](deployment.md) — Docker, cron, and CI details.
