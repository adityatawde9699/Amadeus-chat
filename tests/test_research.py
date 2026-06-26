"""Research: HTML extraction, DDG result parsing, deterministic report.

No network is touched — all HTML is provided as fixture strings.
"""
from __future__ import annotations

from amadeus.core.config import Config
from amadeus.modules import research


SAMPLE_PAGE = """
<html><head><title>  Rust Ownership  </title></head>
<body>
  <nav>menu menu menu</nav>
  <article>
    <h1>Ownership</h1>
    <p>Rust uses ownership and a borrow checker to guarantee memory safety
    without a garbage collector.</p>
  </article>
  <footer>copyright</footer>
  <script>var x = 1;</script>
</body></html>
"""


def test_extract_title():
    assert research._extract_title(SAMPLE_PAGE) == "Rust Ownership"


def test_extract_main_text_strips_noise():
    text = research._extract_main_text(SAMPLE_PAGE)
    assert "borrow checker" in text
    assert "menu" not in text
    assert "copyright" not in text
    assert "var x" not in text


def test_normalise_truncates():
    out = research._normalise("word " * 100, max_chars=20)
    assert len(out) <= 22 and out.endswith("…")


def test_ddg_search_parses_uddg_links():
    html = """
    <div>
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa">A</a>
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fb">B</a>
    </div>
    """
    cfg = Config()
    cfg.research.max_pages = 5

    def fake_fetch(url, c, **kw):
        return html

    orig = research._fetch
    research._fetch = fake_fetch
    try:
        urls = research._ddg_search("anything", cfg)
    finally:
        research._fetch = orig
    assert urls == ["https://example.com/a", "https://example.org/b"]


def test_deterministic_report_contains_sources():
    excerpts = [
        {"url": "http://a", "title": "A", "text": "alpha"},
        {"url": "http://b", "title": "B", "text": "beta"},
    ]
    report = research._deterministic_report("topic", excerpts)
    assert "# Research: topic" in report
    assert "alpha" in report and "beta" in report
    assert "http://a" in report
