"""
Storage layer for Amadeus.

All persistence goes through this module so the rest of the codebase stays
free of direct file I/O.  The data model is intentionally tiny:

* ``tasks.json``        — list of ``{id, title, done, created_at}`` dicts
* ``knowledge_base/``   — one Markdown file per topic
* ``research/<slug>/``  — ``report.md`` + ``sources.json``
* ``indexes/``          — cached BM25 token lists (Phase 4)
"""
from __future__ import annotations

import json
import os
import re
import time
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


# ── helpers ────────────────────────────────────────────────────────────

def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    """Atomically write ``data`` as JSON.

    Writes to a temp file in the same directory and ``os.replace()``s it over
    the target, so an interrupted write can never leave a half-written (and
    thus corrupt) ``tasks.json`` / index cache behind.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        # Clean up the temp file on any failure (including KeyboardInterrupt).
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── slugify ────────────────────────────────────────────────────────────

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase kebab-ish slug.  Used for note filenames and research dirs."""
    s = text.strip().lower()
    s = _SLUG_RE.sub("-", s).strip("-")
    return s or "untitled"


# ── tasks.json ─────────────────────────────────────────────────────────

def load_tasks(path: Path) -> list[dict[str, Any]]:
    """Return the list of tasks (each task is a plain dict)."""
    data = _read_json(path, {"tasks": []})
    if not isinstance(data, dict) or "tasks" not in data:
        return []
    return list(data["tasks"])


def save_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    _write_json(path, {"tasks": tasks})


def add_task(path: Path, title: str) -> dict[str, Any]:
    tasks = load_tasks(path)
    next_id = (max((t["id"] for t in tasks), default=0)) + 1
    task = {
        "id": next_id,
        "title": title,
        "done": False,
        "created_at": _now_iso(),
        "completed_at": None,
    }
    tasks.append(task)
    save_tasks(path, tasks)
    return task


def complete_task(path: Path, task_id: int) -> dict[str, Any] | None:
    tasks = load_tasks(path)
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            t["completed_at"] = _now_iso()
            save_tasks(path, tasks)
            return t
    return None


def delete_task(path: Path, task_id: int) -> bool:
    tasks = load_tasks(path)
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) == len(tasks):
        return False
    save_tasks(path, new_tasks)
    return True


# ── knowledge_base/ ────────────────────────────────────────────────────

NOTE_HEADER_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def list_notes(kb_dir: Path) -> list[Path]:
    """Return all .md files in the knowledge base, sorted by mtime desc."""
    if not kb_dir.exists():
        return []
    files = list(kb_dir.glob("*.md"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def note_path(kb_dir: Path, title: str) -> Path:
    return kb_dir / f"{slugify(title)}.md"


def create_note(kb_dir: Path, title: str, body: str = "") -> Path:
    """Create (or overwrite) a note.  Returns the note's path."""
    kb_dir.mkdir(parents=True, exist_ok=True)
    p = note_path(kb_dir, title)
    if body:
        content = body
    else:
        # Helpful template so the user has something to edit.
        content = (
            f"# {title}\n\n"
            f"_Created: {_now_iso()}_\n\n"
            f"## Summary\n\n"
            f"- \n\n"
            f"## Notes\n\n"
            f"- \n"
        )
    p.write_text(content, encoding="utf-8")
    return p


def read_note(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_note_metadata(path: Path) -> dict[str, Any]:
    """Light-weight front-matter-ish extraction (title + first paragraph).

    Skips markdown headers (lines starting with ``#``) and metadata lines
    starting with ``_`` (our template's ``_Created: …`` line).  Returns the
    first non-empty paragraph found.
    """
    text = read_note(path)
    title_match = NOTE_HEADER_RE.search(text)
    title = title_match.group(1).strip() if title_match else path.stem
    body = text[title_match.end():] if title_match else text

    # Walk paragraph-by-paragraph, skipping ones that begin with a header or
    # metadata marker.  Within a paragraph, strip out any leading header line.
    first_para = ""
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Drop leading header / metadata lines inside the chunk.
        kept_lines = []
        for line in chunk.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("_") and stripped.endswith("_"):
                continue
            kept_lines.append(stripped)
        if kept_lines:
            first_para = " ".join(kept_lines)
            break
    return {
        "path": str(path),
        "title": title,
        "first_para": first_para[:200],
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "size": path.stat().st_size,
    }


# ── research/ ──────────────────────────────────────────────────────────

def research_dir(research_root: Path, topic: str) -> Path:
    d = research_root / slugify(topic)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_research(d: Path, report_md: str, sources: list[dict[str, Any]]) -> tuple[Path, Path]:
    report_path = d / "report.md"
    sources_path = d / "sources.json"
    report_path.write_text(report_md, encoding="utf-8")
    _write_json(sources_path, sources)
    return report_path, sources_path


# ── indexes/ (BM25 cache, Phase 4) ─────────────────────────────────────

def index_cache_path(indexes_dir: Path, name: str) -> Path:
    return indexes_dir / f"{slugify(name)}.json"


def load_index_cache(indexes_dir: Path, name: str) -> dict[str, Any] | None:
    p = index_cache_path(indexes_dir, name)
    return _read_json(p, None)


def save_index_cache(indexes_dir: Path, name: str, data: dict[str, Any]) -> Path:
    p = index_cache_path(indexes_dir, name)
    _write_json(p, data)
    return p


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_markdown_files(d: Path) -> Iterable[Path]:
    if not d.exists():
        return []
    return d.rglob("*.md")


__all__ = [
    "slugify",
    "load_tasks",
    "save_tasks",
    "add_task",
    "complete_task",
    "delete_task",
    "list_notes",
    "note_path",
    "create_note",
    "read_note",
    "parse_note_metadata",
    "research_dir",
    "save_research",
    "load_index_cache",
    "save_index_cache",
    "index_cache_path",
    "file_md5",
    "iter_markdown_files",
]
