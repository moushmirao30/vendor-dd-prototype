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
    error: str = ""
    content_sha256: str = ""
    cache_path: str = ""


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

    def robots_allows(self, url: str) -> bool:
        """
        Ask the site's robots.txt whether our User-Agent may read this URL.

        If robots.txt cannot be reached we ALLOW. That is the convention robots
        parsers follow: an unreachable robots.txt is not a prohibition. This
        choice is written into docs/assumptions_limitations.md.
        """
        if not self.respect_robots:
            return True

        parts = urlparse(url)
        domain = f"{parts.scheme}://{parts.netloc}"

        if domain not in self._robots:
            parser = RobotFileParser()
            parser.set_url(f"{domain}/robots.txt")
            try:
                parser.read()
            except Exception:
                parser = None          # unreachable -> treat as no restrictions
            self._robots[domain] = parser

        parser = self._robots[domain]
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, url)

    # -- cache --------------------------------------------------------------

    def _cache_file(self, url: str) -> Path:
        return self.cache_dir / f"{url_key(url)}.html"

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

        if not self.robots_allows(url):
            return FetchResult(url=url, robots_allowed=False, ok=False,
                               error="disallowed by robots.txt")

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

        result = FetchResult(
            url=url,
            final_url=response.url,
            status=response.status_code,
            ok=response.ok,
            html=response.text if response.ok else "",
            content_sha256=hashlib.sha256(response.text.encode("utf-8")).hexdigest(),
        )

        if result.ok and self.cache_enabled:
            path = self._cache_file(url)
            path.write_text(result.html, encoding="utf-8")
            result.cache_path = str(path)

        return result
