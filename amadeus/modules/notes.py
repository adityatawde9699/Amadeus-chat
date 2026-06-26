"""
Notes / knowledge-base module.

* `amadeus learn new "<title>"`   — open a fresh markdown note (template)
* `amadeus learn list`            — list all notes
* `amadeus learn search "<query"` — BM25 search across all local notes
* `amadeus learn show <slug>`     — print a note's contents

BM25 is fully deterministic and runs in microseconds, so we re-tokenise on
every search.  Phase 4 adds an index cache (`~/.amadeus/indexes/notes.json`)
that short-circuits re-tokenisation when files haven't changed (MD5 check).
"""
from __future__ import annotations

import re
import os
import subprocess
from pathlib import Path
from typing import Any

from rank_bm25 import BM25L

from ..core.config import Config
from ..core import storage
from ..utils import display


# ── tokenisation ───────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "of", "in",
    "on", "at", "to", "for", "with", "without", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "should", "could", "may", "might", "can", "this", "that", "these",
    "those", "it", "its", "as", "by", "from", "into", "your", "you", "i",
}


def _tokenize(text: str) -> list[str]:
    out = []
    for m in _TOKEN_RE.findall(text.lower()):
        if m in _STOPWORDS or len(m) < 2:
            continue
        out.append(m)
    return out


# ── index cache (Phase 4) ──────────────────────────────────────────────

def _load_or_build_index(cfg: Config) -> tuple[list[dict[str, Any]], list[list[str]]]:
    """Return (notes_meta, corpus_tokens).

    Uses the on-disk cache when possible.  The cache stores per-file MD5s;
    any file whose MD5 has changed (or that doesn't exist in the cache) is
    re-tokenised.
    """
    kb_dir = cfg.knowledge_base_dir
    files = storage.list_notes(kb_dir)

    cache = storage.load_index_cache(cfg.indexes_dir, "notes") or {"files": {}}
    cached = cache.get("files", {})

    meta: list[dict[str, Any]] = []
    corpus: list[list[str]] = []
    new_cache: dict[str, Any] = {}

    for f in files:
        md5 = storage.file_md5(f)
        key = str(f)
        new_cache[key] = md5
        entry = cached.get(key)
        if entry and entry.get("md5") == md5:
            tokens = entry["tokens"]
        else:
            tokens = _tokenize(storage.read_note(f))
        info = storage.parse_note_metadata(f)
        info["md5"] = md5
        meta.append(info)
        corpus.append(tokens)
        new_cache[key] = {"md5": md5, "tokens": tokens}

    storage.save_index_cache(cfg.indexes_dir, "notes", {"files": new_cache})
    return meta, corpus


# ── commands ───────────────────────────────────────────────────────────

def cmd_new(cfg: Config, args: Any) -> int:
    title: str = args.title
    if not title:
        display.err("note title is required.  Usage: amadeus learn new \"<title>\"")
        return 2

    # Don't clobber an existing note unless the caller explicitly asks.
    target = storage.note_path(cfg.knowledge_base_dir, title)
    if target.exists() and not getattr(args, "force", False):
        display.err(f"Note already exists: {target}")
        display.dim("Use --force to overwrite, or `amadeus learn show "
                    f"{target.stem}` to view it.")
        return 1

    path = storage.create_note(cfg.knowledge_base_dir, title, body=args.body or "")
    display.ok(f"Note created: {path}")

    # Open in $EDITOR (or nano/vim fallback) unless --no-edit was given.
    if not args.no_edit:
        editor = os.environ.get("EDITOR") or shutil_which_fallback()
        if editor:
            try:
                subprocess.run([editor, str(path)], check=False)
            except OSError as exc:
                display.warn(f"Could not launch editor: {exc}")
    return 0


def shutil_which_fallback() -> str:
    import shutil
    for candidate in ("nano", "vim", "vi"):
        if shutil.which(candidate):
            return candidate
    return ""


def cmd_list(cfg: Config, args: Any) -> int:
    files = storage.list_notes(cfg.knowledge_base_dir)
    if not files:
        display.info("No notes yet.  Create one with: amadeus learn new \"<title>\"")
        return 0
    notes = [storage.parse_note_metadata(p) for p in files]
    display.render_notes(notes)
    return 0


def cmd_search(cfg: Config, args: Any) -> int:
    query: str = args.query
    if not query:
        display.err("query is required.")
        return 2

    meta, corpus = _load_or_build_index(cfg)
    if not meta:
        display.warn("Knowledge base is empty.")
        return 0

    bm25 = BM25L(corpus)
    q_tokens = _tokenize(query)
    if not q_tokens:
        display.warn("Query has no usable tokens after stopword removal.")
        return 0
    scores = bm25.get_scores(q_tokens)

    ranked = sorted(zip(scores, meta), key=lambda x: x[0], reverse=True)

    # BM25L gives 0 for docs that share no terms with the query, so a strict
    # >0 filter is meaningful here.  We further cap at 10 results.
    results = []
    for score, info in ranked:
        if score <= 0:
            break
        snippet = _snippet(info, q_tokens)
        results.append({
            "score": float(score),
            "title": info["title"],
            "snippet": snippet,
            "path": info["path"],
        })
        if len(results) >= 10:
            break

    display.render_search_results(results)
    return 0


def _snippet(info: dict[str, Any], q_tokens: list[str], width: int = 80) -> str:
    """Build a one-line snippet around the first query hit in the note body."""
    text = storage.read_note(Path(info["path"]))
    lower = text.lower()
    best_pos = -1
    for tok in q_tokens:
        pos = lower.find(tok)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
    if best_pos == -1:
        # Fall back to first paragraph from metadata
        return info["first_para"][:width] or "(no preview)"
    start = max(0, best_pos - width // 2)
    end = min(len(text), best_pos + width // 2)
    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


def cmd_show(cfg: Config, args: Any) -> int:
    slug = args.slug
    # Prefer an exact slug match so an unambiguous request is never resolved
    # to the wrong note by prefix.
    exact = cfg.knowledge_base_dir / f"{storage.slugify(slug)}.md"
    if exact.exists():
        path = exact
    else:
        candidates = sorted(cfg.knowledge_base_dir.glob(f"{slug}*.md"))
        if not candidates:
            display.err(f"No note matching '{slug}'.")
            return 1
        if len(candidates) > 1:
            display.warn(f"'{slug}' is ambiguous — {len(candidates)} notes match:")
            for c in candidates:
                display.dim(f"  {c.stem}")
            display.info("Re-run with the full slug to disambiguate.")
            return 1
        path = candidates[0]
    text = storage.read_note(path)
    display.header(path.stem)
    display.markdown(text)
    return 0


__all__ = ["cmd_new", "cmd_list", "cmd_search", "cmd_show"]
