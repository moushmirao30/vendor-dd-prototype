"""
agent2_extract.py — AGENT 2 of 3: Evidence Extraction.

ITS ONE JOB: read the pages Agent 1 collected and turn them into structured
fields, where every field carries the exact text it came from and the URL of the
page that said it. It decides nothing about the vendor. It does not write
sentences. It quotes.

THREE DESIGN DECISIONS THAT NEED DEFENDING
------------------------------------------
1. IT READS RAW HTML, NOT `collected_text`.
   `collected_text` is the cleaned, human-readable version of a page. On
   GitLab's security page the cleaner discarded 88% of the text, including every
   certification sentence. Extraction reads the raw HTML from the cache instead,
   so it keeps the heading structure that makes a snippet meaningful and it is
   immune to a cleaner having an off day. This separation is the single most
   valuable structural decision in the project (see docs/evaluation.md).

2. `value` IS A QUOTE, NEVER A SUMMARY.
   There is no language model in this prototype. Anything that reads like a
   written summary would therefore have to be assembled by string-joining, and a
   machine-assembled sentence is exactly the kind of statement a reviewer cannot
   trace back to a source. So `value` is the single sentence from the page that
   contains the matched term, copied character for character. If the honest
   answer is "the vendor's own words", printing the vendor's own words is not a
   limitation — it is the requirement.

3. EACH PAGE IS PARSED ONCE, THEN SEARCHED FOR ALL EIGHT FIELDS.
   Calling `page_to_blocks` per field would re-parse a 587 KB HTML file eight
   times per page. Blocks are computed once per page and reused, which makes a
   full seven-page vendor extraction finish in under two seconds on a laptop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path

from .parse import (LEVEL_ORDER, Block, Evidence, evidence_level, find_evidence,
                    page_to_blocks, score_field_confidence, split_sentences)
from .schema import ExtractedField

# Below this, a "sentence" is a list item or a label rather than a claim, and we
# keep the whole block instead so the reviewer sees the context around it.
MIN_SENTENCE_CHARS = 30


@dataclass
class ExtractionStep:
    """One line of Agent 2's audit trail, shown in the UI beside Agent 1's."""

    action: str        # "parse-page" | "match" | "no-match" | "missing-html"
    field_name: str
    source_type: str
    detail: str


def resolve_html_path(raw_html_path: str, root: Path) -> Path | None:
    """
    Find a cached page on THIS machine, whatever machine wrote the corpus.

    WHY THIS FUNCTION EXISTS: `raw_html_path` was written as an absolute path
    (`C:\\Users\\...\\data\\cache\\html\\v2_abc.html`). That is fine until the
    corpus is opened anywhere else — a marker's laptop, a fresh clone, a CI box —
    where the file is present but the path is not. The README promises the whole
    workflow replays offline from the cache; an absolute path quietly breaks that
    promise for everyone except the machine that made it.

    The fix in `fetch.py` stores a repo-relative path from now on. This function
    also rescues corpora written before that fix by falling back to the file
    NAME inside this repo's cache directory.
    """
    if not raw_html_path:
        return None

    direct = Path(raw_html_path)
    if direct.is_file():
        return direct

    relative = root / raw_html_path.replace("\\", "/")
    if relative.is_file():
        return relative

    # Last resort: the filename is a content-addressed cache key, so the same
    # name in this repo's cache is the same page.
    name = raw_html_path.replace("\\", "/").rsplit("/", 1)[-1]
    for candidate in (root / "data" / "cache" / "html").glob(name):
        return candidate
    return None


def best_sentence(snippet: str, matched_terms: list[str]) -> str:
    """
    Return the one sentence in `snippet` that contains a matched term.

    This is the `value` shown in the brief. It is chosen, not written: every
    character is copied from the vendor's page. If no single sentence is long
    enough to stand on its own — a bullet list of certifications, for example —
    we return the whole block, because "SOC 2 and 3" alone tells a reviewer
    nothing about what the vendor actually claimed.
    """
    sentences = split_sentences(snippet)
    for sentence in sentences:
        low = sentence.lower()
        if any(t in low for t in matched_terms) and len(sentence) >= MIN_SENTENCE_CHARS:
            return sentence.strip()
    return snippet.strip()


def rank_evidence(
    evidence: list[Evidence],
    authoritative_types: list[str],
    preferred_types: list[str] | None = None,
    min_body_chars_for_high: int = 40,
) -> list[Evidence]:
    """
    Strongest evidence first, because the top item becomes the brief's `value`
    and everything past `max_evidence_per_field` is thrown away.

    The order, worst-to-best tie-breaks last:
      1. CONFIDENCE LEVEL         High before Medium before Low, using the same
                                  `evidence_level` the field's own confidence
                                  uses. This is first for a reason: the top item
                                  becomes the quote printed under the field's
                                  confidence label, so if anything else came
                                  first the brief could print "High" above a
                                  quote that was only worth Medium.
      2. WHERE the term sat        prose > heading > image alt-text
      3. IS THIS THE RIGHT PAGE?   a security claim on the security page beats
                                   the same words on the pricing page
      4. IS THE PAGE FORMAL?       authoritative (security/privacy/pricing/
                                   status/terms) beats marketing pages
      5. HOW MANY TERMS MATCHED    two dictionary terms in one block is a
                                   stronger signal than one
      6. SHORTER BLOCK WINS        density, see below

    RULE 6 IS THE REVERSED ONE, AND IT IS THE POINT.
    This function first sorted by LONGEST snippet, on the reasoning that more
    surrounding text gives a reviewer more context. Running it over the real
    GitLab corpus showed why that is backwards: the longest blocks on any
    vendor site are the boilerplate slabs — a whole status board, an entire
    pricing tier table. GitLab's security field was reported as
    "Website Operational API Operational Git Operations Operational…" — 600
    characters of status board — while the sentence the entire project is built
    around, "GitLab maintains a SOC 2 Type 2 report for the Security,
    Confidentiality and Availability Trust Services Criteria for GitLab.com",
    was ranked THIRD. Past the 40-character floor, a short block that mentions
    the term is a focused claim; a long one is furniture that happens to
    contain the word.

    RULE 3 NEEDS THE OPPOSITE WARNING: it orders evidence, it does not filter
    it. A genuine claim on an unexpected page still appears, just lower down —
    GitLab really does state its FedRAMP position on the pricing page, and
    hiding that because it was "the wrong page" would be the extractor
    overruling the vendor.
    """
    preferred_types = preferred_types or []
    location_rank = {"body": 0, "heading_only": 1, "alt_text_only": 2}
    return sorted(
        evidence,
        key=lambda e: (
            -LEVEL_ORDER.index(
                evidence_level(e, authoritative_types, min_body_chars_for_high)),
            location_rank.get(e.match_location, 3),
            0 if e.source_type in preferred_types else 1,
            0 if e.source_type in authoritative_types else 1,
            -len(e.matched_terms),
            len(e.snippet),
        ),
    )


def dedupe_evidence(evidence: list[Evidence]) -> list[Evidence]:
    """
    Drop repeats of the same text.

    Vendors repeat compliance blurbs in page furniture. Without this, one banner
    that appears on all seven pages produces seven "independent" pieces of
    evidence and makes a single sentence look like a body of proof.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[Evidence] = []
    for e in evidence:
        key = (e.heading.lower(), e.snippet[:120].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    return unique


def status_from_confidence(confidence: str) -> str:
    """
    Translate a confidence level into the brief's three-state status.

      FOUND      High or Medium — the vendor states it, and we can quote it.
      PARTIAL    Low — something matched, but only a heading, a logo, or a
                 fragment. A reviewer must open the page themselves.
      NOT_FOUND  nothing matched on any page we are permitted to read.

    PARTIAL exists so that "we saw a hint" is never reported with the same
    weight as "the vendor said so". That distinction is the whole point of the
    Atlassian test case, where the certifications are images.
    """
    if confidence in ("High", "Medium"):
        return "FOUND"
    if confidence == "Low":
        return "PARTIAL"
    return "NOT_FOUND"


def extract_for_vendor(
    records: list[dict],
    field_dictionary: dict,
    settings: dict,
    root: Path,
) -> tuple[list[ExtractedField], list[ExtractionStep]]:
    """
    Run every field in the dictionary against every collected page.

    `records` are corpus rows as dicts (exactly what `gitlab.json` holds), so
    this function works identically on a live run and on a replay from disk.

    Returns (fields, steps). `steps` is the audit trail: which pages were parsed,
    which fields matched where, and — the important half — which fields matched
    nothing, and how many pages were searched before saying so. A NOT_FOUND with
    no evidence of effort behind it is not a finding, it is a shrug.
    """
    extraction = settings["extraction"]
    authoritative = settings["confidence"]["authoritative_source_types"]
    max_evidence = extraction["max_evidence_per_field"]
    snippet_max = extraction["snippet_max_chars"]
    min_body_high = extraction["min_body_chars_for_high"]

    steps: list[ExtractionStep] = []

    # --- pass 1: parse each page once ---------------------------------------
    pages: list[tuple[dict, list[Block]]] = []
    for record in records:
        html_path = resolve_html_path(record.get("raw_html_path", ""), root)
        if html_path is None:
            steps.append(ExtractionStep(
                action="missing-html", field_name="-",
                source_type=record.get("source_type", "?"),
                detail=(f"cached HTML not found at "
                        f"{record.get('raw_html_path', '(no path recorded)')} — "
                        "page skipped; re-run Agent 1 to refetch"),
            ))
            continue

        html = html_path.read_text(encoding="utf-8", errors="replace")
        blocks = page_to_blocks(html)
        pages.append((record, blocks))
        steps.append(ExtractionStep(
            action="parse-page", field_name="-",
            source_type=record["source_type"],
            detail=f"{len(blocks)} blocks from {len(html):,} characters of HTML",
        ))

    # --- pass 2: search the parsed blocks, field by field --------------------
    fields: list[ExtractedField] = []
    for name, spec in field_dictionary.items():
        hits: list[Evidence] = []

        for record, blocks in pages:
            found = find_evidence(
                blocks,
                terms=spec["terms"],
                negative_terms=spec.get("negative_terms"),
                snippet_max_chars=snippet_max,
                source_url=record["source_url"],
                source_type=record["source_type"],
            )
            if found:
                steps.append(ExtractionStep(
                    action="match", field_name=name,
                    source_type=record["source_type"],
                    detail=f"{len(found)} block(s) matched on {record['source_url']}",
                ))
            hits.extend(found)

        hits = rank_evidence(dedupe_evidence(hits), authoritative,
                             spec.get("preferred_source_types"), min_body_high)
        confidence = score_field_confidence(hits, authoritative, min_body_high)

        if not hits:
            steps.append(ExtractionStep(
                action="no-match", field_name=name, source_type="-",
                detail=(f"no match for any of {len(spec['terms'])} terms across "
                        f"{len(pages)} collected page(s) — reported as NOT_FOUND"),
            ))

        kept = hits[:max_evidence]
        fields.append(ExtractedField(
            name=name,
            label=spec["label"],
            status=status_from_confidence(confidence),
            value=best_sentence(kept[0].snippet, kept[0].matched_terms) if kept else "",
            confidence=confidence,
            evidence=[e.__dict__ | {"evidence_of": len(hits)} for e in kept],
        ))

    return fields, steps


def save_fields(
    fields: list[ExtractedField],
    out_dir: Path,
    slug: str,
    steps: list[ExtractionStep] | None = None,
    ran_on: str = "",
) -> Path:
    """
    Persist Agent 2's output AND its audit trail so both replay from disk.

    WHY THE STEPS ARE SAVED HERE (defect 19, found 2026-08-12 in the browser):
    the first version wrote only the fields. Reload the page and the Agent steps
    tab said "Step 2 — complete, replayed from disk" with no table under it,
    while Agent 1's full trail was still there — because Agent 1 persists its
    steps via `save_run` and Agent 2 did not. The brief asks the interface to let
    a reviewer "run **or replay** the workflow" and "see each agent step"; half a
    trail on replay is the same defect as no replay at all (defect 9), one agent
    later.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}_fields.json"
    path.write_text(
        json.dumps(
            {
                "vendor_slug": slug,
                "ran_on": ran_on,
                "fields": [f.to_dict() for f in fields],
                "steps": [s.__dict__ for s in (steps or [])],
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def load_fields(out_dir: Path, slug: str) -> dict | None:
    """
    Read a previous extraction back. Same replay contract as Agent 1.

    Returns `{"fields": [...], "steps": [...], "ran_on": "..."}`, or None if this
    vendor has never been extracted. A bare list written by the first version of
    `save_fields` is still readable, so an older corpus does not crash the app.
    """
    path = out_dir / f"{slug}_fields.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):        # written before steps were persisted
        return {"fields": data, "steps": [], "ran_on": "an earlier run"}
    return {"fields": data.get("fields", []), "steps": data.get("steps", []),
            "ran_on": data.get("ran_on", "an earlier run")}
