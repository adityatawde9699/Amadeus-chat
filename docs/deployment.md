# Deployment

> **Important:** Amadeus is a **local, single-user CLI**, not a network service.
> There is no server process, port, or API to expose. "Deployment" here means
> reproducible distribution and **unattended invocation** (e.g. scheduled
> research). Sections about reverse proxies, multi-node scaling, and cloud
> application platforms are included for completeness but are largely **not
> applicable** — this is noted explicitly where relevant.

## Deployment Modes

| Mode | Use case | Applicable? |
| --- | --- | --- |
| Local install | Daily interactive use | ✅ Primary |
| Docker | Reproducible/headless runs | ✅ Supported |
| Docker Compose | Mounting host data + scheduled runs | ✅ Optional |
| Cron / systemd timer | Unattended research | ✅ Recommended for automation |
| Reverse proxy (Nginx/Caddy) | — | ❌ No HTTP surface |
| Cloud app platforms (Vercel/Render/Fly.io) | — | ⚠️ Only as a batch/cron container |
| Horizontal scaling / load balancing | — | ❌ Not a service |

## Local Deployment

The canonical installation. See [installation.md](installation.md).

```bash
git clone https://github.com/adityatawde9699/Amadeus-chat.git
cd Amadeus-chat
uv sync --extra llm
uv run amadeus start
```

For day-to-day use, expose the command on your `PATH`:

```bash
# With uv, activate the venv:
source .venv/bin/activate
# Or install into a tool environment:
uv tool install .
amadeus --help
```

## Docker

Amadeus ships no Dockerfile by default; the following is a minimal, production-
quality image you can drop in at the repository root as `Dockerfile`.

```dockerfile
# Dockerfile
FROM python:3.12-slim AS base

# Build tools only needed if you install the llm extra.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Base install (no LLM). Add ".[llm]" to enable local inference.
RUN pip install --no-cache-dir -e .

# Data lives outside the image; mount it at runtime.
VOLUME ["/root/.amadeus"]

ENTRYPOINT ["amadeus"]
CMD ["--help"]
```

Build and run:

```bash
docker build -t amadeus:0.1.0 .

# Persist data on the host and run any subcommand:
docker run --rm -v "$HOME/.amadeus:/root/.amadeus" amadeus:0.1.0 start
docker run --rm -v "$HOME/.amadeus:/root/.amadeus" amadeus:0.1.0 task list
```

> The `~/.amadeus` volume keeps your tasks, notes, models, and config on the
> host so they survive container removal.

## Docker Compose

Useful for pinning a data volume and running scheduled batch commands.

```yaml
# docker-compose.yml
services:
  amadeus:
    build: .
    image: amadeus:0.1.0
    volumes:
      - amadeus-data:/root/.amadeus
    # Override per invocation, e.g.:
    #   docker compose run --rm amadeus research "topic" --no-llm
    command: ["start"]

volumes:
  amadeus-data:
```

```bash
docker compose build
docker compose run --rm amadeus sys status
```

## Unattended / Scheduled Runs

This is the recommended automation pattern. Amadeus has no built-in scheduler by
design (see [architecture.md](architecture.md#background-jobs--event-flow)).

### cron

```cron
# Run a deterministic research pass every weekday at 06:30 and log output.
30 6 * * 1-5  /home/me/amadeus/.venv/bin/amadeus research "ai infra news" --no-llm >> /home/me/.amadeus/logs/cron.log 2>&1
```

### systemd timer

```ini
# ~/.config/systemd/user/amadeus-research.service
[Unit]
Description=Amadeus scheduled research

[Service]
Type=oneshot
ExecStart=%h/amadeus/.venv/bin/amadeus research "ai infra news" --no-llm
```

```ini
# ~/.config/systemd/user/amadeus-research.timer
[Unit]
Description=Run Amadeus research on a schedule

[Timer]
OnCalendar=Mon..Fri 06:30
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user enable --now amadeus-research.timer
```

## Cloud Platforms

Amadeus is not a web app, so PaaS targets (Vercel, Render, Railway, Fly.io) only
make sense as **scheduled container jobs**. The general recipe:

1. Build the Docker image above.
2. Push it to the platform's registry.
3. Configure a **cron/scheduled job** (not a web service) that runs a single
   `amadeus <command>`.
4. Attach a persistent volume mounted at `/root/.amadeus` for state.

> If a platform requires an HTTP health check or a long-running process, Amadeus
> is the wrong fit — it is intentionally a one-shot command.

## Environment Configuration

| Variable | Purpose |
| --- | --- |
| `AMADEUS_MODEL_PATH` | Absolute path to a `.gguf` model inside the container |
| `EDITOR` | Editor for `learn new` (irrelevant in headless runs; use `--no-edit`) |

Mount models and data as volumes rather than baking them into images (a 1+ GB
model bloats the image and is non-portable).

## CI/CD

A minimal GitHub Actions workflow that lints (optional), tests, and builds:

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --extra dev
      - run: uv run python -m compileall amadeus
      - run: uv run pytest -q
      - run: uv build
```

The test suite is network-free and fast (~1 s), so CI requires no services.

## Backups

State is a single directory; back it up with any file tool:

```bash
tar czf amadeus-backup-$(date +%F).tar.gz -C "$HOME" .amadeus
```

Restore by extracting it back to `$HOME`. Because everything is plain text, you
can also keep `~/.amadeus/knowledge_base` and `tasks.json` in a private git repo.

## Monitoring & Logging

Amadeus prints to stdout/stderr. For unattended runs, redirect to a log file (see
the cron example) and inspect it. Structured logging is on the
[roadmap](../ROADMAP.md). See [monitoring.md](monitoring.md).

## Scaling

Not applicable in the traditional sense — there is no server to scale. To process
more work, schedule more independent invocations. CPU inference throughput scales
with `[model].n_threads`; see [performance.md](performance.md).
