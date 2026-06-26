"""
Daily startup dashboard — `amadeus start`.

Aggregates system status, today's tasks, and per-project git summaries
into one panel.  No LLM required.

The dashboard is split into three sections so it can be scanned at a glance:
1. System snapshot (RAM / Disk / CPU)
2. Today's open tasks
3. Per-project git status (one-line summary per project)
"""
from __future__ import annotations

import subprocess  # used by cmd_start below
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.config import Config
from ..core import storage
from ..utils import display
from . import sysadmin


def _greeting() -> str:
    h = datetime.now().hour
    if h < 5:
        return "Burning the midnight oil"
    if h < 12:
        return "Good morning"
    if h < 18:
        return "Good afternoon"
    return "Good evening"


def _project_git_summary(path: Path) -> tuple[str, str]:
    """Return (status_line, branch) for a git project.

    status_line examples:
        "clean"                       — nothing to commit
        "3 modified, 1 untracked"     — dirty
        "not a git repo"              — skip
    """
    import subprocess
    try:
        # Use git itself to detect repo (handles worktrees & nested dirs)
        repo_check = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5,
        )
        if repo_check.returncode != 0:
            return "not a git repo", "-"
        branch = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or "-"
        status = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return "git error", branch if 'branch' in dir() else "-"

    if not status:
        return "clean", branch

    modified = sum(1 for l in status.splitlines() if l.startswith((" M", "M ", "MM", "A ", "D ", "R ")))
    untracked = sum(1 for l in status.splitlines() if l.startswith("??"))
    parts = []
    if modified:
        parts.append(f"{modified} modified")
    if untracked:
        parts.append(f"{untracked} untracked")
    return ", ".join(parts) or "dirty", branch


def cmd_start(cfg: Config, args: Any) -> int:
    # Banner
    display.console.print()
    display.console.print(
        f"[bold cyan]Amadeus[/bold cyan]  ·  "
        f"{_greeting()}, {cfg.user_name}.  ·  "
        f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M')}[/dim]"
    )

    # ── Section 1: System snapshot ─────────────────────────────────
    display.header("System Snapshot")
    ram_line, ram_style = sysadmin._ram_status(cfg)
    disk_line, disk_style = sysadmin._disk_status(cfg)
    cpu_line = sysadmin._cpu_status()
    table = display.make_table([("Resource", "bold"), ("Status", "")])
    table.add_row("CPU", cpu_line)
    table.add_row("RAM", f"[{ram_style}]{ram_line}[/{ram_style}]")
    table.add_row("Disk /", f"[{disk_style}]{disk_line}[/{disk_style}]")
    display.console.print(table)

    # ── Section 2: Today's tasks ───────────────────────────────────
    display.header("Today's Tasks")
    tasks = storage.load_tasks(cfg.tasks_path)
    open_tasks = [t for t in tasks if not t["done"]]
    done_tasks = [t for t in tasks if t["done"]]
    if open_tasks:
        display.render_tasks(open_tasks)
    else:
        display.info("Nothing open. Add one with: amadeus task add \"<title>\"")
    if done_tasks:
        display.dim(f"{len(done_tasks)} completed task(s) hidden.  "
                    f"View with: amadeus task list --all")

    # ── Section 3: Per-project git status ──────────────────────────
    if cfg.project_paths:
        display.header("Project Git Status")
        rows: list[tuple[str, str, str]] = []
        for raw_path in cfg.project_paths:
            p = Path(raw_path).expanduser()
            if not p.exists():
                rows.append((raw_path, "-", "[red]missing[/red]"))
                continue
            summary, branch = _project_git_summary(p)
            style = "green" if summary == "clean" else "yellow"
            rows.append((p.name, branch, f"[{style}]{summary}[/{style}]"))

        t = display.make_table([("Project", "bold"), ("Branch", "cyan"), ("Status", "")])
        for name, branch, status in rows:
            t.add_row(name, branch, status)
        display.console.print(t)

    display.footer("amadeus start  ·  next: amadeus task add | amadeus git status | amadeus sys status")
    return 0


__all__ = ["cmd_start"]
