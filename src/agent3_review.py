"""
agent3_review.py — AGENT 3 of 3: Brief Review.

ITS ONE JOB, in the project brief's words: *"checks whether the extracted
information is usable, highlights missing areas, and prepares a concise vendor
brief."*

First Quadrant Labs narrowed that in writing on 13 August 2026, and the narrowing
is the specification:

    "For Agent 3, focus on review and synthesis rather than introducing another
     complex intelligence layer. It should verify evidence coverage, identify
     missing categories, highlight conflicts or weak evidence, and prepare the
     final brief."

Four verbs. Nothing else belongs in this file.

WHAT THIS AGENT DOES NOT DO, AND WHY THAT IS THE POINT
------------------------------------------------------
It does not re-read pages — Agent 2 already did, and re-parsing would let the two
disagree. It does not re-rank evidence. It does not fetch anything. It does not
score risk, approve a vendor, or make a procurement decision; the brief forbids
all three and `VendorBrief.disclaimer` says so on every export.

It reads Agent 2's output and Agent 1's audit trail, and it writes down what a
careful reviewer would notice. Every judgement it makes comes from
`src/review_rules.py`, which `tools/verify_corpus.py` imports too — so the
checker that gates a commit and the brief that reaches a reviewer can never
drift apart. That shared module is the whole architectural idea here.

THE ONE NUMBER TO READ TWICE
----------------------------
`confidence_score` counts what was FOUND. `coverage` counts what was actually
CHECKED. Postman scores 10/10 with four core fields resting on pages that
returned no readable text; Sentry scores 10/10 with every page read. The brief
prints both, always together, because the score alone cannot tell them apart.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .review_rules import (claim_not_in_matched_sentence, conflicting_values,
                           confidence, extraction_quality, field_coverage,
                           gated_evidence, is_caveated, off_home_evidence,
                           real_evidence, terms_not_visible, unread_home_page,
                           vendor_score)
from .schema import VendorBrief, today


@dataclass
class ReviewStep:
    """One line of Agent 3's audit trail, shown beside Agents 1 and 2 in the UI."""

    action: str        # coverage | missing | weak-evidence | conflict | overview | assemble
    field_name: str
    detail: str


# ---------------------------------------------------------------------------
# The two brief fields that are not extracted from any page
# ---------------------------------------------------------------------------

def product_category(vendor: dict, category: str) -> str:
    """
    The brief's Expected Output asks for a product or service category.

    It is not one of the eight extracted fields and it never could be: a category
    is a judgement about a market, not a sentence on a vendor's website. It comes
    from `config/vendors.yaml`, where a human wrote it down, and the brief labels
    it as curated rather than extracted so no reviewer mistakes it for evidence.
    """
    raw = vendor.get("category") or category or ""
    # vendors.yaml stores it as a slug (`developer_productivity_tools`) because
    # it is also used as a key. The brief is read by a non-technical operations
    # lead, so print it as words.
    return raw.replace("_", " ").replace("-", " ").strip() or "(not categorised)"


def vendor_overview(records: list[dict]) -> tuple[str, str, bool]:
    """
    A one-line overview, QUOTED, never written. Returns (text, url, body_was_readable).

    THE FIRST ATTEMPT AT THIS WAS WRONG AND THE CORPUS SAID SO IMMEDIATELY.
    It took the first complete sentence between 60 and 320 characters from the
    product page body. Three of six results were unusable: GitLab got a run-on
    navigation fragment, JetBrains got "in Java and Kotlin Natively integrated AI
    Latest AI models", and Linear got a CHANGELOG ENTRY — "Render UI before
    vehicle_state sync when minimum required state is present". Requiring the
    vendor's own name in the sentence helped and still returned a wall of
    customer logos for Sentry.

    The reason is structural, and it is the same finding as everywhere else in
    this project: a marketing product page is the least structured page a vendor
    publishes. Across the whole corpus the product page contributed exactly ONE
    of 122 evidence blocks. Trying to mine prose out of it was always going to
    produce something that reads like an overview and is not one.

    So the overview is the product page's `<title>` — already collected into
    `SourceRecord.page_title`, written by the vendor to describe itself in one
    line, and structured rather than mined:

        gitlab     "Finally, AI for the entire software lifecycle."
        linear     "Linear - The system for product development"
        postman    "Postman API Platform - Build, Test & Manage"
        sentry     "Application Performance Monitoring & Error Tracking Software | Sentry"
        jetbrains  "The Leading IDE for Professional Java and Kotlin Development"

    AND IT SURVIVES THE THING THAT BREAKS EVERYTHING ELSE. A `<title>` lives in
    the HTML head and is served before any JavaScript runs, so Atlassian — whose
    product page body yields 52 readable characters from 898 KB — still returns
    "Jira | Project Management for the AI Era | Atlassian". The third return
    value says whether the body was readable, so the brief can mark an overview
    taken from a page we could not otherwise read.
    """
    product = next((r for r in records if r.get("source_type") == "product"), None)
    if not product:
        return "", "", False
    return (product.get("page_title", "").strip(),
            product.get("source_url", ""),
            product.get("content_usable") is not False)


