"""
Task management — `amadeus task add/list/done/delete`.

Tasks live in ``~/.amadeus/tasks.json`` as a flat list of dicts.  No LLM,
no async, no database — just JSON I/O via ``core.storage``.
"""
from __future__ import annotations

from typing import Any

from ..core.config import Config
from ..core import storage
from ..utils import display


def cmd_add(cfg: Config, args: Any) -> int:
    title = args.title
    if not title:
        display.err("task title is required.")
        return 2
    task = storage.add_task(cfg.tasks_path, title)
    display.ok(f"Task #{task['id']} added: {task['title']}")
    return 0


def cmd_list(cfg: Config, args: Any) -> int:
    tasks = storage.load_tasks(cfg.tasks_path)
    if not args.all:
        tasks = [t for t in tasks if not t["done"]]
    display.render_tasks(tasks)
    return 0


def cmd_done(cfg: Config, args: Any) -> int:
    task = storage.complete_task(cfg.tasks_path, args.id)
    if task is None:
        display.err(f"No task with id={args.id}.")
        return 1
    display.ok(f"Task #{task['id']} done: {task['title']}")
    return 0


def cmd_delete(cfg: Config, args: Any) -> int:
    ok = storage.delete_task(cfg.tasks_path, args.id)
    if not ok:
        display.err(f"No task with id={args.id}.")
        return 1
    display.ok(f"Task #{args.id} deleted.")
    return 0


__all__ = ["cmd_add", "cmd_list", "cmd_done", "cmd_delete"]
