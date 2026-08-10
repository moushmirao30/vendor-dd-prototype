"""
test_agent1.py — proves the Source Collection Agent behaves, WITHOUT touching
the network. A fake fetcher stands in for PageFetcher and serves the five HTML
fixtures, so this suite runs on a plane.

What it guards:
  * discovery is tried first, seeds are used only as a fallback
  * a page type that resolves nowhere is recorded as NOT COLLECTED, not dropped
  * every collected page produces an auditable corpus row
  * robots.txt disallow is honoured
"""

from pathlib import Path
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.agent1_collect import collect_for_vendor, base_url, candidate_urls  # noqa: E402
from src.fetch import FetchResult  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config" / "vendors.yaml").read_text(encoding="utf-8"))
PATTERNS = CFG["url_patterns"]
GITLAB = next(v for v in CFG["vendors"] if v["slug"] == "gitlab")
FIXTURE = (ROOT / "tests" / "fixtures" / "linear_style.html").read_text(encoding="utf-8")


class FakeFetcher:
    """Serves a fixture for URLs in `works`, 404s everything else. Records calls."""

    def __init__(self, works: set[str], disallowed: set[str] | None = None):
        self.works = works
        self.disallowed = disallowed or set()
        self.calls: list[str] = []

    def get(self, url: str) -> FetchResult:
        self.calls.append(url)
        if url in self.disallowed:
            return FetchResult(url=url, ok=False, robots_allowed=False,
                               error="disallowed by robots.txt")
        if url in self.works:
            return FetchResult(url=url, final_url=url, status=200, ok=True,
                               html=FIXTURE, content_sha256="abc123",
                               cache_path="data/cache/html/abc123.html")
        return FetchResult(url=url, status=404, ok=False)


def test_base_url_is_derived_from_the_product_seed():
    assert base_url(GITLAB) == "https://about.gitlab.com"


def test_candidates_are_built_from_the_pattern_list():
    cands = candidate_urls(GITLAB, PATTERNS)
    assert "https://about.gitlab.com/security" in cands["security"]
    assert "https://about.gitlab.com/trust-center" in cands["security"]


def test_discovery_is_preferred_over_the_seed_list():
    fetcher = FakeFetcher(works={"https://about.gitlab.com/security"})
    records, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher)

    security = next(r for r in records if r.source_type == "security")
    assert security.source_url == "https://about.gitlab.com/security"
    assert any(s.action == "probe" and s.outcome == "found" for s in steps)


def test_first_working_candidate_wins_and_the_rest_are_not_probed():
    fetcher = FakeFetcher(works={"https://about.gitlab.com/security"})
    collect_for_vendor(GITLAB, PATTERNS, fetcher)
    assert "https://about.gitlab.com/trust-center" not in fetcher.calls, (
        "probing must stop at the first success - this is a research tool, not a crawler"
    )


def test_seed_is_used_when_discovery_finds_nothing():
    """
    GitLab's docs live on docs.gitlab.com, a different host from about.gitlab.com,
    so no URL pattern can ever reach them. This is exactly the case the seed
    fallback exists for - and the reason option (b), pure auto-discovery, was
    rejected in the design.
    """
    fetcher = FakeFetcher(works={"https://docs.gitlab.com/"})
    records, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher)
    assert any(s.action == "seed-fallback" and s.outcome == "found" for s in steps)
    assert any(r.source_url == "https://docs.gitlab.com/" for r in records)


def test_unresolvable_page_types_are_flagged_not_dropped():
    fetcher = FakeFetcher(works=set())          # nothing resolves at all
    records, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher)
    assert records == []
    skipped = [s for s in steps if s.action == "skip"]
    assert len(skipped) == len(GITLAB["seeds"]), "every missing page type must be reported"
    assert all("manual follow-up" in s.outcome for s in skipped)


def test_robots_disallow_is_honoured_and_recorded():
    url = "https://about.gitlab.com/security"
    fetcher = FakeFetcher(works={url}, disallowed={url})
    _, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher)
    assert any("robots.txt" in s.outcome for s in steps)


def test_every_collected_page_yields_an_auditable_corpus_row():
    fetcher = FakeFetcher(works={"https://about.gitlab.com/security"})
    records, _ = collect_for_vendor(GITLAB, PATTERNS, fetcher)
    r = records[0]
    assert r.vendor_name == "GitLab" and r.fetch_ok and r.http_status == 200
    assert r.content_sha256 and r.raw_html_path and r.date_collected
    assert "SOC 2" in r.collected_text or "Service Organization" in r.collected_text


def test_page_cap_is_respected():
    all_urls = {u for urls in candidate_urls(GITLAB, PATTERNS).values() for u in urls}
    fetcher = FakeFetcher(works=all_urls)
    records, _ = collect_for_vendor(GITLAB, PATTERNS, fetcher, max_pages=2)
    assert len(records) <= 2
