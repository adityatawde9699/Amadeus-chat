"""Notes: tokenisation, BM25L ranking, index-cache invalidation, commands."""
from __future__ import annotations

import types

from amadeus.core import storage
from amadeus.modules import notes


def test_tokenize_drops_stopwords_and_short():
    toks = notes._tokenize("The quick brown fox is a FOX")
    assert "the" not in toks and "is" not in toks and "a" not in toks
    assert "quick" in toks and "brown" in toks
    assert toks.count("fox") == 2  # case-folded, kept


def test_bm25_ranks_relevant_note_first(cfg):
    storage.create_note(cfg.knowledge_base_dir, "Rust Ownership",
                        body="# Rust Ownership\n\nRust ownership and the borrow checker.\n")
    storage.create_note(cfg.knowledge_base_dir, "Python GIL",
                        body="# Python GIL\n\nThe Python global interpreter lock.\n")

    meta, corpus = notes._load_or_build_index(cfg)
    from rank_bm25 import BM25L
    bm25 = BM25L(corpus)
    scores = bm25.get_scores(notes._tokenize("rust borrow checker"))
    ranked = sorted(zip(scores, meta), key=lambda x: x[0], reverse=True)
    assert ranked[0][1]["title"] == "Rust Ownership"
    assert ranked[0][0] > 0


def test_index_cache_invalidates_on_change(cfg):
    p = storage.create_note(cfg.knowledge_base_dir, "Topic",
                            body="# T\n\nalpha beta gamma\n")
    notes._load_or_build_index(cfg)  # warms the cache
    cache = storage.load_index_cache(cfg.indexes_dir, "notes")
    assert cache["files"][str(p)]["tokens"]

    # Change the file → md5 changes → tokens are re-derived.
    p.write_text("# T\n\ndelta epsilon\n", encoding="utf-8")
    meta, corpus = notes._load_or_build_index(cfg)
    tokens = corpus[0]
    assert "delta" in tokens and "alpha" not in tokens


def test_cmd_new_refuses_overwrite_without_force(cfg, capsys):
    args = types.SimpleNamespace(title="Dup", body="first", no_edit=True, force=False)
    assert notes.cmd_new(cfg, args) == 0
    # Second create without --force is refused.
    args2 = types.SimpleNamespace(title="Dup", body="second", no_edit=True, force=False)
    assert notes.cmd_new(cfg, args2) == 1
    assert storage.read_note(storage.note_path(cfg.knowledge_base_dir, "Dup")) == "first"
    # With --force it overwrites.
    args3 = types.SimpleNamespace(title="Dup", body="third", no_edit=True, force=True)
    assert notes.cmd_new(cfg, args3) == 0
    assert storage.read_note(storage.note_path(cfg.knowledge_base_dir, "Dup")) == "third"


def test_cmd_show_ambiguous_prefix_warns(cfg):
    storage.create_note(cfg.knowledge_base_dir, "alpha one", body="a")
    storage.create_note(cfg.knowledge_base_dir, "alpha two", body="b")
    args = types.SimpleNamespace(slug="alpha")
    assert notes.cmd_show(cfg, args) == 1  # ambiguous → refuse


def test_cmd_show_exact_match(cfg):
    storage.create_note(cfg.knowledge_base_dir, "alpha one", body="a")
    storage.create_note(cfg.knowledge_base_dir, "alpha two", body="b")
    args = types.SimpleNamespace(slug="alpha-one")
    assert notes.cmd_show(cfg, args) == 0
