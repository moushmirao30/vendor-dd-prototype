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
                    longest_sentence_length,
                    page_to_blocks, score_field_confidence, split_sentences,
                    term_in)
from .schema import ExtractedField

# Below this, a "sentence" is a list item or a label rather than a claim, and we
# keep the whole block instead so the reviewer sees the context around it.
MIN_SENTENCE_CHARS = 30


@dataclass
class ExtractionStep:
    """One line of Agent 2's audit trail, shown in the UI beside Agent 1's."""

    action: str        # parse-page | match | no-match | missing-html
    #                  | unusable-page | unread-home-page
    #                  | home-page-never-found
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

    # ONLY AN ABSOLUTE PATH IS TRUSTED AS WRITTEN (defect 55, 23 Aug 2026).
    # This branch used to read `if direct.is_file()`, unconditionally and first.
    # Corpora now store repo-RELATIVE paths (the defect-16 fix above), and a
    # relative path handed to Path() resolves against the PROCESS's working
    # directory, not against `root`. Run pytest from a parent folder, or keep
    # this repo and a clone of it open in the same shell, and Agent 2 reads the
    # OTHER tree's cache while reporting it as this one's — no missing-html
    # step, no caveat, evidence quoted from an archive nobody asked for. That is
    # defect 40 with the failure hidden instead of recorded, which is the worse
    # half. `root` is the only authority on where this repo's cache lives, so a
    # relative path must go through it. The absolute branch stays because it is
    # exactly what rescues a pre-fix corpus carrying `C:\Users\...`.
    direct = Path(raw_html_path)
    if direct.is_absolute() and direct.is_file():
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
    Return the sentence in `snippet` that carries the MOST of the matched terms.

    This is the `value` shown in the brief. It is chosen, not written: every
    character is copied from the vendor's page. If no single sentence is long
    enough to stand on its own — a bullet list of certifications, for example —
    we return the whole block, because "SOC 2 and 3" alone tells a reviewer
    nothing about what the vendor actually claimed.

    DEFECT 30 (found 13 Aug 2026 by reading JetBrains' brief). This used to
    return the FIRST sentence containing ANY matched term. JetBrains' security
    block is one paragraph containing three sentences, and the field's headline
    came out as:

        "Please visit our Trust Center to learn more about JetBrains' security
         practices, compliance certifications, and data protection measures."

    That sentence matched exactly one term — `trust center` — and it is a
    signpost: it names no certification, no standard and no commitment. Two
    sentences later, in the same quoted block, JetBrains writes "You can also
    find details on our SOC 2 Type II and GDPR compliance…", which matches two
    terms and is the actual claim. First-match ordering meant the reviewer's
    headline was the sentence that said nothing.

    Counting matched terms fixes it without inventing a relevance score: a
    sentence that mentions more of what we were looking for is more likely to be
    the claim, and every candidate is still a verbatim sentence from the page.
    Ties go to the earliest sentence, which preserves the old behaviour whenever
    the term counts are equal — so this is strictly a tie-break improvement, not
    a new policy.

    `term_in` is used rather than a bare `in` so the same whole-token rule that
    selected the block also selects the sentence. The old code used `t in low`,
    which would let "sla" inside "Slack" pick the headline sentence even though
    whole-token matching had rejected it everywhere else — defect 13, still
    alive in this one function.
    """
    candidates = [s.strip() for s in split_sentences(snippet)
                  if len(s.strip()) >= MIN_SENTENCE_CHARS]
    if not candidates:
        return snippet.strip()

    def term_hits(sentence: str) -> int:
        low = sentence.lower()
        return sum(1 for t in matched_terms if term_in(t.lower(), low))

    scored = [(term_hits(s), -i, s) for i, s in enumerate(candidates)]
    best_hits, _, best = max(scored)
    if best_hits == 0:
        # No sentence long enough also carries a term. Returning the whole
        # snippet is honest: it shows the reviewer everything the block said
        # rather than promoting an arbitrary sentence to a headline.
        return snippet.strip()
    return best


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

    RULE 2 MEASURES THE STATEMENT, NOT THE TAG (second half of defect 28,
    13 Aug 2026). It used to be a flat lookup on `match_location`, so anything
    found in a heading sorted below everything found in a paragraph. Raising a
    full-sentence heading to High in `evidence_level` therefore changed its
    score and nothing else: GitHub's
        "GitHub's API stays secure with ISO, SOC 2, and GDPR."
    still lost to three pricing-page blocks and still never reached the brief,
    because it happened to be published inside an <h2>.

    A heading that is a complete sentence is prose that a designer set in larger
    type. What the tier is really trying to separate is a CLAIM from a LABEL, so
    it now applies the same test the confidence rule applies — is there a
    sentence here long enough to stand on its own? "SOC Certification" is a
    label and still sorts below prose. Image alt-text is untouched: a logo is
    never a claim, however it reads.
    """
    preferred_types = preferred_types or []

    def statement_rank(e: Evidence) -> int:
        if e.match_location == "alt_text_only":
            return 2
        if e.match_location == "body":
            return 0
        # heading_only: prose if the heading is itself a complete sentence.
        return 0 if longest_sentence_length(e.snippet) >= min_body_chars_for_high else 1

    return sorted(
        evidence,
        key=lambda e: (
            -LEVEL_ORDER.index(
                evidence_level(e, authoritative_types, min_body_chars_for_high)),
            statement_rank(e),
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
    never_collected: list[str] | None = None,
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
    # PAGE TYPES THAT WERE NEVER COLLECTED AT ALL (defect 26, JetBrains,
    # 12 Aug 2026). Agent 2 only ever received `records`, so a page type that
    # produced no record was invisible to it. JetBrains' security page 404'd six
    # times - the seed plus all five url_patterns - and Agent 1 recorded that
    # faithfully in its trail. Agent 2 could not see the trail, so
    # security_trust came back NOT_FOUND with a caveat about the wrong pages
    # (pricing and docs), never mentioning that no security page was ever found.
    # JetBrains publishes "SOC 2 Type II and GDPR compliance" in plain prose. A
    # 404 proves OUR URL was wrong, not that a vendor is silent.
    never_collected = never_collected or []

    extraction = settings["extraction"]
    authoritative = settings["confidence"]["authoritative_source_types"]
    max_evidence = extraction["max_evidence_per_field"]
    snippet_max = extraction["snippet_max_chars"]
    min_body_high = extraction["min_body_chars_for_high"]
    # Defect 29. `.get` rather than `[...]` so an older settings.yaml without
    # this key still runs instead of dying with a KeyError on a reviewer's
    # machine — the same reason resolve_html_path tolerates an older corpus.
    noise_phrases = extraction.get("noise_phrases") or []

    steps: list[ExtractionStep] = []

    # --- pass 1: parse each page once ---------------------------------------
    pages: list[tuple[dict, list[Block]]] = []
    unusable: list[str] = []
    # DEFECT 40, 18 Aug 2026. Pages Agent 1 collected and read successfully whose
    # cached HTML is not on THIS machine. Tracked separately from `unusable`
    # because the finding and the remedy are both different: an unusable page is
    # a fact about the vendor's site that a human must go and read; an uncached
    # page is a fact about our own archive, and the fix is to re-collect.
    uncached: list[str] = []
    # The date Agent 1 wrote this corpus, quoted back in the defect-40 caveat so
    # a reviewer can see the pages WERE read once, on a stated day, and that only
    # this copy of the archive lacks them.
    collected_dates = sorted({r.get("date_collected", "") for r in records} - {""})
    corpus_date = collected_dates[-1] if collected_dates else ""
    for record in records:
        # A PAGE THAT CARRIES NO WORDS IS NOT EVIDENCE OF ANYTHING (defect 23).
        #
        # Agent 1 marks pages it collected successfully but could not read -
        # JavaScript-rendered pages that return megabytes of HTML and no text.
        # Agent 2 must not treat those as searched, because "we looked and found
        # nothing" and "there was nothing to look at" are different findings and
        # only the first one is about the vendor.
        if record.get("content_usable") is False:
            unusable.append(record.get("source_type", "?"))
            steps.append(ExtractionStep(
                action="unusable-page", field_name="-",
                source_type=record.get("source_type", "?"),
                detail=(f"skipped - Agent 1 recorded only "
                        f"{record.get('block_count', 0)} heading blocks on this "
                        f"page; it was collected but is not readable. NOT this "
                        f"page's fields' fault if they come back NOT_FOUND."),
            ))
            continue

        html_path = resolve_html_path(record.get("raw_html_path", ""), root)
        if html_path is None:
            # DEFECT 40. Until 18 Aug this recorded a step and moved on, and the
            # step was the ONLY place it was recorded. Delete the HTML cache and
            # every field of every vendor came back NOT_FOUND with no caveat,
            # under the printed sentence "nothing matched on any page we could
            # read" — about pages that were never opened. That is defect 23
            # exactly, inside our own deliverable.
            #
            # It matters now because the client asked on 18 Aug that the 22 MB
            # cache NOT be shipped. The archive a reviewer receives is therefore
            # the precise configuration that produced the lie.
            uncached.append(record.get("source_type", "?"))
            steps.append(ExtractionStep(
                action="missing-html", field_name="-",
                source_type=record.get("source_type", "?"),
                detail=(f"cached HTML not found at "
                        f"{record.get('raw_html_path', '(no path recorded)')} — "
                        "page NOT searched; re-collect before reading any "
                        "NOT_FOUND on this page as a statement about the vendor"),
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
                noise_phrases=noise_phrases,
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
            caveat = ""
            if unusable:
                # NEVER report a clean negative when part of the corpus could not
                # be read. The reviewer has to know which kind of NOT_FOUND this
                # is — and if pages were unreadable, calling it "not published"
                # would be a statement about the vendor that our own evidence
                # does not support.
                caveat = (f" — CAUTION: {len(unusable)} further page(s) "
                          f"({', '.join(unusable)}) were collected but not "
                          f"readable, so this NOT_FOUND may be our limit rather "
                          f"than the vendor's silence")
            steps.append(ExtractionStep(
                action="no-match", field_name=name, source_type="-",
                detail=(f"no match for any of {len(spec['terms'])} terms across "
                        f"{len(pages)} readable page(s) — reported as NOT_FOUND"
                        + caveat),
            ))

        kept = hits[:max_evidence]

        # CAVEATS GO IN THE EVIDENCE LIST, BECAUSE A REVIEWER READS THE BRIEF AND
        # NOT THE AUDIT TRAIL.
        #
        # Two different lies are possible when part of a corpus is unreadable, and
        # defect 23 only fixed the first one:
        #
        #   1. A NOT_FOUND that is really "we could not read the page".
        #   2. A FOUND whose evidence came from somewhere ELSE while the page the
        #      fact belongs on was unreadable. Postman, 12 Aug 2026: the privacy
        #      field reported FOUND / High, quoting Postman's SECURITY page, while
        #      Postman's actual privacy policy had been collected and its entire
        #      readable content was "If you're seeing this message, that means
        #      JavaScript has been disabled on your browser". A confident answer
        #      whose primary source was never read is more dangerous than a blank
        #      one, because nothing about it invites checking.
        home = spec.get("preferred_source_types", [])
        unread_home = [s for s in unusable if s in home]
        absent_home = [s for s in never_collected if s in home]
        uncached_home = [s for s in uncached if s in home]
        caveats: list[dict] = []

        # DEFECT 40 — THIS BRANCH IS FIRST ON PURPOSE.
        #
        # It outranks every caveat below it because it is the only one that means
        # "this run did not look at the page at all". The others describe pages we
        # read and found wanting. A reviewer must not be told which page our
        # answer came from instead, or that the vendor's site is JavaScript-heavy,
        # while the real story is that this machine has no copy of the page.
        #
        # It fires whenever the field's own home page is uncached, and also
        # whenever nothing was kept and ANY page is uncached — because with an
        # empty evidence list there is no way for the reviewer to tell an
        # unsearched corpus from a silent vendor.
        if uncached_home or (not kept and uncached):
            missing = uncached_home or uncached
            caveats.append({
                "heading": ("NOT SEARCHED — the cached copy of the "
                            f"{', '.join(sorted(set(missing)))} page is not on "
                            "this machine"),
                "snippet": (f"Agent 1 collected and read the "
                            f"{', '.join(sorted(set(missing)))} page successfully "
                            f"on {corpus_date or 'an earlier run'}, but its cached "
                            f"HTML is absent here, so Agent 2 could not re-read it. "
                            f"This is a limitation of THIS COPY OF THE ARCHIVE, not "
                            f"a finding about the vendor. The submitted archive "
                            f"deliberately excludes the HTML cache at the client's "
                            f"request (18 Aug 2026), so re-collect the public "
                            f"sources — see the README — before treating anything "
                            f"on this page as absent."),
                "matched_terms": [], "match_location": "tool_limitation",
                "source_url": "", "source_type": "-", "evidence_of": 0,
            })
            steps.append(ExtractionStep(
                action="uncached-page", field_name=name,
                source_type=", ".join(sorted(set(missing))),
                detail=("the page this field belongs on was never opened in this "
                        "run — its cached HTML is missing. Any NOT_FOUND here is "
                        "about our archive, not about the vendor"),
            ))
        elif not kept and absent_home:
            caveats.append({
                "heading": ("No " + ", ".join(absent_home) + " page was ever "
                            "located - this is not evidence the vendor is silent"),
                "snippet": (f"Agent 1 never found a {', '.join(absent_home)} page "
                            f"for this vendor: every candidate URL returned an "
                            f"error, so nothing was searched. A 404 proves our URL "
                            f"guess was wrong, not that the vendor publishes "
                            f"nothing. Find the real page by hand and add it to "
                            f"config/vendors.yaml before recording this as absent."),
                "matched_terms": [], "match_location": "tool_limitation",
                "source_url": "", "source_type": "-", "evidence_of": 0,
            })
            steps.append(ExtractionStep(
                action="home-page-never-found", field_name=name,
                source_type=", ".join(absent_home),
                detail=("no page of this type was collected at all - NOT_FOUND "
                        "here says nothing about the vendor"),
            ))
        # DEFECT 41, 18 Aug 2026. This branch used to read `elif not kept and
        # unusable` — ANY unreadable page anywhere on the vendor's site earned a
        # "this may be our limit" caveat on EVERY empty field. That is precisely
        # the over-hedging defect 39 removed from Agent 3, left alive one layer
        # down in Agent 2, so the same brief contained both sentences at once:
        #
        #   Agent 3: "not found on the vendor's public sources (its own pages
        #             read cleanly; 2 other page(s) did not, so this is a
        #             finding about the vendor)"
        #   Agent 2: "NOT_FOUND may be our limit, not the vendor's silence"
        #
        # It fired on eight fields across Linear, Atlassian and JetBrains. The
        # test is the field's OWN home page, exactly as in Agent 3. Verified
        # against the corpus: coverage is unchanged on all seven vendors,
        # because every field this un-caveats is a non-core one.
        # `or not pages` IS NOT PADDING — a test caught its absence. Narrowing to
        # the field's own home page is right only while SOME page read cleanly.
        # When nothing did, no field has a home page to be readable, `unread_home`
        # is empty for all of them, and every field would report a bare NOT_FOUND
        # about a vendor whose site we never read a word of. That is defect 23
        # again. Agent 3's defect-39 fix carries the same hole; it stays hidden
        # there only because all seven real vendors have at least one good page.
        elif not kept and unusable and (unread_home or not pages):
            blocked = unread_home or unusable
            caveats.append({
                "heading": (f"NOT_FOUND may be our limit — the "
                            f"{', '.join(blocked)} page could not be read"),
                "snippet": (f"This field's own page type "
                            f"({', '.join(blocked)}) was collected but "
                            f"contained no readable text — almost certainly "
                            f"JavaScript-rendered. Nothing was searched where this "
                            f"fact belongs, so this NOT_FOUND is about our reach, "
                            f"not the vendor's silence. Verify by hand before "
                            f"recording it as not published."),
                "matched_terms": [], "match_location": "tool_limitation",
                "source_url": "", "source_type": "-", "evidence_of": 0,
            })
        elif kept and unread_home:
            caveats.append({
                "heading": "The page this fact belongs on could not be read",
                "snippet": (f"The {', '.join(unread_home)} page was collected but "
                            f"contained no readable text, so this answer comes from "
                            f"the "
                            f"{', '.join(sorted({e.source_type for e in kept}))} "
                            f"page instead. Treat the confidence above as being "
                            f"about the quote, not about the vendor's actual "
                            f"{', '.join(unread_home)} document, which nobody has "
                            f"read."),
                "matched_terms": [], "match_location": "tool_limitation",
                "source_url": "", "source_type": "-", "evidence_of": 0,
            })
            steps.append(ExtractionStep(
                action="unread-home-page", field_name=name,
                source_type=", ".join(unread_home),
                detail=(f"{name} reported {status_from_confidence(confidence)} from "
                        f"{', '.join(sorted({e.source_type for e in kept}))}, but its "
                        f"own page type ({', '.join(unread_home)}) was unreadable — "
                        f"caveat attached to the field"),
            ))

        fields.append(ExtractedField(
            name=name,
            label=spec["label"],
            status=status_from_confidence(confidence),
            value=best_sentence(kept[0].snippet, kept[0].matched_terms) if kept else "",
            confidence=confidence,
            evidence=([e.__dict__ | {"evidence_of": len(hits)} for e in kept]
                      + caveats),
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
