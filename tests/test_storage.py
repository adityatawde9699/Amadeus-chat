"""Storage layer: slugify, tasks, atomic writes, notes, index cache."""
from __future__ import annotations

import json

from amadeus.core import storage


def test_slugify_basic():
    assert storage.slugify("Hello, World!") == "hello-world"
    assert storage.slugify("  Qwen2.5  Architecture ") == "qwen2-5-architecture"
    assert storage.slugify("") == "untitled"
    assert storage.slugify("---") == "untitled"


def test_task_add_list_complete_delete(tmp_path):
    p = tmp_path / "tasks.json"
    t1 = storage.add_task(p, "first")
    t2 = storage.add_task(p, "second")
    assert t1["id"] == 1 and t2["id"] == 2
    assert t1["done"] is False

    tasks = storage.load_tasks(p)
    assert [t["title"] for t in tasks] == ["first", "second"]

    done = storage.complete_task(p, 1)
    assert done["done"] is True and done["completed_at"]
    assert storage.complete_task(p, 999) is None

    assert storage.delete_task(p, 2) is True
    assert storage.delete_task(p, 2) is False
    assert [t["id"] for t in storage.load_tasks(p)] == [1]


def test_load_tasks_corrupt_returns_empty(tmp_path):
    p = tmp_path / "tasks.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert storage.load_tasks(p) == []


def test_write_json_is_atomic_and_valid(tmp_path):
    p = tmp_path / "data.json"
    storage._write_json(p, {"a": 1, "b": [1, 2, 3]})
    assert json.loads(p.read_text()) == {"a": 1, "b": [1, 2, 3]}
    # No stray temp files left behind.
    leftovers = [q.name for q in tmp_path.iterdir() if q.name != "data.json"]
    assert leftovers == []


def test_note_create_and_metadata(tmp_path):
    kb = tmp_path / "kb"
    p = storage.create_note(kb, "Qwen2 Architecture")
    assert p.name == "qwen2-architecture.md"
    assert p.exists()

    meta = storage.parse_note_metadata(p)
    assert meta["title"] == "Qwen2 Architecture"
    # Template body has no prose paragraph yet.
    assert isinstance(meta["first_para"], str)


def test_note_create_with_body_metadata(tmp_path):
    kb = tmp_path / "kb"
    body = "# Topic\n\nThis is the first paragraph of prose.\n"
    p = storage.create_note(kb, "Topic", body=body)
    meta = storage.parse_note_metadata(p)
    assert meta["title"] == "Topic"
    assert "first paragraph of prose" in meta["first_para"]


def test_index_cache_roundtrip_and_md5(tmp_path):
    idx = tmp_path / "indexes"
    assert storage.load_index_cache(idx, "notes") is None
    storage.save_index_cache(idx, "notes", {"files": {"a": "1"}})
    assert storage.load_index_cache(idx, "notes") == {"files": {"a": "1"}}

    f = tmp_path / "f.txt"
    f.write_text("hello")
    h1 = storage.file_md5(f)
    f.write_text("hello world")
    assert storage.file_md5(f) != h1
