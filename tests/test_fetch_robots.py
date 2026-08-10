"""
test_fetch_robots.py — regression tests for the robots.txt handling.

THE BUG THESE EXIST FOR (found in the first live run, 2026-08-10):
Agent 1 reported "disallowed by robots.txt" for every about.gitlab.com page and
collected 2 of 6 sources. GitLab's robots.txt permits all of them - it disallows
only /search/ and /api/. The real cause was Python's RobotFileParser.read():
it fetches robots.txt with urllib's own user agent, GitLab's CDN answered 403,
and RobotFileParser treats 401/403 on robots.txt as "disallow everything".

Four legitimate public sources were dropped, with a message that blamed the
vendor for a defect in our own code. These tests make that impossible to repeat.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import fetch as fetch_mod  # noqa: E402
from src.fetch import PageFetcher  # noqa: E402

GITLAB_ROBOTS = """\
User-agent: *
Disallow: /search/
Disallow: /api/
Sitemap: https://about.gitlab.com/sitemap.xml
"""

SETTINGS = {
    "fetch": {"user_agent": "FQL-VendorDD-Prototype/0.1", "delay_seconds_per_domain": 0,
              "timeout_seconds": 5, "respect_robots_txt": True, "follow_redirects": True},
    "cache": {"enabled": False, "reuse_existing": False, "dir": "cache"},
}


class FakeResponse:
    def __init__(self, status: int, text: str = ""):
        self.status_code, self.text = status, text
        self.url = "https://about.gitlab.com/robots.txt"
        self.ok = 200 <= status < 300


@pytest.fixture
def fetcher(tmp_path):
    return PageFetcher(SETTINGS, tmp_path)


def patch_robots(monkeypatch, response, seen: dict | None = None):
    def fake_get(url, headers=None, timeout=None, allow_redirects=None):
        if seen is not None:
            seen["url"], seen["headers"] = url, headers
        return response
    monkeypatch.setattr(fetch_mod.requests, "get", fake_get)


def test_403_on_robots_txt_does_not_disallow_the_whole_site(fetcher, monkeypatch):
    """THE GITLAB REGRESSION. RFC 9309: a 4xx robots.txt means 'no restrictions'."""
    patch_robots(monkeypatch, FakeResponse(403))
    allowed, reason = fetcher.robots_allows("https://about.gitlab.com/security/")
    assert allowed is True, "a CDN blocking robots.txt is not a prohibition on the site"
    assert "403" in reason and "unrestricted" in reason


def test_robots_txt_is_requested_with_our_own_user_agent(fetcher, monkeypatch):
    """urllib sent 'Python-urllib/3.x', which is what got blocked. Use our UA."""
    seen: dict = {}
    patch_robots(monkeypatch, FakeResponse(200, GITLAB_ROBOTS), seen)
    fetcher.robots_allows("https://about.gitlab.com/security/")
    assert seen["url"] == "https://about.gitlab.com/robots.txt"
    assert seen["headers"]["User-Agent"] == SETTINGS["fetch"]["user_agent"]


def test_real_gitlab_rules_allow_security_and_block_search(fetcher, monkeypatch):
    patch_robots(monkeypatch, FakeResponse(200, GITLAB_ROBOTS))
    assert fetcher.robots_allows("https://about.gitlab.com/security/")[0] is True
    assert fetcher.robots_allows("https://about.gitlab.com/pricing/")[0] is True
    assert fetcher.robots_allows("https://about.gitlab.com/search/x")[0] is False
    assert fetcher.robots_allows("https://about.gitlab.com/api/v4")[0] is False


@pytest.mark.parametrize("status", [429, 500, 503])
def test_unreachable_robots_txt_is_treated_as_disallow(fetcher, monkeypatch, status):
    """RFC 9309: 429 and 5xx mean 'unreachable' - assume complete disallow."""
    patch_robots(monkeypatch, FakeResponse(status))
    allowed, reason = fetcher.robots_allows("https://about.gitlab.com/security/")
    assert allowed is False and "disallow" in reason.lower()


def test_network_failure_on_robots_txt_is_treated_as_disallow(fetcher, monkeypatch):
    def boom(*a, **k):
        raise fetch_mod.requests.RequestException("dns failure")
    monkeypatch.setattr(fetch_mod.requests, "get", boom)
    allowed, reason = fetcher.robots_allows("https://about.gitlab.com/security/")
    assert allowed is False and "unreachable" in reason


def test_every_refusal_explains_itself(fetcher, monkeypatch):
    """A bare 'disallowed by robots.txt' hid a bug for a whole run. Never again."""
    patch_robots(monkeypatch, FakeResponse(503))
    _, reason = fetcher.robots_allows("https://about.gitlab.com/security/")
    assert len(reason) > 30 and "503" in reason
