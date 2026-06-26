"""
Rich-based terminal rendering helpers.

Centralises the *look & feel* of Amadeus so individual modules don't have to
import ``rich`` directly.  All color-coding rules live here:

* green  = success
* yellow = warning
* red    = error
* cyan   = info
* dim    = secondary / metadata
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt


# A single shared console — keeps color/width decisions consistent.
console = Console()


# ── primitives ─────────────────────────────────────────────────────────

def info(msg: str) -> None:
    console.print(f"[cyan]ℹ[/cyan] {msg}")


def ok(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def warn(msg: str) -> None:
    console.print(f"[yellow]⚠[/yellow] {msg}")


def err(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")


def dim(msg: str) -> None:
    console.print(f"[dim]{msg}[/dim]")


def header(title: str, subtitle: str | None = None) -> None:
    """Print a section header rule with a title."""
    console.print()
    if subtitle:
        console.print(Rule(f"[bold cyan]{title}[/bold cyan] · [dim]{subtitle}[/dim]"))
    else:
        console.print(Rule(f"[bold cyan]{title}[/bold cyan]"))
    console.print()


def panel(content: str | Text, title: str | None = None, style: str = "cyan") -> None:
    """Print a Rich panel with a colored border."""
    console.print(Panel(content, title=title, border_style=style, expand=True))


def markdown(text: str) -> None:
    console.print(Markdown(text))


def confirm(question: str, default: bool = False) -> bool:
    return Confirm.ask(f"[yellow]?[/yellow] {question}", default=default, console=console)


def prompt(question: str, default: str = "") -> str:
    return Prompt.ask(f"[cyan]?[/cyan] {question}", default=default, console=console)


# ── tables ─────────────────────────────────────────────────────────────

def make_table(columns: list[tuple[str, str]], title: str | None = None) -> Table:
    """Build a Table.  ``columns`` is a list of (header, style) tuples.

    ``style`` is a Rich style string applied to the column body (e.g. "cyan",
    "bold", "dim").  Pass "" for no styling.
    """
    t = Table(title=title, show_header=True, header_style="bold cyan",
              border_style="dim", expand=True)
    for header, style in columns:
        t.add_column(header, style=style or None, overflow="fold")
    return t


def render_tasks(tasks: list[dict[str, Any]]) -> None:
    if not tasks:
        info("No tasks yet.  Add one with: amadeus task add \"<title>\"")
        return
    t = make_table([("ID", "dim"), ("✓", "green"), ("Title", ""), ("Created", "dim")],
                   title="Tasks")
    for task in tasks:
        done = "[green]✓[/green]" if task["done"] else "[dim]·[/dim]"
        title = f"[dim]{task['title']}[/dim]" if task["done"] else task["title"]
        t.add_row(str(task["id"]), done, title, task.get("created_at", ""))
    console.print(t)


def render_notes(notes: list[dict[str, Any]]) -> None:
    if not notes:
        info("No notes yet.  Create one with: amadeus learn new \"<title>\"")
        return
    t = make_table([("Title", "bold"), ("First paragraph", "dim"), ("Modified", "dim")],
                   title="Knowledge Base")
    for n in notes:
        t.add_row(n["title"], n["first_para"], n["mtime"])
    console.print(t)


def render_search_results(results: list[dict[str, Any]]) -> None:
    if not results:
        warn("No matches.")
        return
    t = make_table([("Score", "green"), ("Note", "bold"), ("Snippet", "dim")],
                   title="BM25 Search Results")
    for r in results:
        t.add_row(f"{r['score']:.2f}", r["title"], r["snippet"])
    console.print(t)


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    t = make_table([("#", "dim"), ("URL", "cyan"), ("Title", "")], title="Sources")
    for i, s in enumerate(sources, 1):
        t.add_row(str(i), s.get("url", ""), s.get("title", "")[:80])
    console.print(t)


def render_kv(rows: list[tuple[str, str]], title: str | None = None) -> None:
    """Print a two-column key/value table."""
    t = make_table([("Key", "dim"), ("Value", "")], title=title)
    for k, v in rows:
        t.add_row(k, v)
    console.print(t)


def footer(msg: str = "") -> None:
    if msg:
        console.print()
        console.print(Rule(style="dim"))
        dim(msg)
    console.print()


__all__ = [
    "console",
    "info", "ok", "warn", "err", "dim",
    "header", "panel", "markdown",
    "confirm", "prompt",
    "make_table",
    "render_tasks", "render_notes", "render_search_results",
    "render_sources", "render_kv",
    "footer",
]
