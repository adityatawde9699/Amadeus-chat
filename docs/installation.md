# Installation

This page covers installing Amadeus on Linux, macOS, and Windows, with and
without the optional local LLM.

## Requirements

| Component | Requirement | Notes |
| --- | --- | --- |
| Python | ≥ 3.12 | Uses stdlib `tomllib`; 3.12 is the supported baseline |
| Git | Any recent version | Required for the `git` subcommands |
| OS | Linux (primary), macOS, Windows | `sys clean` cleaners are Linux-only |
| RAM | 2 GB+ (4 GB+ for LLM) | Deterministic features need only tens of MB |
| Build tools | C/C++ toolchain | Only for the optional `llama-cpp-python` |
| Model | A GGUF file | Only for LLM features; see [ai.md](ai.md) |

## Dependency Overview

| Dependency | Extra | Purpose |
| --- | --- | --- |
| `psutil` | base | System metrics |
| `rich` | base | Terminal rendering |
| `rank-bm25` | base | BM25L note search |
| `requests` | base | Web research fetch |
| `beautifulsoup4` | base | HTML text extraction |
| `llama-cpp-python` | `llm` | Local GGUF inference |
| `pytest`, `pytest-cov` | `dev` | Test suite |

## Option A — Install with `uv` (recommended)

[`uv`](https://github.com/astral-sh/uv) installs from the committed `uv.lock`,
giving a reproducible environment.

```bash
git clone https://github.com/adityatawde9699/Amadeus-chat.git
cd Amadeus-chat

uv sync                          # base
uv sync --extra llm              # + local LLM
uv sync --extra dev              # + test tooling
uv sync --extra llm --extra dev  # everything
```

Run commands through `uv run`:

```bash
uv run amadeus --help
```

Or activate the environment:

```bash
source .venv/bin/activate
amadeus --help
```

## Option B — Install with `pip`

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .                   # base
pip install -e ".[llm]"            # + local LLM
pip install -e ".[dev]"            # + test tooling
```

`requirements.txt` is generated from `pyproject.toml` for environments that
prefer a flat requirements file:

```bash
pip install -r requirements.txt
```

## Installing the Optional LLM

`llama-cpp-python` compiles a native extension. If the wheel build fails, ensure
a C/C++ toolchain is present:

| Platform | Toolchain |
| --- | --- |
| Debian/Ubuntu | `sudo apt install build-essential` |
| Fedora | `sudo dnf groupinstall "Development Tools"` |
| macOS | `xcode-select --install` |
| Windows | Visual Studio Build Tools (C++ workload) |

Then:

```bash
uv sync --extra llm
# or
pip install -e ".[llm]"
```

See [troubleshooting.md](troubleshooting.md) for common build errors.

## Providing a Model

Download a small Q4_K_M GGUF and place it where Amadeus can discover it:

```bash
mkdir -p ~/.amadeus/models
huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
    qwen2.5-1.5b-instruct-q4_k_m.gguf \
    --local-dir ~/.amadeus/models/

amadeus config | grep model.path   # verify discovery
```

Discovery order and tuning: [configuration.md](configuration.md) and [ai.md](ai.md).

## Verify the Installation

```bash
amadeus --version
amadeus --help
amadeus config --path
uv run python -m compileall amadeus   # syntax check
uv run pytest -q                       # if dev extra installed
```

A successful run prints the version, the command list, the config path, and a
green test summary.

## Upgrading

```bash
cd Amadeus-chat
git pull
uv sync --extra llm --extra dev   # re-resolve against the updated lock
```

Your data in `~/.amadeus/` is untouched by upgrades.

## Uninstalling

```bash
# Remove the environment
rm -rf .venv

# Optionally remove your data (irreversible)
rm -rf ~/.amadeus
```

## Next Steps

- [getting-started.md](getting-started.md) — first commands.
- [configuration.md](configuration.md) — tune behaviour.
- [cli.md](cli.md) — full command reference.
