"""
test_text_quality.py — guards the two content-integrity bugs found on 2026-08-10
when the first successful GitLab collection was inspected record by record.

BUG 1 - THE CLEANER SILENTLY DISCARDED THE EVIDENCE.
GitLab's security page produced 487 characters of `collected_text` out of 6,415
characters of visible text: 7.6%. Everything trafilatura threw away included
"GitLab maintains a SOC 2 Type 2 report..." under an <h3>SOC Certification</h3>
heading. Measured ratios on the other six pages were 17%-79%, so 7.6% is an
outlier, not normal cleaning.

BUG 2 - MOJIBAKE.
Servers that omit `charset` make requests fall back to ISO-8859-1, so UTF-8
curly quotes arrive as garbage. GitLab's privacy page gave
'the "U.S. State Privacy Rights" section' as 'the âU.S. State Privacy Rightsâ'.
For a project whose deliverable is verbatim evidence snippets, that is a
correctness bug.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import fetch as fetch_mod  # noqa: E402
from src.fetch import PageFetcher  # noqa: E402
from src.parse import main_text, visible_text  # noqa: E402

# A page shaped like GitLab's: real evidence buried in framework-generated
# component markup that content cleaners routinely discard as boilerplate.
VUE_STYLE_PAGE = """<html><body>
<h1>We're committed to Information Security</h1>
<p>It's our mission to be the leading example in security and transparency.</p>
<div class="card" data-v-cec41b51><h3>SOC Certification</h3>
<div class="card__description" data-v-64ad2128><span><p>GitLab maintains a SOC 2 Type 2
report for the Security, Confidentiality and Availability Trust Services Criteria for
GitLab.com. GitLab maintains a SOC 2 Type 2 report for GitLab Dedicated.</p></span></div></div>
<div class="card" data-v-cec41b51><h3>ISO Certification</h3>
<div class="card__description"><span><p>GitLab maintains ISO/IEC 27001:2022 certification
for the information security management system supporting GitLab.com and GitLab
Dedicated, covering the full scope of the SaaS subscriptions offered.</p></span></div></div>
</body></html>"""


def test_cleaner_never_silently_drops_the_evidence():
    """THE GITLAB SECURITY-PAGE REGRESSION."""
    text, extractor = main_text(VUE_STYLE_PAGE)
    full = visible_text(VUE_STYLE_PAGE)

    assert len(text) / len(full) >= 0.15, (
        f"kept only {len(text) / len(full):.0%} of the page - "
        f"this is how the SOC 2 evidence was lost"
    )
    assert "SOC 2 Type 2" in text
    assert "ISO/IEC 27001" in text
    assert extractor, "the corpus must record which cleaner produced the text"


def test_main_text_reports_which_extractor_it_used():
    _, extractor = main_text("<html><body><p>Short page.</p></body></html>")
    assert isinstance(extractor, str) and extractor


def test_visible_text_strips_scripts_and_styles():
    html = "<html><body><script>var x=1;</script><style>p{}</style><p>Real text</p></body></html>"
    out = visible_text(html)
    assert "Real text" in out and "var x" not in out


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------
SETTINGS = {
    "fetch": {"user_agent": "FQL-VendorDD-Prototype/0.1", "delay_seconds_per_domain": 0,
              "timeout_seconds": 5, "respect_robots_txt": False, "follow_redirects": True},
    "cache": {"enabled": False, "reuse_existing": False, "dir": "cache"},
}


class UTF8PageServedWithoutCharset:
    """Mimics a server sending UTF-8 bytes with no charset declared."""

    def __init__(self):
        self._bytes = '<html><body><p>the “U.S. State Privacy Rights” section</p></body></html>'.encode("utf-8")
        self.status_code, self.ok, self.url = 200, True, "https://example.com/privacy"
        self.encoding = "ISO-8859-1"          # what requests assumes with no charset
        self.apparent_encoding = "utf-8"      # what the bytes actually are

    @property
    def text(self) -> str:
        return self._bytes.decode(self.encoding, errors="replace")


def test_utf8_page_without_a_charset_header_is_not_mangled(tmp_path, monkeypatch):
    """THE PRIVACY-PAGE REGRESSION: curly quotes must survive the fetch."""
    monkeypatch.setattr(fetch_mod.requests, "get",
                        lambda *a, **k: UTF8PageServedWithoutCharset())
    result = PageFetcher(SETTINGS, tmp_path).get("https://example.com/privacy")

    assert "“U.S. State Privacy Rights”" in result.html
    assert "â" not in result.html, "mojibake - evidence snippets would be corrupted"


def test_cache_key_is_versioned_so_bad_cached_pages_are_not_reused(tmp_path):
    """Pages cached before the encoding fix hold mojibake and must not be served."""
    fetcher = PageFetcher({**SETTINGS, "cache": {"enabled": True, "reuse_existing": True,
                                                 "dir": "cache"}}, tmp_path)
    assert fetcher._cache_file("https://x.test/a").name.startswith(f"{fetcher.CACHE_VERSION}_")
