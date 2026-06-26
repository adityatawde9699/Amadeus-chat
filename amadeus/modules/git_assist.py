"""
Git assistant — `amadeus git status` and `amadeus git commit`.

* `git status`  — deterministic pretty-print of `git status --porcelain`
                  plus `git diff --stat`.
* `git commit`  — loads the LLM *only* for commit message generation, then
                  releases it.  Falls back to a deterministic template if
                  the LLM is unavailable.

Determinism-first: even with the LLM available, we *propose* a message and
ask for confirmation before running `git commit`.  No surprises.
"""
from __future__ import annotations

import re
import subprocess
from collections import Counter
from typing import Any

from ..core.config import Config
from ..utils import display
from ..utils.llm import llm_session, is_available


# ── helpers ────────────────────────────────────────────────────────────

def _git(args: list[str], cwd: str = ".", timeout: int = 15) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr
    except (subprocess.SubprocessError, OSError) as exc:
        return -1, "", str(exc)


def _is_repo(cwd: str = ".") -> bool:
    rc, _, _ = _git(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
    return rc == 0


def _porcelain(cwd: str = ".") -> list[str]:
    rc, out, _ = _git(["status", "--porcelain"], cwd=cwd)
    if rc != 0:
        return []
    return [line for line in out.splitlines() if line.strip()]


def _diff_stat(cwd: str = ".") -> str:
    rc, out, _ = _git(["diff", "--stat"], cwd=cwd)
    if rc != 0:
        return ""
    return out.strip()


def _branch(cwd: str = ".") -> str:
    rc, out, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return out.strip() if rc == 0 else "-"


def _classify(line: str) -> tuple[str, str]:
    """Return (status_code, path) from a porcelain line."""
    code = line[:2]
    path = line[3:]
    # Renames come as `old -> new`
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return code, path


# ── git status ─────────────────────────────────────────────────────────

def cmd_status(cfg: Config, args: Any) -> int:
    if not _is_repo():
        display.err("Not inside a git repository.")
        return 1

    branch = _branch()
    porcelain = _porcelain()
    display.header("Git Status", f"branch={branch}  changes={len(porcelain)}")

    if not porcelain:
        display.ok("Working tree clean.")
        return 0

    # Group by status code for a readable view.
    grouped: dict[str, list[str]] = {}
    for code, path in (_classify(l) for l in porcelain):
        key = code.strip() or "?"
        grouped.setdefault(key, []).append(path)

    style_map = {
        "M": "yellow", " M": "yellow", "MM": "yellow",
        "A": "green", "??": "dim", "D": "red", "R": "cyan", "U": "red",
    }
    table = display.make_table([("Status", "bold"), ("Path", "")])
    for code, paths in sorted(grouped.items()):
        style = style_map.get(code, "")
        for p in paths:
            table.add_row(f"[{style}]{code}[/{style}]" if style else code, p)
    display.console.print(table)

    # diff --stat
    stat = _diff_stat()
    if stat:
        display.console.print()
        display.dim("── diff --stat ──")
        display.console.print(stat)

    return 0


# ── git commit ─────────────────────────────────────────────────────────

_COMMIT_SYSTEM_PROMPT = (
    "You write Conventional Commits messages. Produce ONE message in the form "
    "`type(scope): imperative summary`, optionally followed by a blank line and "
    "a 1-3 sentence body explaining the why. Keep the summary under 72 "
    "characters. Use one of: feat, fix, docs, style, refactor, perf, test, "
    "build, ci, chore, revert. Reply with only the commit message — no "
    "preamble, no code fences, no commentary. /no_think"
)

_COMMIT_USER_TEMPLATE = """\
Diff:
```diff
{diff}
```

Files changed:
{files}"""


def _gather_diff(max_chars: int = 8000) -> tuple[str, list[str]]:
    """Return (diff_text, files_changed).  Truncated to keep prompt small."""
    porcelain = _porcelain()
    files = [_classify(l)[1] for l in porcelain]

    # Get staged + unstaged diff so the message reflects reality.
    rc1, staged, _ = _git(["diff", "--cached"])
    rc2, unstaged, _ = _git(["diff"])
    diff = staged + "\n" + unstaged
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n…[truncated]"
    return diff, files


def _infer_type(files: list[str]) -> str:
    """Cheap heuristic fallback when no LLM is available."""
    if any(f.endswith((".md", ".rst", ".txt")) for f in files):
        return "docs"
    if any("test" in f.lower() for f in files):
        return "test"
    if any(f.endswith((".yml", ".yaml", ".toml", "Dockerfile", "Makefile")) for f in files):
        return "build"
    return "chore"


def _fallback_message(files: list[str], cfg: Config) -> str:
    """Deterministic commit message when the LLM is unavailable."""
    ctype = _infer_type(files) if cfg.git.default_type == "auto" else cfg.git.default_type
    # Pick the most common top-level dir as scope
    dirs = Counter((f.split("/")[0] if "/" in f else "root") for f in files)
    scope = dirs.most_common(1)[0][0] if dirs else ""
    scope_str = f"({scope})" if scope and scope != "root" else ""
    summary = ", ".join(files[:3])
    if len(files) > 3:
        summary += f", +{len(files) - 3} more"
    return f"{ctype}{scope_str}: update {summary}"


def _propose_message(cfg: Config, diff: str, files: list[str]) -> str:
    """Use the LLM if available; otherwise fall back deterministically."""
    if not is_available(cfg) or not diff.strip():
        return _fallback_message(files, cfg)

    user_msg = _COMMIT_USER_TEMPLATE.format(
        diff=diff[:4000],
        files="\n".join(files[:30]),
    )
    try:
        with llm_session(cfg) as llm:
            if llm is None:
                return _fallback_message(files, cfg)
            # Use the chat API so llama-cpp applies the model's chat template —
            # raw completion on an instruct model produces garbage.
            msg = llm.chat(
                [
                    {"role": "system", "content": _COMMIT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=cfg.model.max_tokens,
                temperature=cfg.model.temperature,
            )
        # Strip stray code fences / leading labels the model may add anyway.
        msg = re.sub(r"^```[a-z]*\n?", "", msg).strip("`").strip()
        return msg or _fallback_message(files, cfg)
    except Exception as exc:  # noqa: BLE001
        display.warn(f"LLM failed ({exc}); falling back to deterministic message.")
        return _fallback_message(files, cfg)


def cmd_commit(cfg: Config, args: Any) -> int:
    if not _is_repo():
        display.err("Not inside a git repository.")
        return 1

    porcelain = _porcelain()
    if not porcelain:
        display.warn("Nothing to commit — working tree clean.")
        return 0

    display.header("Generating Commit Message")

    # Build the message from the *current* working tree (staged + unstaged)
    # WITHOUT staging anything yet.  Staging only happens after the user
    # accepts — so aborting leaves the index exactly as it was found.
    diff, files = _gather_diff()
    if not files:
        display.warn("No file changes detected.")
        return 0

    display.dim(f"Files: {', '.join(files[:8])}{' …' if len(files) > 8 else ''}")
    message = _propose_message(cfg, diff, files)

    display.console.print()
    display.panel(message, title="Proposed commit message", style="cyan")
    display.console.print()

    if args.yes:
        choice = "y"
    else:
        choice = display.prompt("Accept this message? [y]es / [e]dit / [n]o", default="y").lower()

    if choice == "e":
        message = display.prompt("Enter new message (single line)", default=message)
        choice = "y"
    if choice != "y":
        display.warn("Commit aborted.  Index left untouched.")
        return 1

    # Only now do we touch the index.
    if cfg.git.auto_stage and not args.no_stage:
        rc, _, err = _git(["add", "-A"])
        if rc != 0:
            display.err(f"git add -A failed: {err.strip()}")
            return 1
        display.ok("Staged all changes (git add -A).")

    rc, _, err = _git(["commit", "-m", message])
    if rc != 0:
        display.err(f"git commit failed: {err.strip()}")
        return 1
    display.ok("Committed.")
    # Show the resulting commit hash
    rc, out, _ = _git(["log", "-1", "--oneline"])
    if rc == 0:
        display.dim(out.strip())
    return 0


__all__ = ["cmd_status", "cmd_commit"]
