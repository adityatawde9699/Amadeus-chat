"""
System administration module — `amadeus sys status` and `amadeus sys clean`.

Deterministic, no LLM required.  Uses ``psutil`` for stats and standard Unix
tools for cleanup.

Safety rules for ``sys clean``:
* Only paths listed in ``config.sys.clean_targets`` are touched.
* Each target must match one of a small allow-list of *categories* (apt cache,
  apt lists, journal older-than-X, /tmp/amadeus) — see ``_classify_target``.
* Anything not on the allow-list is skipped with a yellow warning, even if
  the user added it to config.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from ..core.config import Config
from ..utils import display


# ── status ─────────────────────────────────────────────────────────────

def _bytes_human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _ram_status(cfg: Config) -> tuple[str, str]:
    vm = psutil.virtual_memory()
    free_mb = vm.available / (1024 * 1024)
    used_pct = vm.percent
    style = "green"
    if free_mb < cfg.sys.ram_warn_mb:
        style = "yellow"
    line = f"Used {used_pct:.1f}%  ·  Available {_bytes_human(vm.available)}  ·  Total {_bytes_human(vm.total)}"
    return line, style


def _disk_status(cfg: Config, path: str = "/") -> tuple[str, str]:
    try:
        du = psutil.disk_usage(path)
    except OSError:
        return f"unable to stat {path}", "red"
    free_gb = du.free / (1024 ** 3)
    style = "green"
    if free_gb < cfg.sys.disk_warn_gb:
        style = "yellow"
    line = f"Used {du.percent:.1f}%  ·  Free {_bytes_human(du.free)}  ·  Total {_bytes_human(du.total)}"
    return line, style


def _cpu_status() -> str:
    load1, load5, load15 = os.getloadavg()
    cores = os.cpu_count() or 1
    return f"Load {load1:.2f}/{load5:.2f}/{load15:.2f}  ·  Cores {cores}  ·  CPU {psutil.cpu_percent(interval=0.3):.1f}%"


def _top_processes(n: int = 5) -> list[tuple[str, str, float]]:
    procs = []
    for p in psutil.process_iter(["name", "memory_percent"]):
        try:
            info = p.info
            procs.append((info["name"] or "?", str(p.pid), info["memory_percent"] or 0.0))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x[2], reverse=True)
    return procs[:n]


def cmd_status(cfg: Config, args: Any) -> int:
    display.header("System Status", datetime.now().strftime("%Y-%m-%d %H:%M"))

    ram_line, ram_style = _ram_status(cfg)
    disk_line, disk_style = _disk_status(cfg)
    cpu_line = _cpu_status()

    table = display.make_table([("Resource", "bold"), ("Status", "")], title=None)
    table.add_row("[bold]CPU[/bold]", cpu_line)
    table.add_row("[bold]RAM[/bold]", f"[{ram_style}]{ram_line}[/{ram_style}]")
    table.add_row("[bold]Disk /[/bold]", f"[{disk_style}]{disk_line}[/{disk_style}]")
    display.console.print(table)

    # Battery (laptop-friendly)
    bat = _battery_status()
    if bat:
        display.console.print()
        display.dim(f"Battery: {bat}")

    # Top processes by RAM — useful on a 4GB box
    display.console.print()
    top = _top_processes(5)
    if top:
        t = display.make_table([("PID", "dim"), ("Process", ""), ("RAM %", "green")],
                               title="Top processes by RAM")
        for name, pid, pct in top:
            t.add_row(pid, name, f"{pct:.2f}")
        display.console.print(t)

    display.footer("amadeus sys status")
    return 0


def _battery_status() -> str | None:
    try:
        bat = psutil.sensors_battery()
    except (OSError, AttributeError):
        return None
    if bat is None:
        return None
    plug = "plugged" if bat.power_plugged else "on battery"
    return f"{bat.percent:.0f}% ({plug})"


# ── clean ──────────────────────────────────────────────────────────────

# Categories we know how to clean safely.  Anything else in config.sys.clean_targets
# is reported but skipped.
_APT_ARCHIVE_RE = "/var/cache/apt/archives"
_APT_LISTS_RE = "/var/lib/apt/lists"
_TMP_AMADEUS_RE = "/tmp/amadeus"
_JOURNAL_RE = "/var/log/journal"


def _classify_target(path: str) -> str:
    """Return a category label for the given clean target, or 'unknown'."""
    p = path.rstrip("/")
    if p == _APT_ARCHIVE_RE:
        return "apt-archives"
    if p == _APT_LISTS_RE:
        return "apt-lists"
    if p == _TMP_AMADEUS_RE:
        return "tmp-amadeus"
    if p == _JOURNAL_RE:
        return "journal"
    return "unknown"


def _clean_apt_archives(dry_run: bool = False) -> tuple[int, int]:
    """Run `apt-get clean`.  Returns (bytes_freed_approx, files_removed).

    In ``dry_run`` mode nothing is deleted; the current cache size is reported
    as the amount that *would* be freed.
    """
    if shutil.which("apt-get") is None:
        return 0, 0
    if dry_run:
        return _dir_size(Path(_APT_ARCHIVE_RE)), 0
    try:
        before = _dir_size(Path(_APT_ARCHIVE_RE))
        subprocess.run(["apt-get", "clean"], check=False, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        after = _dir_size(Path(_APT_ARCHIVE_RE))
        return max(0, before - after), 0
    except (OSError, subprocess.SubprocessError):
        return 0, 0


def _clean_apt_lists(dry_run: bool = False) -> tuple[int, int]:
    if not os.path.isdir(_APT_LISTS_RE):
        return 0, 0
    before = _dir_size(Path(_APT_LISTS_RE))
    if dry_run:
        files = [e for e in Path(_APT_LISTS_RE).glob("*") if e.is_file()]
        return before, len(files)
    n = 0
    for entry in Path(_APT_LISTS_RE).glob("*"):
        try:
            if entry.is_file():
                entry.unlink()
                n += 1
        except OSError:
            continue
    after = _dir_size(Path(_APT_LISTS_RE))
    return max(0, before - after), n


def _clean_tmp_amadeus(dry_run: bool = False) -> tuple[int, int]:
    p = Path(_TMP_AMADEUS_RE)
    if not p.exists():
        return 0, 0
    before = _dir_size(p)
    if dry_run:
        return before, sum(1 for _ in p.iterdir())
    n = 0
    try:
        for child in p.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                n += 1
            except OSError:
                continue
    except OSError:
        pass
    after = _dir_size(p)
    return max(0, before - after), n


def _clean_journal(dry_run: bool = False) -> tuple[int, int]:
    if shutil.which("journalctl") is None:
        return 0, 0
    if dry_run:
        return _dir_size(Path(_JOURNAL_RE)), 0
    try:
        before = _dir_size(Path(_JOURNAL_RE))
        subprocess.run(["journalctl", "--vacuum-time=3d"], check=False, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        after = _dir_size(Path(_JOURNAL_RE))
        return max(0, before - after), 0
    except (OSError, subprocess.SubprocessError):
        return 0, 0


_CLEANERS = {
    "apt-archives": _clean_apt_archives,
    "apt-lists":    _clean_apt_lists,
    "tmp-amadeus":  _clean_tmp_amadeus,
    "journal":      _clean_journal,
}


def _dir_size(p: Path) -> int:
    if not p.exists():
        return 0
    total = 0
    if p.is_file():
        return p.stat().st_size
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                continue
    return total


def cmd_clean(cfg: Config, args: Any) -> int:
    dry_run = bool(getattr(args, "dry_run", False))
    display.header("System Cleanup", "dry-run (nothing will be deleted)" if dry_run else None)

    if not cfg.sys.clean_targets:
        display.warn("No clean targets configured.")
        return 0

    total_freed = 0
    total_files = 0

    for target in cfg.sys.clean_targets:
        category = _classify_target(target)
        if category == "unknown":
            display.warn(f"Skipping unrecognised target (not in allow-list): {target}")
            continue

        verb = "Would clean" if dry_run else "Cleaning"
        display.info(f"{verb} {category}  ({target})")
        try:
            freed, files = _CLEANERS[category](dry_run)
        except Exception as exc:  # noqa: BLE001 — we want to keep going
            display.err(f"  failed: {exc}")
            continue
        if freed or files:
            word = "would free" if dry_run else "freed"
            removed = "would remove" if dry_run else "removed"
            display.ok(f"  {word} {_bytes_human(freed)} · {removed} {files} file(s)")
        else:
            display.dim("  already clean")
        total_freed += freed
        total_files += files

    display.console.print()
    summary_verb = "Would free" if dry_run else "Freed"
    summary_removed = "would remove" if dry_run else "removed"
    display.panel(
        f"{summary_verb} [bold green]{_bytes_human(total_freed)}[/bold green]  ·  "
        f"{summary_removed.capitalize()} [bold]{total_files}[/bold] file(s)",
        title="Cleanup Summary (dry-run)" if dry_run else "Cleanup Summary",
        style="green",
    )
    return 0


__all__ = ["cmd_status", "cmd_clean"]
