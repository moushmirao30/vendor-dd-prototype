"""
fetch.py — the only file in this project that touches the network.

EVERYTHING POLITE LIVES HERE. Isolating network access in one small module means
the "did we scrape responsibly?" question has exactly one file to audit, and the
rest of the project can be tested without a network connection at all.

Four guarantees this module makes:
  1. robots.txt is checked before every request; a disallowed URL is never fetched.
  2. Requests to the same domain are spaced by a configurable delay.
  3. The User-Agent identifies the project honestly. We never impersonate a browser.
  4. Every fetched page is written to disk. Later runs read the cache, so the whole
     workflow replays OFFLINE and a vendor changing their site cannot break a demo.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests


@dataclass
class FetchResult:
    """Everything we know about one attempt to read one public page."""

    url: str
    final_url: str = ""        # after redirects; may differ from url
    status: int = 0            # HTTP status, or 0 if the request never completed
    ok: bool = False
    html: str = ""
    from_cache: bool = False
    robots_allowed: bool = True
    robots_note: str = ""      # WHY robots allowed or refused - never just a boolean
    error: str = ""
    content_sha256: str = ""
    cache_path: str = ""


@dataclass
class RobotsPolicy:
    """
    One domain's robots.txt, plus a record of how we obtained it.

    WHY THIS IS NOT JUST A BOOLEAN — a real failure from 2026-08-10:
    the first live run reported "disallowed by robots.txt" for every
    about.gitlab.com page. GitLab's robots.txt actually permits all of them; it
    disallows only /search/ and /api/. The real cause was that Python's
    `RobotFileParser.read()` fetches robots.txt with urllib's own user agent,
    GitLab's CDN answered 403, and RobotFileParser treats 401/403 on robots.txt
    as "disallow everything". Four legitimate sources were dropped with a
    message that blamed the vendor.

    RFC 9309 (the robots.txt standard) is clearer than Python's stdlib:
      * 2xx                      -> parse and apply the rules
      * 4xx other than 429       -> "unavailable"; the crawler MAY access anything
      * 429 and 5xx              -> "unreachable"; assume complete disallow
    We follow the RFC, fetch robots.txt with OUR OWN honest user agent, and
    record which branch was taken so a reviewer can see the reasoning.

    We never add browser-impersonating headers. If a site refuses our honest
    user agent, that is recorded as a finding for manual review - not something
    to work around. Bypassing access restrictions is out of scope by the brief.
    """

    parser: RobotFileParser | None
    status: int
    note: str
    default_allow: bool

    def allows(self, url: str, user_agent: str) -> bool:
        if self.parser is not None:
            return self.parser.can_fetch(user_agent, url)
        return self.default_allow


def url_key(url: str) -> str:
    """Stable, filename-safe key for a URL. Used as the cache filename."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


