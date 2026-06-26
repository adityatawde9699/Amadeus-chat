"""Git assistant: porcelain classification and deterministic fallback."""
from __future__ import annotations

from amadeus.core.config import GitConfig, Config
from amadeus.modules import git_assist


def test_classify_plain_and_rename():
    assert git_assist._classify(" M path/to/file.py") == (" M", "path/to/file.py")
    assert git_assist._classify("?? new.txt") == ("??", "new.txt")
    code, path = git_assist._classify("R  old.py -> new.py")
    assert code == "R " and path == "new.py"


def test_infer_type_heuristics():
    assert git_assist._infer_type(["README.md"]) == "docs"
    assert git_assist._infer_type(["tests/test_x.py"]) == "test"
    assert git_assist._infer_type(["pyproject.toml"]) == "build"
    assert git_assist._infer_type(["src/app.py"]) == "chore"


def test_fallback_message_uses_default_type_and_scope():
    cfg = Config(git=GitConfig(default_type="feat"))
    msg = git_assist._fallback_message(["amadeus/cli.py", "amadeus/core/config.py"], cfg)
    assert msg.startswith("feat(amadeus):")
    assert "cli.py" in msg


def test_fallback_message_auto_type():
    cfg = Config(git=GitConfig(default_type="auto"))
    msg = git_assist._fallback_message(["docs/guide.md"], cfg)
    assert msg.startswith("docs")


def test_fallback_message_truncates_file_list():
    cfg = Config(git=GitConfig(default_type="chore"))
    files = [f"f{i}.py" for i in range(6)]
    msg = git_assist._fallback_message(files, cfg)
    assert "+3 more" in msg
