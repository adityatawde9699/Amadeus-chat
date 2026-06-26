# Frequently Asked Questions

A quick index of common questions. For deeper topics, follow the links into
[`docs/`](docs/).

## General

### What is Amadeus?
A local, deterministic-first CLI assistant for low-RAM laptops. It handles daily
dashboards, tasks, notes, git, research, and system maintenance, loading a local
LLM only for the two tasks that benefit from it. See the [README](README.md).

### Is it a chatbot?
No. Amadeus is **fire-and-forget**: each command runs once and exits. There is
no chat loop and no resident model.

### Which platforms are supported?
The deterministic features are cross-platform Python. The system-maintenance
module (`amadeus sys clean`) is Linux-centric (apt, journald). macOS and Windows
work for everything except the Linux-specific cleaners.

## Installation & Setup

### Do I need a GPU?
No. Amadeus targets CPU inference. A GPU is neither required nor used by default.

### Do I have to install the LLM?
No. The base install has zero ML dependencies. Install the optional extra
(`uv sync --extra llm`) only if you want generated commit messages and research
summaries. See [docs/installation.md](docs/installation.md).

### Why Python 3.12?
The project standardized on 3.12 to match its lockfile and CI baseline and to
use `tomllib` from the standard library. See [docs/development.md](docs/development.md).

### `pip install -e .` did nothing useful — why?
You are likely on a pre-0.1.0 checkout where the package layout was incomplete.
Update to 0.1.0+; the `amadeus` package and entry point now exist.

## Models & AI

### How does Amadeus find my model?
In this order: `[model].path` in `config.toml` → `$AMADEUS_MODEL_PATH` → the
first `*.gguf` in `~/.amadeus/models/`. See [docs/ai.md](docs/ai.md).

### Which models work?
Any GGUF model supported by `llama-cpp-python`. Small Q4_K_M instruct models
(1.5B–3B) are ideal for low-RAM machines. Reasoning models (Qwen3-class) are
supported — their `<think>` output is stripped automatically.

### My commit messages came out as a generic template. Why?
That is the deterministic fallback. It happens when no model is discoverable, or
when a reasoning model spent its entire token budget "thinking" without emitting
an answer. Amadeus mitigates the latter with `/no_think`, but you can also raise
`[model].max_tokens`. See [docs/troubleshooting.md](docs/troubleshooting.md).

### Does it call any external AI API?
No. All inference is local and offline.

## Data & Storage

### Where is my data stored?
Under `~/.amadeus/`: `config.toml`, `tasks.json`, `knowledge_base/*.md`,
`research/<slug>/`, `indexes/`, and `models/`. See [docs/database.md](docs/database.md).

### How do I back up or move my data?
Copy the directory: `cp -r ~/.amadeus ~/amadeus-backup`. Everything is plain
text and portable.

### Is my data encrypted?
Not at rest in 0.1.x. Use filesystem permissions (`chmod 700 ~/.amadeus`).
Optional encryption is on the [roadmap](ROADMAP.md).

## Usage

### How do I see everything at once?
`amadeus start` — the daily dashboard.

### Can I run research unattended?
Yes, with `cron` or `nohup`, e.g.
`nohup amadeus research "topic" --no-llm &`. A built-in daemon is intentionally
out of scope. See [ROADMAP.md](ROADMAP.md).

### How do I search my notes?
`amadeus learn search "<query>"` — deterministic BM25L ranking. See
[docs/cli.md](docs/cli.md).

## Privacy & Security

### Does Amadeus phone home?
No telemetry, no analytics, no auto-updates. The only outbound network traffic
is the web-research fetcher, and only when you run `amadeus research`.

### How do I report a security issue?
Privately, per [SECURITY.md](SECURITY.md). Do not open a public issue.

## Contributing

### How can I help?
Read [CONTRIBUTING.md](CONTRIBUTING.md). Bug fixes, deterministic features,
tests, and docs are all welcome.

### What is the commit style?
[Conventional Commits](https://www.conventionalcommits.org/). Amadeus can even
generate them for you with `amadeus git commit`.
