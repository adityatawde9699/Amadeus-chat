# Amadeus Documentation

The complete documentation set for **Amadeus** — a deterministic-first,
fire-and-forget CLI assistant for low-RAM machines. Start with the project
[README](../README.md) for an overview, then dive into the topic you need.

## Start Here

| Guide | What it covers |
| --- | --- |
| [Getting Started](getting-started.md) | Install and run your first commands |
| [Installation](installation.md) | Detailed install (uv/pip), platforms, the optional LLM |
| [Configuration](configuration.md) | Every `config.toml` option and env var |
| [CLI Reference](cli.md) | Every command and flag |
| [Examples](examples.md) | Copy-pasteable workflows |

## Concepts & Internals

| Guide | What it covers |
| --- | --- |
| [Architecture](architecture.md) | System design, lifecycle, and diagrams |
| [AI & the Local LLM](ai.md) | Model discovery, lifecycle, prompts, reasoning models |
| [Data Storage](database.md) | On-disk formats under `~/.amadeus/` |
| [Caching](caching.md) | BM25 index cache and model lifetime |
| [Authentication](authentication.md) | The single-user trust model |

## Operations

| Guide | What it covers |
| --- | --- |
| [Development](development.md) | Local setup, workflow, standards, release |
| [Testing](testing.md) | Test suite, fixtures, mocking, coverage |
| [Deployment](deployment.md) | Docker, cron/systemd, CI/CD, backups |
| [Monitoring](monitoring.md) | System reporting, logs, exit codes |
| [Performance](performance.md) | Measured benchmarks and tuning |
| [Security](security.md) | Threat model and safeguards |
| [Troubleshooting](troubleshooting.md) | Symptoms, causes, fixes |

## Reference

| Guide | What it covers |
| --- | --- |
| [API Reference](api.md) | CLI surface + internal Python API |
| [Glossary](glossary.md) | Definitions of key terms |

## Project Governance

- [Contributing](../CONTRIBUTING.md)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
- [Security Policy](../SECURITY.md)
- [Roadmap](../ROADMAP.md)
- [Changelog](../CHANGELOG.md)
- [FAQ](../FAQ.md)
- [License](../LICENSE)

## Diagram Conventions

Architecture and workflow diagrams use [Mermaid](https://mermaid.js.org/), which
GitHub renders natively in Markdown. If a diagram does not render, view the page
on GitHub or in a Mermaid-aware Markdown viewer.
