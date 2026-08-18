"""
schema.py — the shape of every piece of data in this project, in one place.

WHY A SCHEMA FILE EXISTS
------------------------
Three agents hand data to each other. If each one invents its own dictionary
keys, the project rots by day 10 and the UI silently shows blank fields. These
dataclasses are the contract: Agent 1 produces SourceRecords, Agent 2 turns
SourceRecords into ExtractedFields, Agent 3 turns those into a VendorBrief.

Every field below either comes straight from the project brief or is justified
in a comment. Nothing is here "just in case".
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Literal

Confidence = Literal["High", "Medium", "Low", "NOT_FOUND"]
Status = Literal["FOUND", "PARTIAL", "NOT_FOUND"]


@dataclass
class SourceRecord:
    """
    One collected public page. This is a row of the vendor corpus.

    The first nine fields are the ones the project brief asks for by name.
    The five after them are additions — each earns its place by making the
    result auditable rather than merely present.
    """

    # --- required by the brief ---
    vendor_name: str
    source_url: str
    source_type: str            # security | privacy | pricing | docs | status | product | terms
    page_title: str
    collected_text: str         # cleaned main-content text
    date_collected: str         # ISO date, e.g. "2026-08-12"
    tags: list[str] = field(default_factory=list)
    evidence_note: str = ""     # one line: why this page was collected

    # --- additions, each with a reason ---
    vendor_slug: str = ""       # stable filename-safe key; vendor names contain spaces
    http_status: int = 0        # reviewer can see 404/403 instead of wondering why a field is empty
    fetch_ok: bool = False      # explicit success flag; an empty page is not the same as a failed fetch
    raw_html_path: str = ""     # proves the text came from the page and was not invented
    content_sha256: str = ""    # lets "replay" detect that a page changed since collection
    robots_allowed: bool = True # written evidence that access rules were respected
    text_extractor: str = ""    # which cleaner produced collected_text; see parse.main_text

    # --- content usability (added 2026-08-12, defect 23) ---
    # A page can return HTTP 200, pass robots, cache cleanly, and still contain
    # no readable text at all. Atlassian's Jira product page is 898 KB of HTML
    # that yields 52 characters and ZERO heading blocks, because the content is
    # rendered by JavaScript we deliberately do not run. Without these two
    # fields, every field sourced from that page becomes NOT_FOUND, and a
    # NOT_FOUND caused by our fetcher is indistinguishable from a vendor that
    # genuinely does not publish something. For a due-diligence tool that is the
    # worst available bug: it makes a false statement about a company.
    block_count: int = 0        # heading blocks the extractor will actually see
    content_usable: bool = True # False -> collected, but unusable as evidence

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExtractedField:
    """
    One answer inside a vendor brief.

    NOTE THE SHAPE: this is an object, not a string. `status` makes NOT_FOUND a
    first-class value rather than an empty cell, which is how the brief's
    "flag missing information instead of guessing" requirement is enforced
    structurally rather than by good intentions.
    """

    name: str
    label: str
    status: Status = "NOT_FOUND"
    value: str = ""                                  # short human-readable summary
    confidence: Confidence = "NOT_FOUND"
    evidence: list[dict] = field(default_factory=list)  # Evidence objects, as dicts

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VendorBrief:
    """
    The final first-pass research brief. Its fields map 1:1 to the bullet list
    in the project brief's "Expected Output" section — no more, no less.
    """

    vendor_name: str
    vendor_slug: str
    generated_on: str = ""
    vendor_overview: str = ""
    product_category: str = ""
    key_sources: list[str] = field(default_factory=list)
    fields: dict[str, dict] = field(default_factory=dict)   # name -> ExtractedField.to_dict()
    missing_or_unclear: list[str] = field(default_factory=list)
    review_flags: list[str] = field(default_factory=list)
    overall_confidence: Confidence = "NOT_FOUND"
    confidence_score: int = 0                                # 0-10, see docs/confidence_rules.md

    # COVERAGE TRAVELS WITH THE SCORE. ALWAYS. (defect 31, added 13 Aug 2026)
    #
    # `confidence_score` counts what was FOUND. It cannot count what was never
    # LOOKED AT. Measured on the real corpus: Postman scores 10/10 -> High with
    # four core fields resting on pages that returned no readable text at all,
    # and Sentry scores 10/10 -> High with every page read. Printed alone, those
    # two vendors are indistinguishable to an operations lead — which is exactly
    # the failure this project exists to report, reproduced by our own scoring.
    #
    # These three fields are on the dataclass rather than computed at render
    # time so that no exporter, template or UI panel can show the score without
    # them being available beside it.
    coverage_verified: int = 0        # core fields whose evidence carries no caveat
    coverage_total: int = 0           # core fields in total
    coverage_caveated: list[str] = field(default_factory=list)

    # Printed on every export. The brief requires the output to state plainly
    # that this is a first-pass aid and that final review stays manual.
    disclaimer: str = (
        "FIRST-PASS INTERNAL RESEARCH AID. Generated from public web pages only. "
        "This is not a vendor risk score, a security approval, or a procurement "
        "decision. Every field must be confirmed by a human reviewer before use."
    )

    def to_dict(self) -> dict:
        return asdict(self)


def today() -> str:
    """ISO date string used for `date_collected` everywhere."""
    return date.today().isoformat()