class PageFetcher:
    """
    Cache-first, robots-respecting page fetcher.

    Usage:
        fetcher = PageFetcher(settings, project_root)
        result = fetcher.get("https://linear.app/security")
    """

    def __init__(self, settings: dict, root: Path):
        f = settings["fetch"]
        self.user_agent: str = f["user_agent"]
        self.delay: float = float(f["delay_seconds_per_domain"])
        self.timeout: int = int(f["timeout_seconds"])
        self.respect_robots: bool = bool(f["respect_robots_txt"])
        self.follow_redirects: bool = bool(f.get("follow_redirects", True))

        c = settings["cache"]
        self.cache_enabled: bool = bool(c["enabled"])
        self.reuse_existing: bool = bool(c["reuse_existing"])
        self.cache_dir: Path = root / c["dir"]
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._last_request_at: dict[str, float] = {}   # domain -> monotonic timestamp
        self._robots: dict[str, RobotFileParser | None] = {}  # domain -> parser

    # -- politeness ---------------------------------------------------------

    def _wait_turn(self, domain: str) -> None:
        """Sleep so that consecutive requests to one domain are `delay` apart."""
        last = self._last_request_at.get(domain)
        if last is not None:
            remaining = self.delay - (time.monotonic() - last)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at[domain] = time.monotonic()

    def _load_robots(self, domain: str) -> RobotsPolicy:
        """Fetch and interpret one domain's robots.txt, per RFC 9309."""
        try:
            response = requests.get(
                f"{domain}/robots.txt",
                headers={"User-Agent": self.user_agent},   # our honest UA, not urllib's
                timeout=self.timeout,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            return RobotsPolicy(
                None, 0,
                f"robots.txt unreachable ({type(exc).__name__}); "
                "RFC 9309 says assume complete disallow",
                default_allow=False,
            )

        code = response.status_code

        if 200 <= code < 300:
            parser = RobotFileParser()
            parser.parse(response.text.splitlines())
            return RobotsPolicy(parser, code, "robots.txt read and applied",
                                default_allow=True)

        if code == 429 or 500 <= code < 600:
            return RobotsPolicy(
                None, code,
                f"robots.txt unreachable (HTTP {code}); RFC 9309 says assume disallow",
                default_allow=False,
            )

        # Any other 4xx, including the 403 that a CDN returns to unknown agents.
        return RobotsPolicy(
            None, code,
            f"no usable robots.txt (HTTP {code}); RFC 9309 treats this as unrestricted",
            default_allow=True,
        )

    def robots_policy(self, url: str) -> RobotsPolicy:
        """Cached per-domain robots policy."""
        parts = urlparse(url)
        domain = f"{parts.scheme}://{parts.netloc}"
        if domain not in self._robots:
            self._robots[domain] = self._load_robots(domain)
        return self._robots[domain]

    def robots_allows(self, url: str) -> tuple[bool, str]:
        """Returns (allowed, human-readable reason). Never a bare boolean."""
        if not self.respect_robots:
            return True, "robots.txt checking disabled in settings.yaml"
        policy = self.robots_policy(url)
        allowed = policy.allows(url, self.user_agent)
        verdict = "allowed" if allowed else "DISALLOWED by an explicit rule"
        return allowed, f"{verdict} - {policy.note}"

    # -- cache --------------------------------------------------------------

    # Bumped whenever a fetch-layer change makes existing cached pages wrong.
    # v1 -> v2: cached pages fetched before the encoding fix contain mojibake.
    CACHE_VERSION = "v2"

    def _cache_file(self, url: str) -> Path:
        return self.cache_dir / f"{self.CACHE_VERSION}_{url_key(url)}.html"

    def cached(self, url: str) -> FetchResult | None:
        """Return the cached page for this URL, or None."""
        path = self._cache_file(url)
        if not (self.cache_enabled and self.reuse_existing and path.exists()):
            return None
        html = path.read_text(encoding="utf-8", errors="replace")
        return FetchResult(
            url=url, final_url=url, status=200, ok=True, html=html, from_cache=True,
            content_sha256=hashlib.sha256(html.encode("utf-8")).hexdigest(),
            cache_path=str(path),
        )

    # -- the one public method ---------------------------------------------

    def get(self, url: str) -> FetchResult:
        """Fetch one page. Cache first, then robots, then network."""
        hit = self.cached(url)
        if hit is not None:
            return hit

        allowed, reason = self.robots_allows(url)
        if not allowed:
            return FetchResult(url=url, robots_allowed=False, ok=False,
                               robots_note=reason, error=f"not fetched: {reason}")

        self._wait_turn(urlparse(url).netloc)

        try:
            response = requests.get(
                url,
                headers={"User-Agent": self.user_agent,
                         "Accept": "text/html,application/xhtml+xml"},
                timeout=self.timeout,
                allow_redirects=self.follow_redirects,
            )
        except requests.RequestException as exc:
            return FetchResult(url=url, ok=False, error=f"{type(exc).__name__}: {exc}")

        # ---- character encoding -------------------------------------------
        # When a server sends `Content-Type: text/html` with NO charset, requests
        # falls back to ISO-8859-1 (an old HTTP/1.1 rule). Almost every modern
        # page is UTF-8, so that fallback turns a curly quote into mojibake.
        # GitLab's privacy page arrived as: 'the "U.S. State Privacy Rights"
        # section' -> 'the âU.S. State Privacy Rightsâ section'.
        # In a project whose output is verbatim evidence snippets, corrupted
        # quotation marks are a correctness bug, not a cosmetic one.
        if not response.encoding or response.encoding.lower() in (
            "iso-8859-1", "latin-1", "latin1", "ascii"
        ):
            detected = response.apparent_encoding
            if detected:
                response.encoding = detected

        result = FetchResult(
            url=url,
            final_url=response.url,
            status=response.status_code,
            ok=response.ok,
            html=response.text if response.ok else "",
            robots_note=reason,
            content_sha256=hashlib.sha256(response.text.encode("utf-8")).hexdigest(),
        )

        if result.ok and self.cache_enabled:
            path = self._cache_file(url)
            path.write_text(result.html, encoding="utf-8")
            result.cache_path = str(path)

        return result
