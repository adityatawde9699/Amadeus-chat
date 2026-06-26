"""
Lazy-loaded LLM wrapper.

The Amadeus architecture is *deterministic-first*: the LLM is only loaded
into RAM when explicitly needed (git commit message generation, research
summarisation) and released immediately afterwards.

This module provides a context-manager-based API so callers can do::

    with llm_session(config) as llm:
        msg = llm.complete("Summarise: ...")

…guaranteeing that the llama-cpp model is unloaded (and the Python object
dropped) on exit, freeing RAM back to the OS.

If ``llama-cpp-python`` is not installed, or no model path is configured,
``llm_session`` yields ``None`` — callers should fall back to deterministic
behaviour (see ``modules/git_assist.py`` for an example).
"""
from __future__ import annotations

import gc
import logging
import os
import re
from contextlib import contextmanager
from typing import Iterator, Optional

from ..core.config import Config

log = logging.getLogger("amadeus.llm")


# Reasoning models (e.g. Qwen3) emit a <think>…</think> block before their
# answer.  We never want that chain-of-thought in a commit message or report,
# so strip it (including an unclosed block if the model ran out of tokens).
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CLOSE_THINK_RE = re.compile(r"^.*?</think>", re.DOTALL | re.IGNORECASE)
_OPEN_THINK_RE = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)


def strip_think(text: str) -> str:
    """Remove reasoning blocks from a reasoning model's output.

    Handles three shapes:
      * a matched ``<think>…</think>`` block anywhere in the text;
      * a *leading* reasoning section ending in ``</think>`` with no opening
        tag — the Qwen3 chat template auto-opens the think block, so the
        returned content starts mid-reasoning and only the closing tag is
        visible.  We keep everything after the last ``</think>``;
      * an unclosed ``<think>…`` (model truncated before finishing).
    """
    text = _THINK_RE.sub("", text)
    if "</think>" in text.lower():
        text = _CLOSE_THINK_RE.sub("", text)
    text = _OPEN_THINK_RE.sub("", text)
    return text.strip()


class LLMWrapper:
    """Thin wrapper around a llama-cpp-python ``Llama`` instance.

    Exists so we can swap the backend (e.g. to an OpenAI-compatible local
    server) without touching every caller.
    """

    def __init__(self, llama, cfg):
        self._llama = llama
        self._cfg = cfg

    def complete(self, prompt: str, *, max_tokens: int | None = None,
                 temperature: float | None = None, stop: list[str] | None = None) -> str:
        """Single-shot completion.  Returns the model's text output."""
        kwargs = {
            "max_tokens": max_tokens or self._cfg.model.max_tokens,
            "temperature": temperature if temperature is not None else self._cfg.model.temperature,
            "echo": False,
        }
        if stop:
            kwargs["stop"] = stop
        resp = self._llama(prompt, **kwargs)
        return strip_think(resp["choices"][0]["text"])

    def chat(self, messages: list[dict[str, str]], *, max_tokens: int | None = None,
             temperature: float | None = None) -> str:
        """Chat-style completion.  ``messages`` follows the OpenAI shape."""
        kwargs = {
            "max_tokens": max_tokens or self._cfg.model.max_tokens,
            "temperature": temperature if temperature is not None else self._cfg.model.temperature,
        }
        resp = self._llama.create_chat_completion(messages=messages, **kwargs)
        return strip_think(resp["choices"][0]["message"]["content"])


def _load_llama(cfg: Config):
    """Import llama_cpp lazily and instantiate the model.

    Returns ``None`` if anything is missing (no model path, no library).
    The caller is expected to handle the ``None`` case gracefully.
    """
    model_path = cfg.model.path
    if not model_path or not os.path.isfile(model_path):
        log.warning("No model path configured (or file missing): %r", model_path)
        return None

    try:
        from llama_cpp import Llama
    except ImportError:
        log.warning("llama-cpp-python not installed; LLM features disabled.")
        return None

    n_threads = cfg.model.n_threads or None  # 0 → let llama-cpp auto-detect
    log.info("Loading LLM: %s (ctx=%d, threads=%s)", model_path, cfg.model.n_ctx, n_threads)
    llama = Llama(
        model_path=model_path,
        n_ctx=cfg.model.n_ctx,
        n_threads=n_threads,
        n_batch=cfg.model.n_batch,
        use_mlock=False,
        use_mmap=True,
        verbose=False,
        seed=42,
    )
    return llama


@contextmanager
def llm_session(cfg: Config) -> Iterator[Optional[LLMWrapper]]:
    """Context manager that loads an LLM, yields it, and unloads on exit.

    Yields ``None`` if no LLM is available — callers must handle this.

    The unload path explicitly deletes the llama object and triggers a
    ``gc.collect()`` so mmap'd weights are released back to the OS rather
    than lingering in Python's ref cycles.
    """
    llama = _load_llama(cfg)
    wrapper = LLMWrapper(llama, cfg) if llama is not None else None
    try:
        yield wrapper
    finally:
        if llama is not None:
            log.info("Unloading LLM (freeing RAM).")
            del llama
            del wrapper
            gc.collect()


def is_available(cfg: Config) -> bool:
    """True if both the library and a model path are configured."""
    if not cfg.model.path or not os.path.isfile(cfg.model.path):
        return False
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    return True


__all__ = ["LLMWrapper", "llm_session", "is_available", "strip_think"]
