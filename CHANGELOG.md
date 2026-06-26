# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation set under `docs/` and root governance files
  (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `ROADMAP.md`,
  `FAQ.md`, this changelog).

## [0.1.0] - 2026-06-26

First coherent, runnable release of the redesigned Amadeus CLI. This release
completes the refactor from a persistent-LLM chat REPL into a
deterministic-first, fire-and-forget command-line assistant.

### Added
- **Package & CLI** — `amadeus` package with an `argparse` dispatcher
  (`amadeus/cli.py`) exposing `start`, `task`, `git`, `learn`, `research`,
  `sys`, and `config` commands. Installable entry point `amadeus`.
- **Daily dashboard** (`amadeus start`) — system snapshot, open tasks, and
  per-project git status.
- **Task management** (`amadeus task add|list|done|delete`) — plain-JSON tasks.
- **Knowledge base** (`amadeus learn new|list|search|show`) — Markdown notes
  with deterministic BM25L search and an MD5-invalidated index cache.
- **Git assistant** (`amadeus git status|commit`) — porcelain parsing and
  Conventional Commit message generation (LLM or deterministic fallback).
- **Web research** (`amadeus research`) — DuckDuckGo HTML scraping, text
  extraction, optional LLM summarization, `report.md` + `sources.json` output.
- **System maintenance** (`amadeus sys status|clean`) — resource metrics and an
  allow-listed cleanup with `--dry-run`.
- **Local LLM** — lazy `llm_session()` lifecycle, model auto-discovery
  (config → `$AMADEUS_MODEL_PATH` → `~/.amadeus/models/*.gguf`), reasoning-model
  `<think>` stripping, and `/no_think` for commit generation.
- **Test suite** — 57 pytest cases (storage, config, notes/BM25, git, research,
  sysadmin, LLM helpers, CLI), network-free and isolated to a temporary home.
- **Benchmark script** — `scripts/benchmark.py` producing measured figures.

### Changed
- Standardized on Python 3.12 across `pyproject.toml`, `.python-version`, and
  `uv.lock`.
- Reconciled dependencies: `pyproject.toml` is the single source of truth;
  `uv.lock` and `requirements.txt` regenerated; removed the legacy RAG stack
  (`sentence-transformers`, `numpy`, `pypdf`).

### Security / Hardening
- Atomic JSON writes (temp file + `os.replace`) for `tasks.json` and indexes.
- `git commit` now stages changes **only after** the user accepts the proposed
  message, leaving the index untouched on abort.
- `learn new` refuses to overwrite an existing note without `--force`;
  `learn show` prefers an exact slug and warns on ambiguous prefixes.
- `sys clean --dry-run` reports what would be freed without deleting.

### Removed
- Legacy chat application files (`chat.py`, `download_model.py`) and the stale
  `.env.example` from the old Hugging Face download flow.

[Unreleased]: https://github.com/adityatawde9699/Amadeus-chat/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/adityatawde9699/Amadeus-chat/releases/tag/v0.1.0
