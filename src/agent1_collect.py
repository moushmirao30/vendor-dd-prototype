"""
agent1_collect.py — AGENT 1 of 3: Source Collection.

ITS ONE JOB: given a vendor, decide which public URLs are worth reading, confirm
they exist, and store them as SourceRecords. It does not interpret anything.

THE HYBRID DESIGN, AND WHY
--------------------------
Three options were considered:
  (a) a hand-curated URL list only  -> honest, but the "agent" does no work
  (b) pure automatic discovery      -> impressive, but silently misses vendors
                                       like GitHub whose trust content is not at
                                       a guessable path
  (c) hybrid: guess, verify, fall back  <- chosen

Agent 1 builds candidate URLs from the pattern list in config/vendors.yaml,
keeps the candidates that actually return HTTP 200, and falls back to the
manually curated seed URL for any page type it failed to discover. Every URL is
recorded with the HTTP status it returned and whether it came from discovery or
from the seed list, so the reviewer can see exactly how each source was found.

There is NO crawling and NO link-following. Each candidate is one request.
That is a deliberate scope boundary, not a limitation of effort.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .fetch import PageFetcher, FetchResult
from .parse import main_text, page_title
from .schema import SourceRecord, today


@dataclass
class CollectionStep:
    """One line of the audit trail shown in the 'Agent steps' tab of the UI."""

    action: str          # "probe" | "seed-fallback" | "skip"
    source_type: str
    url: str
    status: int
    outcome: str


def base_url(vendor: dict) -> str:
    """
    Derive the vendor's root URL from its `product` seed.

    Example: https://about.gitlab.com/  ->  https://about.gitlab.com
             https://sentry.io/welcome/ ->  https://sentry.io
    """
    seed = vendor["seeds"].get("product") or next(iter(vendor["seeds"].values()))
    parts = urlparse(seed)
    return f"{parts.scheme}://{parts.netloc}"


def candidate_urls(vendor: dict, patterns: dict[str, list[str]]) -> dict[str, list[str]]:
    """Build the ordered list of URLs to try for each page type."""
    root = base_url(vendor)
    return {stype: [urljoin(root + "/", p.lstrip("/")) for p in paths]
            for stype, paths in patterns.items()}


def collect_for_vendor(
    vendor: dict,
    patterns: dict[str, list[str]],
    fetcher: PageFetcher,
    max_pages: int = 10,
    max_requests: int = 20,
) -> tuple[list[SourceRecord], list[CollectionStep]]:
    """
    Collect every public page for one vendor.

    `max_pages`    caps how many pages we KEEP.
    `max_requests` caps how many requests we MAKE - a separate, stricter limit.

    WHY BOTH: the first live run on 2026-08-10 made 25 requests to collect 2
    pages, because a vendor where nothing resolves burns the full candidate list.
    Capping only successes means the politest outcome (everything found on the
    first try) makes the fewest requests and the rudest outcome makes the most.
    That is backwards, so requests are capped directly.

    Returns (records, steps). `steps` is the human-readable audit trail; it is
    what makes this agent explainable to a non-technical reviewer rather than a
    black box that "found some pages".
    """
    records: list[SourceRecord] = []
    steps: list[CollectionStep] = []
    resolved: dict[str, FetchResult] = {}
    requests_made = 0

    def outcome_of(result: FetchResult) -> str:
        if result.ok:
            return "found"
        if not result.robots_allowed:
            return result.robots_note or "disallowed by robots.txt"
        return result.error or f"HTTP {result.status}"

    candidates = candidate_urls(vendor, patterns)

    # --- pass 1: try to discover each page type from URL patterns -----------
    for stype, urls in candidates.items():
        if stype in resolved:
            continue
        for url in urls:
            if len(resolved) >= max_pages or requests_made >= max_requests:
                break
            result = fetcher.get(url)
            requests_made += 0 if result.from_cache else 1
            steps.append(CollectionStep(action="probe", source_type=stype, url=url,
                                        status=result.status, outcome=outcome_of(result)))
            if result.ok:
                resolved[stype] = result
                break  # first working candidate wins; do not probe the rest

    # --- pass 2: fall back to the curated seed for anything not discovered ---
    # Seeds are tried even if the request budget is spent: they are the URLs a
    # human already verified, so they are the most valuable single request left.
    for stype, seed_url in vendor["seeds"].items():
        if stype in resolved or len(resolved) >= max_pages:
            continue
        result = fetcher.get(seed_url)
        requests_made += 0 if result.from_cache else 1
        steps.append(CollectionStep(action="seed-fallback", source_type=stype,
                                    url=seed_url, status=result.status,
                                    outcome=outcome_of(result)))
        if result.ok:
            resolved[stype] = result

    # --- build the corpus rows ---------------------------------------------
    verified = vendor.get("verified", [])
    for stype, result in resolved.items():
        text, extractor = main_text(result.html)
        records.append(SourceRecord(
            vendor_name=vendor["name"],
            vendor_slug=vendor["slug"],
            source_url=result.final_url or result.url,
            source_type=stype,
            page_title=page_title(result.html),
            collected_text=text,
            date_collected=today(),
            tags=[stype] + (["human-verified"] if stype in verified else []),
            evidence_note=(
                f"{stype} page for {vendor['name']}; "
                f"{len(text)} characters of main content; "
                f"{'served from cache' if result.from_cache else 'fetched live'}; "
                f"text via {extractor}"
            ),
            http_status=result.status,
            fetch_ok=result.ok,
            raw_html_path=result.cache_path,
            content_sha256=result.content_sha256,
            robots_allowed=result.robots_allowed,
            text_extractor=extractor,
        ))

    # Page types we wanted but never resolved. Recorded explicitly so the brief
    # can say "no privacy page found" rather than silently omitting it.
    for stype in vendor["seeds"]:
        if stype not in resolved:
            steps.append(CollectionStep(
                action="skip", source_type=stype, url=vendor["seeds"][stype],
                status=0, outcome="NOT COLLECTED - flag for manual follow-up",
            ))

    return records, steps


def save_corpus(records: list[SourceRecord], out_dir: Path, slug: str) -> Path:
    """Write one vendor's corpus as JSON (canonical store). CSV export is separate."""
    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.json"
    path.write_text(
        json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def save_run(steps: list[CollectionStep], out_dir: Path, slug: str, ran_on: str) -> Path:
    """
    Write the audit trail alongside the corpus.

    WHY THIS EXISTS: the project brief requires the interface to let a reviewer
    "run OR REPLAY the workflow" and "see each agent step". Keeping the steps
    only in Streamlit's session state meant that refreshing the browser erased
    the entire audit trail, and the app looked as though it had never been run
    even though the corpus was sitting on disk. Persisting the run makes replay
    real: a reviewer can open the app tomorrow and see exactly what happened.
    """
    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}_run.json"
    path.write_text(
        json.dumps({"vendor_slug": slug, "ran_on": ran_on,
                    "steps": [s.__dict__ for s in steps]},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def load_previous_run(corpus_dir: Path, slug: str) -> dict | None:
    """Load a saved corpus + audit trail, so the UI can replay without refetching."""
    import json

    corpus_path = corpus_dir / f"{slug}.json"
    if not corpus_path.exists():
        return None

    run_path = corpus_dir / f"{slug}_run.json"
    run = json.loads(run_path.read_text(encoding="utf-8")) if run_path.exists() else {}

    return {
        "records": json.loads(corpus_path.read_text(encoding="utf-8")),
        "steps": run.get("steps", []),
        "ran_on": run.get("ran_on", "unknown"),
        "corpus_path": str(corpus_path.name),
        "from_disk": True,
    }
