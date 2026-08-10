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


def test_the_human_curated_seed_beats_a_guessed_url():
    """
    THE ZENDESK REGRESSION. Discovery used to run first and take the first HTTP
    200. For GitLab's `docs` that meant /support answered 200 and redirected to
    a single Zendesk help article, which the agent then preferred over
    docs.gitlab.com - the vendor's entire documentation site. A 200 means the
    URL exists, not that it is the right page.
    """
    fetcher = FakeFetcher(works={"https://docs.gitlab.com/",
                                 "https://about.gitlab.com/support"})
    records, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher)

    docs = next(r for r in records if r.source_type == "docs")
    assert docs.source_url == "https://docs.gitlab.com/", "the curated seed must win"
    assert any(s.action == "curated-seed" and s.outcome == "found" for s in steps)
    assert "https://about.gitlab.com/support" not in fetcher.calls, (
        "no reason to probe once the curated URL worked"
    )


def test_discovery_fills_gaps_the_seed_list_does_not_cover():
    """GitLab has no `terms` seed; the agent must find it unaided."""
    fetcher = FakeFetcher(works={"https://about.gitlab.com/terms"})
    records, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher, max_requests=40)
    terms = next(r for r in records if r.source_type == "terms")
    assert terms.source_url == "https://about.gitlab.com/terms"
    assert any(s.action == "discovered" and s.outcome == "found" for s in steps)


def test_first_working_candidate_wins_and_the_rest_are_not_probed():
    fetcher = FakeFetcher(works={"https://about.gitlab.com/terms"})
    collect_for_vendor(GITLAB, PATTERNS, fetcher, max_requests=40)
    assert "https://about.gitlab.com/terms-of-service" not in fetcher.calls, (
        "probing must stop at the first success - this is a research tool, not a crawler"
    )


def test_a_redirect_is_reported_not_hidden():
    """A 200 that lands somewhere else is a finding the reviewer must see."""
    class RedirectingFetcher(FakeFetcher):
        def get(self, url):
            r = super().get(url)
            if r.ok:
                r.final_url = "https://support.gitlab.com/hc/en-us/articles/116264"
            return r

    fetcher = RedirectingFetcher(works={"https://docs.gitlab.com/"})
    _, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher)
    assert any("REDIRECTED" in s.outcome for s in steps)


def test_seeds_reach_hosts_no_url_pattern_could_ever_guess():
    """
    GitLab's docs live on docs.gitlab.com, a different host from about.gitlab.com,
    so no URL pattern can reach them. This is why option (b), pure auto-discovery,
    was rejected in the design.
    """
    fetcher = FakeFetcher(works={"https://docs.gitlab.com/"})
    records, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher)
    assert any(s.action == "curated-seed" and s.outcome == "found" for s in steps)
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


def test_a_saved_run_can_be_replayed_without_refetching(tmp_path):
    """
    The brief requires the interface to "run OR REPLAY the workflow". Keeping
    results only in Streamlit session state meant a browser refresh erased the
    entire audit trail while the corpus sat on disk, so the app looked as though
    it had never been run.
    """
    from src.agent1_collect import save_corpus, save_run, load_previous_run

    fetcher = FakeFetcher(works={"https://about.gitlab.com/security"})
    records, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher)

    save_corpus(records, tmp_path, "gitlab")
    save_run(steps, tmp_path, "gitlab", ran_on="2026-08-10T16:00:00")

    replayed = load_previous_run(tmp_path, "gitlab")
    assert replayed is not None and replayed["from_disk"] is True
    assert len(replayed["records"]) == len(records)
    assert len(replayed["steps"]) == len(steps), "the audit trail must survive a refresh"
    assert replayed["ran_on"] == "2026-08-10T16:00:00"


def test_replay_returns_none_for_a_vendor_never_collected(tmp_path):
    from src.agent1_collect import load_previous_run
    assert load_previous_run(tmp_path, "never-run") is None


def test_the_request_budget_announces_itself_instead_of_silently_dropping_pages():
    """
    Page types are probed in config order, so a budget spent on earlier failures
    would make the last ones disappear with no trace. A reviewer reading the
    audit trail must be able to tell "not found" apart from "never attempted".
    """
    fetcher = FakeFetcher(works=set())
    _, steps = collect_for_vendor(GITLAB, PATTERNS, fetcher, max_requests=8)
    stops = [s for s in steps if s.action == "budget-stop"]
    assert stops, "hitting the request limit must be recorded"
    assert "not attempted" in stops[0].outcome
