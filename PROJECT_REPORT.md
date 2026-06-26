# Amadeus Project Report

**Assessment date:** 20 June 2026  
**Resolution date:** 26 June 2026  
**Repository:** `llama`  
**Project version declared in `pyproject.toml`:** `0.1.0`

> **Resolution (26 June 2026).** The recovery plan below has been executed on
> branch `feature/recovery-and-model-wiring`. All five critical findings are
> addressed: the `amadeus/` package and `amadeus/cli.py` dispatcher exist and
> run every documented command; dependencies are reconciled (`pyproject.toml`
> is the single source, `uv.lock`/`requirements.txt` regenerated, Python 3.12
> baseline); a 57-test pytest suite passes with no network access; the
> high-priority data-changing risks are hardened (atomic JSON writes, commit
> staging only after acceptance, note-overwrite guard, `sys clean --dry-run`);
> the local GGUF model is wired via auto-discovery and the LLM commit/research
> paths are verified (with `<think>` stripping for reasoning models); and the
> README figures are now **measured** (see its Benchmarks section) rather than
> estimated. The sections below are retained as the original assessment.
>
> **Current status:** runnable, tested, model-wired — alpha.

## Executive Summary

Amadeus is being redesigned from a persistent local-LLM chat application into a
deterministic-first, fire-and-forget command-line assistant. The proposed design
is appropriate for low-memory systems: ordinary operations use conventional
Python code, while the local LLM is loaded only for commit-message generation
and research summarization.

The new implementation contains substantial modules for configuration, storage,
tasks, notes, Git assistance, research, system monitoring, terminal rendering,
and lazy LLM access. The Python source compiles successfully.

However, the repository is currently in an incomplete refactor state and is not
usable through the documented `amadeus` command. The package configuration
expects an `amadeus` package and an `amadeus.cli` entry point, but neither
exists. The new source directories are also untracked, the former working
application has been deleted locally, there are no tests, and dependency
definitions disagree. The immediate priority is therefore to complete the
package structure and CLI dispatcher before adding features.

**Overall status:** promising architecture, incomplete integration  
**Current readiness:** pre-alpha / not releasable

## Project Purpose

The redesigned Amadeus aims to provide a local CLI assistant with five main
capabilities:

1. A daily dashboard combining machine status, tasks, and project Git status.
2. Plain-JSON task management.
3. Markdown note management with deterministic BM25L search.
4. Git status presentation and optional local-LLM commit-message generation.
5. Web research with deterministic extraction and optional local-LLM
   summarization.

The central design constraint is low RAM usage. Persistent chat history,
embedding models, vector databases, and a permanently loaded LLM have been
removed from the new design.

## Current Architecture

| Area | Current implementation | Responsibility |
|---|---|---|
| Configuration | `core/config.py` | Creates and loads `~/.amadeus/config.toml` |
| Storage | `core/storage.py` | Tasks, notes, research output, and index-cache I/O |
| Tasks | `modules/tasks.py` | Add, list, complete, and delete tasks |
| Notes | `modules/notes.py` | Markdown notes and BM25L search |
| Git | `modules/git_assist.py` | Status display and commit creation |
| Research | `modules/research.py` | DuckDuckGo search, page extraction, reports |
| System | `modules/sysadmin.py` | Resource status and allow-listed cleanup |
| Startup | `modules/startup.py` | Combined daily dashboard |
| LLM | `utils/llm.py` | Lazy `llama-cpp-python` lifecycle |
| Display | `utils/display.py` | Shared Rich terminal output |

The new implementation contains approximately 2,000 lines of Python across
these modules. Persistence is local and human-readable:

- `~/.amadeus/tasks.json`
- `~/.amadeus/knowledge_base/*.md`
- `~/.amadeus/research/<topic>/report.md`
- `~/.amadeus/research/<topic>/sources.json`
- `~/.amadeus/indexes/notes.json`

## Strengths

### Clear resource-management strategy

`utils/llm.py` imports `llama_cpp` only when needed and exposes a context
manager that releases references and runs garbage collection after inference.
The deterministic fallback behavior means most features do not need an LLM.

### Simple, portable persistence

The project uses JSON and Markdown rather than a database. This keeps backups,
inspection, and manual recovery straightforward.

### Separation of concerns

The former monolithic application is being split into focused modules. Display,
storage, configuration, and LLM access are centralized rather than duplicated.

### Safety considerations

System cleanup accepts only recognized target categories. Git commits require
confirmation by default. Network requests have configurable timeouts, and the
research pipeline can operate without the LLM.

### Deterministic local search

BM25L note search is lightweight and avoids the memory cost of
`sentence-transformers` and PyTorch. The MD5 cache avoids re-tokenizing
unchanged notes.

## Critical Findings

### 1. The package and CLI entry point do not exist

`pyproject.toml` declares:

```toml
[project.scripts]
amadeus = "amadeus.cli:main"
```

It also configures package discovery with `include = ["amadeus*"]`. The source
tree has top-level `core`, `modules`, and `utils` directories, but no
`amadeus/` directory and no `cli.py`.

Validation found that package discovery returns no packages. Importing
`modules.tasks` fails with:

```text
ImportError: attempted relative import beyond top-level package
```

Consequently, `pip install -e .` cannot produce the documented working CLI.

