"""
Amadeus CLI — fire-and-forget command dispatcher.

Each subcommand maps to a ``cmd_*(cfg, args) -> int`` function in one of the
feature modules.  ``main()`` loads the config once, dispatches to the selected
command, and returns its exit code.  No persistent process, no daemon — the
process starts, does one job, and exits.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from . import __version__
from .core.config import load_config, config_to_dict, Config
from .modules import git_assist, notes, research, startup, sysadmin, tasks
from .utils import display


# ── config command (small enough to live here) ─────────────────────────

def _flatten(d: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    """Flatten the nested config dict into (dotted.key, value) rows."""
    rows: list[tuple[str, str]] = []
    for key, val in d.items():
        dotted = f"{prefix}{key}"
        if isinstance(val, dict):
            rows.extend(_flatten(val, prefix=f"{dotted}."))
        else:
            rows.append((dotted, str(val)))
    return rows


def cmd_config(cfg: Config, args: Any) -> int:
    if args.path:
        # Plain print: a path must be machine-readable (no wrapping/markup).
        print(str(cfg.config_path))
        return 0
    display.header("Configuration", str(cfg.config_path))
    display.render_kv(_flatten(config_to_dict(cfg)))
    return 0


# ── parser construction ─────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="amadeus",
        description="Deterministic-first, fire-and-forget CLI assistant.",
    )
    p.add_argument("--version", action="version", version=f"amadeus {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    # start
    sp = sub.add_parser("start", help="Daily dashboard (system + tasks + git)")
    sp.set_defaults(func=startup.cmd_start)

    # task
    tp = sub.add_parser("task", help="Task management")
    tsub = tp.add_subparsers(dest="subcommand", metavar="<action>")
    t_add = tsub.add_parser("add", help="Add a task")
    t_add.add_argument("title", help="Task title")
    t_add.set_defaults(func=tasks.cmd_add)
    t_list = tsub.add_parser("list", help="List open tasks")
    t_list.add_argument("--all", action="store_true", help="Include completed tasks")
    t_list.set_defaults(func=tasks.cmd_list)
    t_done = tsub.add_parser("done", help="Mark a task complete")
    t_done.add_argument("id", type=int, help="Task id")
    t_done.set_defaults(func=tasks.cmd_done)
    t_del = tsub.add_parser("delete", help="Delete a task")
    t_del.add_argument("id", type=int, help="Task id")
    t_del.set_defaults(func=tasks.cmd_delete)

    # git
    gp = sub.add_parser("git", help="Git assistant")
    gsub = gp.add_subparsers(dest="subcommand", metavar="<action>")
    g_status = gsub.add_parser("status", help="Smart git status")
    g_status.set_defaults(func=git_assist.cmd_status)
    g_commit = gsub.add_parser("commit", help="Generate a commit message from the diff")
    g_commit.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    g_commit.add_argument("--no-stage", action="store_true",
                          help="Do not run `git add -A` before committing")
    g_commit.add_argument("--default-type", default=None,
                          help="Conventional-commit type for the fallback message")
    g_commit.set_defaults(func=git_assist.cmd_commit)

    # learn (notes)
    lp = sub.add_parser("learn", help="Notes / knowledge base")
    lsub = lp.add_subparsers(dest="subcommand", metavar="<action>")
    l_new = lsub.add_parser("new", help="Create a markdown note")
    l_new.add_argument("title", help="Note title")
    l_new.add_argument("--body", default="", help="Note body (non-interactive)")
    l_new.add_argument("--no-edit", action="store_true", help="Do not open $EDITOR")
    l_new.add_argument("--force", action="store_true", help="Overwrite an existing note")
    l_new.set_defaults(func=notes.cmd_new)
    l_list = lsub.add_parser("list", help="List all notes")
    l_list.set_defaults(func=notes.cmd_list)
    l_search = lsub.add_parser("search", help="BM25L search across notes")
    l_search.add_argument("query", help="Search query")
    l_search.set_defaults(func=notes.cmd_search)
    l_show = lsub.add_parser("show", help="Print a note")
    l_show.add_argument("slug", help="Note slug (or prefix)")
    l_show.set_defaults(func=notes.cmd_show)

    # research
    rp = sub.add_parser("research", help="Autonomous web research")
    rp.add_argument("topic", help="Research topic")
    rp.add_argument("--no-llm", action="store_true",
                    help="Skip LLM; write a deterministic stitched report")
    rp.set_defaults(func=research.cmd_research)

    # sys
    syp = sub.add_parser("sys", help="System maintenance")
    sysub = syp.add_subparsers(dest="subcommand", metavar="<action>")
    s_status = sysub.add_parser("status", help="RAM / CPU / Disk / processes")
    s_status.set_defaults(func=sysadmin.cmd_status)
    s_clean = sysub.add_parser("clean", help="Clean allow-listed caches")
    s_clean.add_argument("--dry-run", action="store_true",
                         help="Report what would be freed without deleting")
    s_clean.set_defaults(func=sysadmin.cmd_clean)

    # config
    cp = sub.add_parser("config", help="Show configuration")
    cp.add_argument("--path", action="store_true", help="Print the config file path")
    cp.set_defaults(func=cmd_config)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2

    cfg = load_config()

    # CLI override: `git commit --default-type feat`
    if getattr(args, "default_type", None):
        cfg.git.default_type = args.default_type

    try:
        return int(func(cfg, args))
    except KeyboardInterrupt:
        display.console.print()
        display.warn("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
