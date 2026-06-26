# Architecture

This document explains how Amadeus is structured, how a command flows through
the system, and how the optional AI pipeline works.

## System Overview

Amadeus is a **stateless CLI dispatcher**. There is no daemon, server, database
engine, or message queue. Every invocation:

1. Parses arguments (`argparse`).
2. Loads configuration once (`core.config`).
3. Dispatches to exactly one feature module.
4. Reads/writes plain files (`core.storage`) and renders output (`utils.display`).
5. Optionally loads a local LLM for a single step (`utils.llm`), then unloads it.
6. Exits, returning memory to the OS.

```mermaid
flowchart TD
    subgraph Shell
      U([User]) -->|amadeus task add "x"| E[entry point<br/>amadeus = cli:main]
    end
    E --> P[argparse parser]
    P --> L[load_config]
    P --> D{dispatch by subcommand}
    D --> M1[modules.startup]
    D --> M2[modules.tasks]
    D --> M3[modules.notes]
    D --> M4[modules.git_assist]
    D --> M5[modules.research]
    D --> M6[modules.sysadmin]
    D --> M7[cli.cmd_config]
    M1 & M2 & M3 & M4 & M5 & M6 & M7 --> S[core.storage]
    M1 & M2 & M3 & M4 & M5 & M6 & M7 --> V[utils.display]
    M4 & M5 -. on demand .-> A[utils.llm.llm_session]
    A -. mmap load/unload .-> G[(local .gguf)]
    S --> FS[(~/.amadeus files)]
```

## High-Level Architecture

The codebase is organized into three layers with a strict dependency direction:
modules depend on core and utils, never the reverse.

```mermaid
flowchart LR
    subgraph Presentation
      CLI[cli.py<br/>argparse dispatcher]
    end
    subgraph Features["Feature modules (one per command group)"]
      startup
      tasks
      notes
      git_assist
      research
      sysadmin
    end
    subgraph Shared
      config[core.config]
      storage[core.storage]
      display[utils.display]
      llm[utils.llm]
    end
    CLI --> Features
    Features --> config
    Features --> storage
    Features --> display
    git_assist --> llm
    research --> llm
    llm --> config
```

This is a lightweight take on **Clean Architecture**: the feature modules are use
cases, `core` holds entities and persistence, and `utils` provides infrastructure
adapters (terminal I/O, model runtime). Dependencies point inward toward `core`.

## Folder Responsibilities

| Path | Responsibility |
| --- | --- |
| `amadeus/cli.py` | Build the argument parser, load config, dispatch, map exit codes |
| `amadeus/core/config.py` | Load/validate `config.toml`; model auto-discovery; typed `Config` dataclasses |
| `amadeus/core/storage.py` | All file I/O: tasks JSON, Markdown notes, research output, index cache, atomic writes, `slugify` |
| `amadeus/modules/startup.py` | `amadeus start` — compose the daily dashboard |
| `amadeus/modules/tasks.py` | `amadeus task …` — task CRUD |
| `amadeus/modules/notes.py` | `amadeus learn …` — note CRUD + BM25L search + index cache |
| `amadeus/modules/git_assist.py` | `amadeus git …` — porcelain parsing, commit message generation |
| `amadeus/modules/research.py` | `amadeus research …` — search, fetch, extract, summarize |
| `amadeus/modules/sysadmin.py` | `amadeus sys …` — metrics + allow-listed cleanup |
| `amadeus/utils/llm.py` | Lazy LLM lifecycle (`llm_session`), `strip_think`, availability checks |
| `amadeus/utils/display.py` | Rich console: tables, panels, prompts, colour rules |

```mermaid
flowchart TD
    root["amadeus/"] --> cli["cli.py"]
    root --> core["core/"]
    root --> modules["modules/"]
    root --> utils["utils/"]
    core --> cfg["config.py"]
    core --> sto["storage.py"]
    modules --> st["startup.py"]
    modules --> tk["tasks.py"]
    modules --> nt["notes.py"]
    modules --> gi["git_assist.py"]
    modules --> rs["research.py"]
    modules --> sa["sysadmin.py"]
    utils --> ll["llm.py"]
    utils --> dp["display.py"]
```

## Component Relationships

A representative command, `amadeus task add`, exercises the common path:

```mermaid
sequenceDiagram
    actor User
    participant CLI as cli.main
    participant Cfg as core.config
    participant Mod as modules.tasks
    participant Sto as core.storage
    participant Dsp as utils.display
    User->>CLI: amadeus task add "Write docs"
    CLI->>Cfg: load_config()
    Cfg-->>CLI: Config
    CLI->>Mod: cmd_add(cfg, args)
    Mod->>Sto: add_task(tasks_path, title)
    Sto->>Sto: atomic _write_json()
    Sto-->>Mod: task dict
    Mod->>Dsp: ok("Task #1 added")
    Dsp-->>User: rendered output
    Mod-->>CLI: exit code 0
```

## Request (Command) Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Parse: argv
    Parse --> Help: no subcommand
    Help --> [*]: exit 2
    Parse --> LoadConfig: subcommand found
    LoadConfig --> Override: apply --default-type etc.
    Override --> Dispatch: call cmd_*(cfg, args)
    Dispatch --> Work: read/write files, render
    Work --> LLM: only git commit / research
    LLM --> Work: model unloaded
    Work --> [*]: return exit code
    Dispatch --> Interrupt: Ctrl-C
    Interrupt --> [*]: exit 130
