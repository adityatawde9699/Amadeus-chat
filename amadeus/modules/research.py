"""
Autonomous research command — `amadeus research "<topic>"`.

Pipeline (deterministic steps + one LLM call at the very end):
1. Build a search URL (DuckDuckGo HTML — no API key required).
2. Fetch and parse result links with ``requests`` + ``beautifulsoup4``.
3. Fetch each result page, extract main text (deterministic boilerplate
   stripping).
4. Concatenate cleaned excerpts (capped at ~12k chars).
5. Load the LLM *only* for the final summarisation step, then release.
6. Write ``report.md`` + ``sources.json`` to ``~/.amadeus/research/<slug>/``.

If no LLM is available, the report is just the stitched excerpts with a
header — still useful as raw research material.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ..core.config import Config
from ..core import storage
from ..utils import display
from ..utils.llm import llm_session, is_available


# ── fetch helpers ──────────────────────────────────────────────────────

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _fetch(url: str, cfg: Config, *, as_text: bool = True) -> str | bytes | None:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": cfg.research.user_agent or _USER_AGENT},
            timeout=cfg.research.fetch_timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text if as_text else resp.content
    except requests.RequestException as exc:
        display.warn(f"fetch failed: {url}  ({exc.__class__.__name__})")
        return None


def _ddg_search(topic: str, cfg: Config) -> list[str]:
    """Scrape DuckDuckGo HTML for result URLs.  No API key required."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(topic)}"
    html = _fetch(url, cfg)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out: list[str] = []
    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        # DuckDuckGo wraps links as //duckduckgo.com/l/?uddg=<encoded>
        if "uddg=" in href:
            from urllib.parse import parse_qs, unquote
            qs = href.split("?", 1)[1] if "?" in href else ""
            params = parse_qs(qs)
            target = params.get("uddg", [None])[0]
            if target:
                out.append(unquote(target))
        elif href.startswith("http"):
            out.append(href)
        if len(out) >= cfg.research.max_pages:
            break
    return out


# ── text extraction ────────────────────────────────────────────────────

_NOISE_TAGS = ("script", "style", "nav", "footer", "header", "aside", "form", "noscript")


def _extract_main_text(html: str, max_chars: int = 4000) -> str:
    """Cheap boilerplate stripping.  Returns visible text from the main content."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    # Prefer <article>, <main>, or largest <div>
    candidates = soup.find_all(["article", "main"]) or soup.find_all("div")
    if not candidates:
        text = soup.get_text(separator=" ", strip=True)
        return _normalise(text, max_chars)

    best = max(candidates, key=lambda el: len(el.get_text(strip=True)), default=None)
    if best is None:
        text = soup.get_text(separator=" ", strip=True)
        return _normalise(text, max_chars)
    text = best.get_text(separator=" ", strip=True)
    return _normalise(text, max_chars)


def _normalise(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " …"
    return text


def _extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "(untitled)"


# ── summarisation (LLM, lazy) ─────────────────────────────────────────

_SUMMARY_SYSTEM_PROMPT = (
    "You are a research assistant. Write a structured Markdown report with the "
    "sections `## Summary` (2-3 paragraphs), `## Key Points` (bullet list), and "
    "`## Sources`. Synthesise only what the provided excerpts contain — do not "
    "invent facts; if the excerpts are sparse, say so explicitly. Reply with "
    "only the report."
)

_SUMMARY_USER_TEMPLATE = """\
Topic: {topic}

Excerpts from web sources:
{excerpts}"""


def _summarise(cfg: Config, topic: str, excerpts: list[dict[str, str]]) -> str:
    if not is_available(cfg):
        return _deterministic_report(topic, excerpts)

    body = "\n\n".join(
        f"### Source {i+1}: {e['title']}\nURL: {e['url']}\n\n{e['text']}"
        for i, e in enumerate(excerpts)
        if e.get("text")
    )
    if not body:
        return _deterministic_report(topic, excerpts)

    # Cap excerpts so the prompt + reply fits the (low-RAM) n_ctx window.
    user_msg = _SUMMARY_USER_TEMPLATE.format(topic=topic, excerpts=body[:6000])
    try:
        with llm_session(cfg) as llm:
            if llm is None:
                return _deterministic_report(topic, excerpts)
            # Chat API applies the model's chat template (instruct model).
            report = llm.chat(
                [
                    {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=cfg.model.max_tokens,
                temperature=cfg.model.temperature,
            )
        return report or _deterministic_report(topic, excerpts)
    except Exception as exc:  # noqa: BLE001
        display.warn(f"LLM summarisation failed ({exc}); writing deterministic report.")
        return _deterministic_report(topic, excerpts)


def _deterministic_report(topic: str, excerpts: list[dict[str, str]]) -> str:
    lines = [f"# Research: {topic}", "",
             f"_Generated: {datetime.now().isoformat(timespec='seconds')}_", "",
             "## Summary", "",
             f"This report aggregates {len(excerpts)} web source(s) on **{topic}**.  "
             "The LLM was unavailable, so the content below is the raw extracted text "
             "stitched together for manual review.", ""]
    for i, e in enumerate(excerpts, 1):
        lines.append(f"## Source {i}: {e.get('title', '(untitled)')}")
        lines.append(f"URL: <{e.get('url', '')}>")
        lines.append("")
        lines.append(e.get("text", "(no body extracted)"))
        lines.append("")
    return "\n".join(lines)


# ── command entry ──────────────────────────────────────────────────────

def cmd_research(cfg: Config, args: Any) -> int:
    topic: str = args.topic
    if not topic:
        display.err("topic is required.")
        return 2

    display.header("Autonomous Research", topic)
    display.info(f"Searching the web for: {topic}")

    urls = _ddg_search(topic, cfg)
    if not urls:
        display.err("No search results found.")
        return 1

    display.ok(f"Found {len(urls)} candidate source(s).  Fetching full text…")

    sources: list[dict[str, str]] = []
    for i, url in enumerate(urls, 1):
        display.dim(f"  [{i}/{len(urls)}] {url}")
        html = _fetch(url, cfg)
        if not html:
            continue
        title = _extract_title(html)
        text = _extract_main_text(html)
        if not text:
            continue
        sources.append({"url": url, "title": title, "text": text})
        # Be polite to the source server.
        time.sleep(0.4)

    if not sources:
        display.err("Could not extract usable text from any source.")
        return 1

    display.ok(f"Extracted text from {len(sources)} source(s).")

    if args.no_llm:
        display.info("--no-llm set; writing deterministic report.")
        report = _deterministic_report(topic, sources)
    else:
        display.info("Summarising with LLM (loaded just for this step)…")
        report = _summarise(cfg, topic, sources)

    out_dir = storage.research_dir(cfg.research_dir, topic)
    report_path, sources_path = storage.save_research(out_dir, report, sources)
    display.console.print()
    display.ok(f"Report saved:      {report_path}")
    display.ok(f"Sources JSON:      {sources_path}")
    display.render_sources(sources)
    return 0


__all__ = ["cmd_research"]