# ---------------------------------------------------------------------------
# The review itself
# ---------------------------------------------------------------------------

def review_vendor(
    vendor: dict,
    fields: list[dict],
    records: list[dict],
    collection_steps: list[dict],
    field_dictionary: dict,
    settings: dict,
    category: str = "",
) -> tuple[VendorBrief, list[ReviewStep]]:
    """
    Turn Agent 2's fields into a reviewed VendorBrief.

    Everything it needs is already on disk, so this replays offline exactly like
    the other two agents. Returns (brief, steps); `steps` is the audit trail the
    UI prints beside Agent 1's and Agent 2's.
    """
    conf = settings["confidence"]
    core = conf["core_fields"]
    min_claim = settings["extraction"]["min_body_chars_for_high"]

    unusable = [r["source_type"] for r in records if r.get("content_usable") is False]
    never_collected = [s["source_type"] for s in collection_steps
                       if s.get("action") == "skip"]

    steps: list[ReviewStep] = []
    missing: list[str] = []
    flags: list[str] = []
    reviewed: dict[str, dict] = {}

    # --- verb 1: verify evidence coverage ---------------------------------
    score = vendor_score(fields, core, conf["field_score"], conf["vendor_thresholds"])
    cov = score["coverage"]
    steps.append(ReviewStep(
        "coverage", "-",
        f"{score['score']}/10 core -> {score['band']}, but only "
        f"{cov['verified']} of {cov['core_total']} core fields rest on evidence we "
        f"could read"
        + (f" (caveated: {', '.join(cov['caveated'])})" if cov["caveated"] else "")))

    if cov["caveated"] and score["band"] == "High":
        flags.append(
            f"SCORE OVERSTATES COVERAGE — {score['score']}/10 ({score['band']}) while "
            f"{len(cov['caveated'])} core field(s) rest on pages nobody could read "
            f"({', '.join(cov['caveated'])}). Do not compare this vendor against a "
            f"fully-read one on the score alone.")

    if unusable:
        flags.append(
            f"{len(unusable)} page(s) collected but unreadable ({', '.join(sorted(set(unusable)))}) "
            f"— JavaScript-rendered. Any gap below may be OUR limit, not the vendor's silence.")
    if never_collected:
        flags.append(
            f"no {', '.join(sorted(set(never_collected)))} page was ever located — every candidate "
            f"URL failed. A 404 proves our URL guess was wrong, not that the vendor publishes "
            f"nothing. Find it by hand before recording it as absent.")

    # --- verbs 2, 3: missing categories, weak evidence, conflicts ----------
    for f in fields:
        name = f["name"]
        ev = real_evidence(f)
        level, why = confidence(f, field_dictionary, unusable)

        reviewed[name] = dict(f)
        reviewed[name]["extraction_quality"] = extraction_quality(f)
        reviewed[name]["confidence"] = level
        reviewed[name]["confidence_reason"] = why
        # Cite only what the reader can actually see (see review_rules).
        for card in reviewed[name].get("evidence", []):
            hidden = terms_not_visible(card)
            if hidden:
                card["terms_not_shown"] = hidden

        if f["status"] == "NOT_FOUND":
            # THE CLIENT ASKED FOR EXACTLY THIS DISTINCTION, 13 Aug 2026:
            #   "clearly distinguish: information NOT FOUND on the vendor's
            #    public sources / information that COULD NOT BE EVALUATED
            #    because the page could not be reliably extracted."
            #
            # The first version of this blurred them — it said "could not be
            # evaluated" whenever ANY page of the vendor was unreadable, which
            # over-hedged JetBrains' data-residency field into a limitation when
            # both of its home pages (security and privacy) read perfectly well
            # and JetBrains simply does not publish it. Over-hedging is its own
            # dishonesty: it hides a genuine finding behind our own excuse, and
            # it is the mirror image of defect 23.
            #
            # The test is whether THIS FIELD's own home page was readable, not
            # whether the vendor had any bad page at all.
            unread = unread_home_page(f, unusable, field_dictionary)
            if unread:
                kind = (f"could not be evaluated — its {', '.join(unread)} page was "
                        f"collected but could not be reliably extracted")
            else:
                kind = "not found on the vendor's public sources"
                if unusable:
                    kind += (f" (its own pages read cleanly; {len(unusable)} other page(s) "
                             f"did not, so this is a finding about the vendor)")
            missing.append(f"{f['label']}: {kind}")
            steps.append(ReviewStep("missing", name, kind))
            continue

        if f["status"] == "PARTIAL":
            missing.append(f"{f['label']}: a heading or label only — the vendor named it "
                           f"but published no statement. Open the page.")
            steps.append(ReviewStep("missing", name, "label only, no claim written"))

        off = off_home_evidence(f, field_dictionary)
        if off:
            home = field_dictionary.get(name, {}).get("preferred_source_types", [])
            flags.append(f"{f['label']}: evidence came only from {', '.join(off)}, never from "
                         f"{'/'.join(home)}. The match is real; the finding is weak.")
            steps.append(ReviewStep("weak-evidence", name, f"off-home: {', '.join(off)}"))

        gated = gated_evidence(f)
        if gated:
            flags.append(f"{f['label']}: the vendor says the proof exists but does not publish it "
                         f"(\"{gated[0]}\"). It cannot be closed from public sources alone.")
            steps.append(ReviewStep("weak-evidence", name, f"gated evidence: {', '.join(gated)}"))

        for card in ev:
            short = claim_not_in_matched_sentence(card, min_claim)
            if short is not None:
                flags.append(
                    f"{f['label']}: the confidence label was earned by a sentence that does not "
                    f"contain the matched term (longest term-carrying sentence is {short} "
                    f"characters). Read the quote before relying on the label.")
                steps.append(ReviewStep("weak-evidence", name,
                                        f"claim not in matched sentence ({short} chars)"))
                break

        for conflict in conflicting_values(f):
            flags.append(f"{f['label']}: CONFLICT — {conflict}")
            steps.append(ReviewStep("conflict", name, conflict))

    # --- verb 4: prepare the final brief -----------------------------------
    overview, overview_url, overview_body_readable = vendor_overview(records)
    if not overview:
        flags.append("no vendor overview could be quoted — no product page was collected.")
    elif not overview_body_readable:
        flags.append(
            "the vendor overview is the product page's title. That page's BODY could not be "
            "read (JavaScript-rendered), so the title is all we have from it — the description "
            "is the vendor's own, but nothing else on that page was searched.")
    steps.append(ReviewStep(
        "overview", "-",
        f"quoted from the page title of {overview_url}"
        + ("" if overview_body_readable else " — body unreadable, title only")
        if overview else "unavailable: no product page collected"))

    key_sources = [r["source_url"] for r in records if r.get("content_usable") is not False]
    steps.append(ReviewStep(
        "assemble", "-",
        f"{len(reviewed)} fields, {len(missing)} missing or unclear, "
        f"{len(flags)} review flag(s), {len(key_sources)} readable source(s)"))

    brief = VendorBrief(
        vendor_name=vendor["name"],
        vendor_slug=vendor["slug"],
        generated_on=today(),
        vendor_overview=overview,
        product_category=product_category(vendor, category),
        key_sources=key_sources,
        fields=reviewed,
        missing_or_unclear=missing,
        review_flags=flags,
        overall_confidence=score["band"],
        confidence_score=score["score"],
        coverage_verified=cov["verified"],
        coverage_total=cov["core_total"],
        coverage_caveated=cov["caveated"],
    )
    return brief, steps


def save_brief(brief: VendorBrief, out_dir: Path, steps: list[ReviewStep] | None = None) -> Path:
    """
    Persist the brief AND its audit trail, so Agent 3 replays from disk like the
    other two. Half a trail on replay is the same defect as no replay (defect 19).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{brief.vendor_slug}_brief.json"
    payload = brief.to_dict()
    payload["steps"] = [s.__dict__ for s in (steps or [])]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_brief(out_dir: Path, slug: str) -> dict | None:
    """Read a previous review back. Same replay contract as Agents 1 and 2."""
    path = out_dir / f"{slug}_brief.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