### 2. The refactor is not committed as a coherent state

Git currently reports:

- Modified: `README.md`, `pyproject.toml`
- Deleted: `chat.py`, `download_model.py`
- Untracked: `core/`, `modules/`, `utils/`

The last committed revision still represents the older chat application.
Losing or partially staging the working tree would lose the new implementation
or produce a broken revision.

### 3. No automated tests are present

`pyproject.toml` points pytest at `tests/`, but no test directory exists and
pytest is not installed in the active environment. Syntax compilation passes,
but no functional behavior is verified.

High-value untested areas include:

- Configuration creation and malformed TOML handling
- Task ID and corrupted JSON behavior
- Note-cache invalidation and BM25 ranking
- Git porcelain parsing and commit fallback messages
- HTML extraction and DuckDuckGo result parsing
- Cleanup allow-list enforcement
- LLM load/unload and fallback paths

### 4. Dependency specifications are inconsistent

`pyproject.toml` describes the redesigned application, while
`requirements.txt` still describes the old LLM/RAG application. The latter
includes heavy packages such as `sentence-transformers`, `numpy`, and `pypdf`,
but omits new required packages including `psutil`, `requests`, and
`beautifulsoup4`.

The existing `uv.lock` is also stale: it still identifies the project as
`llama`, requires Python 3.12, and resolves the old dependency set. The new
`pyproject.toml` allows Python 3.11, while `.python-version` specifies 3.12.

In the active virtual environment, `requests` and `bs4` are missing, so the
research module cannot run.

### 5. Documentation reports completion prematurely

The README marks all four implementation phases complete and documents a broad
command set. Since the dispatcher and package are absent, none of those
commands are currently available through the advertised interface.

Performance statements such as the idle RAM baseline and model-load duration
are design targets or observations that have not been backed by benchmarks in
this repository.

## Additional Technical Risks

| Priority | Risk | Impact |
|---|---|---|
| High | `git commit` can run `git add -A` before user confirmation | Aborting leaves all changes staged |
| High | Task and index JSON writes are not atomic | Interrupted writes can corrupt local state |
| Medium | Research depends on DuckDuckGo HTML selectors | Search can break when external markup changes |
| Medium | Research reports store full extracted source text in JSON | Storage growth and copied-content concerns |
| Medium | Note creation overwrites an existing slug without warning | Accidental note loss |
| Medium | `learn show` uses the first prefix match | Ambiguous slugs can display the wrong note |
| Medium | Cleanup invokes privileged system tools without a dry-run | Behavior depends on host permissions |
| Low | Several imports are unused | Minor maintenance noise |
| Low | No logging or diagnostic mode is exposed by the CLI design | Harder failure investigation |

## Recommended Recovery Plan

### Phase 1: Restore a runnable package

1. Create `amadeus/` and move `core/`, `modules/`, and `utils/` under it.
2. Add `amadeus/cli.py` with the documented argparse command tree.
3. Add `amadeus/__init__.py` and expose a version.
4. Verify `python -m amadeus.cli --help` and the installed `amadeus --help`.
5. Commit the refactor as one coherent change.

### Phase 2: Establish reproducible installation

1. Treat `pyproject.toml` as the single dependency source.
2. Remove or regenerate `requirements.txt`.
3. Regenerate `uv.lock` from the new metadata.
4. Decide whether Python 3.11 or 3.12 is the supported baseline and align
   `.python-version`, metadata, CI, and documentation.
5. Test both base installation and the optional `llm` extra.

### Phase 3: Add minimum release tests

Add unit tests for configuration, storage, notes, Git parsing, research HTML
parsing, and cleanup classification. Add CLI smoke tests covering every
documented subcommand. Network and Git subprocess behavior should be mocked in
unit tests.

Recommended release gates:

```text
python -m compileall amadeus
pytest
python -m amadeus.cli --help
amadeus config --path
```

### Phase 4: Harden data-changing behavior

1. Write JSON through temporary files followed by atomic replacement.
2. Refuse to overwrite an existing note unless explicitly requested.
3. Separate commit-message generation from staging, or restore the previous
   staging state when the user aborts.
4. Add `--dry-run` to system cleanup.
5. Validate configuration values and report malformed config files clearly.

### Phase 5: Benchmark and release

Measure startup time, peak RAM, LLM load time, command duration, and note-search
performance on the target low-memory hardware. Replace README estimates with
measured results, then publish an initial pre-release.

## Suggested Milestones

| Milestone | Exit criterion |
|---|---|
| M1: Runnable CLI | All documented commands parse and base commands launch |
| M2: Reproducible build | Clean environment installs from lock file |
| M3: Tested core | Storage and deterministic modules have meaningful coverage |
| M4: Optional LLM verified | Missing-model and working-model paths both pass |
| M5: Pre-release | Documentation matches tested behavior and benchmarks |

## Conclusion

The redesign has a sound direction: it reduces memory pressure, simplifies
persistence, and narrows LLM use to tasks where generative output adds value.
Most feature modules already exist and are syntactically valid.

The project should not yet be treated as complete. Its next engineering goal is
integration rather than new functionality: establish the package, implement
the CLI entry point, reconcile dependencies, add tests, and make the current
working tree reproducible. Once those items are complete, the project will have
a credible foundation for a useful low-resource local assistant.