```

Exit codes follow a simple convention:

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Operation failed (e.g. not a git repo, no results) |
| `2` | Usage error / missing required argument |
| `130` | Interrupted (Ctrl-C) |

## Authentication Flow

Amadeus is a **single-user local tool** with no authentication subsystem. The
trust boundary is the operating-system user account; authorization is delegated
to filesystem permissions and the privileges of the invoking shell.

```mermaid
flowchart LR
    U([OS user session]) -->|owns| Files[(~/.amadeus/*)]
    U -->|invokes with its privileges| A[amadeus]
    A -->|reads/writes| Files
    A -->|sudo-context only| Priv[privileged cleaners<br/>apt / journald]
```

See [authentication.md](authentication.md) for the full trust model.

## Data Flow

Persistence is plain files. No ORM, no migrations.

```mermaid
flowchart LR
    subgraph Inputs
      cmd[CLI args]
      web[(Web pages)]
    end
    subgraph Amadeus
      tasks[tasks module] --> tj[(tasks.json)]
      notes[notes module] --> kb[(knowledge_base/*.md)]
      notes --> idx[(indexes/notes.json)]
      research[research module] --> rep[(research/&lt;slug&gt;/report.md)]
      research --> src[(research/&lt;slug&gt;/sources.json)]
    end
    cmd --> tasks
    cmd --> notes
    web --> research
```

Details and schemas: [database.md](database.md).

## AI Pipeline

The LLM is loaded only inside `utils.llm.llm_session()` and released on context
exit. Two commands use it; both fall back to deterministic output if a model is
unavailable.

```mermaid
flowchart TD
    Start([git commit / research]) --> Avail{is_available?}
    Avail -- no --> Fallback[deterministic template]
    Avail -- yes --> Open[llm_session: load .gguf]
    Open --> Build[build chat messages<br/>system + user]
    Build --> Chat[llm.chat → chat template]
    Chat --> Strip[strip_think: remove &lt;think&gt;…&lt;/think&gt;]
    Strip --> Empty{empty after strip?}
    Empty -- yes --> Fallback
    Empty -- no --> Use[use generated text]
    Open --> Close[context exit: del + gc.collect]
    Use --> Close
    Fallback --> Done([render result])
    Use --> Done
    Close --> Done
```

The full pipeline, prompts, and reasoning-model handling are in [ai.md](ai.md).

## Background Jobs & Event Flow

Amadeus has **no built-in background jobs, scheduler, or event bus** — this is a
deliberate design decision to keep the idle footprint at zero. Unattended work is
delegated to the operating system:

```mermaid
flowchart LR
    cron["cron / systemd timer"] -->|scheduled| A1["amadeus research 'topic' --no-llm"]
    nohup["nohup / &"] -->|detached| A2["amadeus research 'topic'"]
    A1 --> out[(research/&lt;slug&gt;/)]
    A2 --> out
```

There is no message queue, no pub/sub, and no inter-process communication. Each
scheduled invocation is fully independent.

## Caching Strategy

Two distinct "caches" exist, with different lifetimes:

| Cache | Location | Lifetime | Invalidation |
| --- | --- | --- | --- |
| BM25 index | `~/.amadeus/indexes/notes.json` | Persistent | Per-file MD5 change |
| LLM weights | Process RSS (mmap) | One `llm_session` | Released on context exit |

See [caching.md](caching.md).

## Database Design

There is no database server. The "database" is a directory of human-readable
files. The conceptual entity relationships:

```mermaid
erDiagram
    CONFIG ||--|| HOME : "configures"
    HOME ||--o{ TASK : "stores"
    HOME ||--o{ NOTE : "stores"
    HOME ||--o{ RESEARCH : "stores"
    HOME ||--|| INDEX : "caches"
    NOTE ||--|| INDEX : "tokenized into"
    RESEARCH ||--o{ SOURCE : "cites"
    TASK {
      int id
      string title
      bool done
      string created_at
      string completed_at
    }
    NOTE {
      string slug
      string title
      string first_para
      string mtime
    }
    RESEARCH {
      string slug
      string report_md
    }
    SOURCE {
      string url
      string title
      string text
    }
```

Full schemas and file formats: [database.md](database.md).

## Deployment Architecture

Because Amadeus is a local CLI, "deployment" means reproducible distribution and
unattended invocation, not a running service.

```mermaid
flowchart TD
    subgraph Developer Machine
      repo[git clone] --> env[uv sync]
      env --> bin[amadeus CLI]
    end
    subgraph Container
      img[Docker image] --> run[docker run amadeus ...]
    end
    subgraph Scheduled
      timer[cron / systemd] --> bin
    end
    bin --> data[(host ~/.amadeus volume)]
    run --> data
```

See [deployment.md](deployment.md).

## Design Principles Recap

- **Deterministic-first** — the LLM is optional and short-lived.
- **Stateless** — no daemon; the OS reclaims memory on exit.
- **Plain files** — portable, greppable, backup-friendly storage.
- **Separation of concerns** — modules are use cases; `core`/`utils` are shared.
- **Fail safe** — atomic writes, allow-lists, confirmations, dry-runs.
