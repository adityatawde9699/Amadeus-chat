"""CLI dispatcher: parser wiring and smoke dispatch (isolated to tmp home)."""
from __future__ import annotations

import types

import pytest

from amadeus import cli


def _parse(argv):
    return cli.build_parser().parse_args(argv)


@pytest.mark.parametrize("argv,expected_attrs", [
    (["start"], {}),
    (["task", "add", "hello"], {"title": "hello"}),
    (["task", "list", "--all"], {"all": True}),
    (["task", "done", "3"], {"id": 3}),
    (["task", "delete", "4"], {"id": 4}),
    (["git", "status"], {}),
    (["git", "commit", "-y"], {"yes": True, "no_stage": False}),
    (["learn", "new", "X", "--no-edit"], {"title": "X", "no_edit": True, "force": False}),
    (["learn", "search", "q"], {"query": "q"}),
    (["learn", "show", "slug"], {"slug": "slug"}),
    (["research", "topic", "--no-llm"], {"topic": "topic", "no_llm": True}),
    (["sys", "status"], {}),
    (["sys", "clean", "--dry-run"], {"dry_run": True}),
    (["config", "--path"], {"path": True}),
])
def test_every_subcommand_parses(argv, expected_attrs):
    args = _parse(argv)
    assert hasattr(args, "func")
    for k, v in expected_attrs.items():
        assert getattr(args, k) == v


def test_no_command_returns_2(capsys):
    assert cli.main([]) == 2


def test_config_path_prints_path(cfg, capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: cfg)
    assert cli.main(["config", "--path"]) == 0
    out = capsys.readouterr().out
    assert str(cfg.config_path) in out


def test_main_dispatches_task_add_and_list(cfg, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_config", lambda: cfg)
    assert cli.main(["task", "add", "do a thing"]) == 0
    assert cli.main(["task", "list"]) == 0
    out = capsys.readouterr().out
    assert "do a thing" in out


def test_default_type_override_applied(cfg, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: cfg)
    captured = {}

    def fake_commit(c, a):
        captured["default_type"] = c.git.default_type
        return 0

    monkeypatch.setattr(cli.git_assist, "cmd_commit", fake_commit)
    assert cli.main(["git", "commit", "--default-type", "feat", "-y"]) == 0
    assert captured["default_type"] == "feat"
