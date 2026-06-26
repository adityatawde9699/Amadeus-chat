# Roadmap

This roadmap describes the direction of Amadeus. It is intentionally
conservative — every item must respect the project's core constraints:
**deterministic-first**, **low-RAM**, and **stateless/fire-and-forget**. Dates
are indicative, not commitments.

## Status Legend

| Symbol | Meaning |
| --- | --- |
| ✅ | Done |
| 🔜 | Planned (next) |
| 🧪 | Experimental / under consideration |
| ❌ | Explicitly out of scope |

## Released — v0.1.0 (2026-06-26)

- ✅ `amadeus` package + `argparse` CLI dispatcher.
- ✅ Daily dashboard, tasks, knowledge base (BM25L), git assistant, web
  research, system maintenance, config inspection.
- ✅ Lazy local LLM with model auto-discovery and reasoning-model support.
- ✅ 57-test suite; measured benchmarks; hardened data-changing operations.

## Near Term — v0.2.x

- 🔜 **Note tagging & metadata** — front-matter tags and `learn search --tag`.
- 🔜 **Structured logging** — `--verbose`/`--quiet` global flags and a log file
  under `~/.amadeus/logs/` for failure investigation.
- 🔜 **Config validation** — clear, actionable errors for malformed
  `config.toml` and out-of-range values.
- 🔜 **`amadeus bench`** — promote `scripts/benchmark.py` to a first-class
  subcommand.
- 🔜 **Shell completions** — bash/zsh/fish completion scripts.

## Mid Term — v0.3.x

- 🧪 **Pluggable LLM backends** — an OpenAI-compatible local server backend
  (e.g. `llama-server`, Ollama) selectable in config, alongside the in-process
  `llama-cpp-python` backend.
- 🧪 **Research caching** — skip re-fetching recently seen URLs.
- 🧪 **Note export** — render the knowledge base to a static HTML site.
- 🧪 **Task scheduling helpers** — first-class `cron` snippet generation for
  unattended `research`.

## Long Term — v1.0

- 🧪 **Optional encrypted storage** — at-rest encryption for the knowledge base.
- 🧪 **Cross-platform polish** — first-class macOS and Windows support for the
  system-maintenance module (currently Linux-centric).
- 🧪 **Plugin API** — a documented extension point for third-party subcommands.

## Explicitly Out of Scope

- ❌ **Persistent daemon / always-on model** — reintroduces the RAM footprint
  this project exists to eliminate. Use `cron` or `nohup` for unattended runs.
- ❌ **Embedding / vector database** — BM25L is deterministic and dependency-light;
  vector search would pull in PyTorch-class dependencies.
- ❌ **Cloud sync service** — Amadeus is local-first by design. Sync your
  `~/.amadeus/` directory with your own tooling (git, rsync, Syncthing).
- ❌ **Multi-user server mode** — there is no authentication surface and none is
  planned.

## Feedback

Have an idea? Open a [Discussion](https://github.com/adityatawde9699/Amadeus-chat/discussions)
or an [Issue](https://github.com/adityatawde9699/Amadeus-chat/issues). Proposals that
align with the design philosophy are prioritized.
