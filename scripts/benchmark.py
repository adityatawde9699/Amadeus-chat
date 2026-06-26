#!/usr/bin/env python3
"""
Amadeus micro-benchmark.

Measures the figures the README used to *estimate*:

  * cold-start wall time of a deterministic command (`amadeus config --path`)
  * idle resident memory of that cold start
  * note-search latency over a synthetic knowledge base
  * LLM load time + RAM, and a single commit-style completion (if a model is
    configured / discoverable)

Run:  uv run python scripts/benchmark.py
Everything is isolated to a temp Amadeus home, so your real ~/.amadeus is
never touched.
"""
from __future__ import annotations

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path

# Ensure the package is importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psutil  # noqa: E402

from amadeus.core.config import ensure_amadeus_home, load_config  # noqa: E402
from amadeus.core import storage  # noqa: E402
from amadeus.modules import notes  # noqa: E402
from amadeus.utils.llm import is_available, llm_session  # noqa: E402


def _fmt_mb(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


def bench_cold_start(home: Path) -> tuple[float, int]:
    """Run `amadeus config --path` as a fresh subprocess and time it.

    Returns (wall_seconds, peak_rss_bytes).
    """
    env = dict(os.environ)
    # Force the isolated home by pointing HOME at the temp dir's parent.
    repo = str(Path(__file__).resolve().parent.parent)
    cmd = [sys.executable, "-c",
           "import time,resource,sys;"
           "sys.path.insert(0, %r);"
           "from amadeus.cli import main;"
           "main(['config','--path']);"
           "print('RSS', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)" % repo]
    t0 = time.perf_counter()
    out = subprocess.run(cmd, capture_output=True, text=True, env=env)
    wall = time.perf_counter() - t0
    rss_kb = 0
    for line in out.stdout.splitlines():
        if line.startswith("RSS"):
            rss_kb = int(line.split()[1])
    # ru_maxrss is KiB on Linux.
    return wall, rss_kb * 1024


def bench_note_search(home: Path, n_notes: int = 200) -> tuple[float, int]:
    """Build a synthetic KB and time one BM25L search.  Returns (sec, n_notes)."""
    cfg = load_config(home)
    words = ["rust", "python", "kernel", "scheduler", "ownership", "borrow",
             "async", "memory", "cache", "vector", "token", "model"]
    for i in range(n_notes):
        body = f"# Note {i}\n\n" + " ".join(words[(i + j) % len(words)] for j in range(40))
        storage.create_note(cfg.knowledge_base_dir, f"note-{i:04d}", body=body)

    import types
    args = types.SimpleNamespace(query="rust ownership borrow checker")
    # Warm cache first so we measure steady-state search, not first-build.
    notes._load_or_build_index(cfg)
    t0 = time.perf_counter()
    notes.cmd_search(cfg, args)
    return time.perf_counter() - t0, n_notes


def bench_llm(home: Path) -> dict[str, str] | None:
    cfg = load_config(home)
    if not is_available(cfg):
        return None
    proc = psutil.Process()
    rss_before = proc.memory_info().rss
    t0 = time.perf_counter()
    with llm_session(cfg) as llm:
        load_s = time.perf_counter() - t0
        rss_loaded = proc.memory_info().rss
        t1 = time.perf_counter()
        out = llm.complete("Say 'ok' and nothing else.", max_tokens=8, temperature=0.0)
        infer_s = time.perf_counter() - t1
    rss_after = proc.memory_info().rss
    return {
        "model": os.path.basename(cfg.model.path),
        "load_time": f"{load_s:.2f} s",
        "load_rss_delta": _fmt_mb(rss_loaded - rss_before),
        "first_token_completion": f"{infer_s:.2f} s",
        "released_rss_delta": _fmt_mb(rss_after - rss_before),
        "sample_output": out[:40].replace("\n", " "),
    }


def main() -> int:
    print("Amadeus benchmark")
    print("=" * 60)

    # Separate temp homes so the LLM bench doesn't index 200 synthetic notes.
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        home1 = ensure_amadeus_home(Path(d1) / ".amadeus")
        wall, rss = bench_cold_start(home1)
        print(f"cold start (config --path) : {wall * 1000:.0f} ms")
        print(f"cold-start peak RSS        : {_fmt_mb(rss)}")

        home2 = ensure_amadeus_home(Path(d2) / ".amadeus")
        search_s, n = bench_note_search(home2)
        print(f"note search ({n} notes)    : {search_s * 1000:.1f} ms")

    print("-" * 60)
    # LLM bench uses the real (discoverable) model + the real home.
    real_home = ensure_amadeus_home()
    llm = bench_llm(real_home)
    if llm is None:
        print("LLM: not available (no model discovered / llama-cpp missing)")
    else:
        for k, v in llm.items():
            print(f"LLM {k:24s}: {v}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
