"""LLM helpers that don't require a loaded model."""
from __future__ import annotations

from amadeus.utils import llm
from amadeus.core.config import Config


def test_strip_think_removes_closed_block():
    out = llm.strip_think("<think>reasoning here</think>feat: do a thing")
    assert out == "feat: do a thing"


def test_strip_think_removes_unclosed_block():
    # Truncated reasoning (model ran out of tokens mid-think).
    out = llm.strip_think("answer first\n<think>still thinking and cut off")
    assert out == "answer first"


def test_strip_think_case_insensitive_multiline():
    text = "<THINK>\nline1\nline2\n</THINK>\n\nfinal answer"
    assert llm.strip_think(text) == "final answer"


def test_strip_think_noop_when_absent():
    assert llm.strip_think("  plain text  ") == "plain text"


def test_is_available_false_without_model(tmp_path):
    cfg = Config()
    cfg.model.path = ""
    assert llm.is_available(cfg) is False
