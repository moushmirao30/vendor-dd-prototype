"""
review_rules.py — the review predicates, in ONE place, imported by two callers.

WHY THIS FILE EXISTS
--------------------
`tools/verify_corpus.py` grew into a working prototype of Agent 3 before Agent 3
was written. By 13 August it already computed the vendor score, field coverage,
off-home evidence, unread home pages, unusable pages and the
claim-not-in-matched-sentence check — every judgement the Brief Review Agent
needs to make.

The obvious next move was to write those checks again inside Agent 3. That would
have been the fourth instance in this project of the same failure: two things
that are supposed to agree, drifting apart because nobody made them share code.
Defect 15 was the confidence rule disagreeing with its own documentation.
Defect 36 was two docstrings disagreeing about one rule, which silently killed
an entire status value. A build-time checker and a shipped brief computing
"coverage" two different ways would be the same bug wearing a third hat.

So every predicate lives here. `verify_corpus.py` imports it to decide whether a
corpus may be committed. `agent3_review.py` imports it to decide what the
reviewer is told. When a rule changes, it changes once.

WHAT IS NOT HERE
----------------
Anything that needs to read meaning. These are mechanical predicates over
structure — which page, which status, is there a caveat, is the term visible in
the quote. They cannot tell you whether a sentence is *true*, or whether it
answers the question a procurement team actually asked. That is the reviewer's
job, and saying so plainly is the point of the whole prototype.
"""

from __future__ import annotations

import re

from .parse import longest_sentence_length, split_sentences, term_in

# ---------------------------------------------------------------------------
# Helpers shared by several predicates
# ---------------------------------------------------------------------------

CAVEAT = "tool_limitation"


def real_evidence(field: dict) -> list[dict]:
    """
    The evidence a reviewer can actually read, with our own caveats removed.

    Caveat entries are injected into the evidence list on purpose — a reviewer
    reads the brief, not the audit trail — but they are notes from us, not
    statements from the vendor. Every predicate that asks "what did the vendor
    say?" must exclude them, and forgetting to is an easy way to make a field
    look better evidenced than it is.
    """
    return [e for e in field.get("evidence", []) if e.get("match_location") != CAVEAT]


def caveats(field: dict) -> list[dict]:
    """The notes we attached about our own limitations."""
    return [e for e in field.get("evidence", []) if e.get("match_location") == CAVEAT]


def is_caveated(field: dict) -> bool:
    return bool(caveats(field))


def home_types(field_name: str, dictionary: dict) -> list[str]:
    """The page types where this field's answer belongs."""
    return dictionary.get(field_name, {}).get("preferred_source_types", []) or []


# ---------------------------------------------------------------------------
# COVERAGE — what was checked, as opposed to what was found
# ---------------------------------------------------------------------------

def field_coverage(fields: list[dict], core_field_names: list[str]) -> dict:
    """
    How many core fields rest on evidence we could actually read.

    THIS IS THE ANSWER TO DEFECT 31, AND IT IS THE MOST IMPORTANT NUMBER IN THE
    BRIEF AFTER THE SCORE ITSELF.

    Measured on the real corpus, 13 August: Postman scores 10/10 -> High with
    four of eight fields resting on pages that returned no readable text at all
    (its privacy policy is 0 characters). Sentry scores 10/10 -> High with every
    page read. The score cannot tell them apart, because the score counts what
    was FOUND and never counts what was never LOOKED AT.

    Presented side by side without this figure, those two vendors are
    indistinguishable to an operations lead — which is precisely the failure this
    whole project exists to report, reproduced by our own scoring.
    """
    core = [f for f in fields if f["name"] in core_field_names]
    caveated = [f["name"] for f in core if is_caveated(f)]
    return {
        "core_total": len(core),
        "verified": len(core) - len(caveated),
        "caveated": sorted(caveated),
    }


def vendor_score(fields: list[dict], core_field_names: list[str],
                 field_score: dict, thresholds: dict) -> dict:
    """
    The 0-10 EVIDENCE score and its band — how much quotable material was found.

    DEFECT 42, 18 Aug 2026: THIS IS NOT THE CLIENT'S CONFIDENCE MEASURE, AND IT
    USED TO BE CALLED ONE.

    It sums `f["confidence"]`, which is Agent 2's extraction axis — the sentence
    measure the client asked us on 18 Aug not to base confidence on. The two-axis
    change that day landed on the FIELD CARD and never reached the vendor header,
    so one brief carried both answers at once:

        header:  Confidence 10/10 -> High        (this function)
        fields:  confidence: Medium              (the client's rule)

    and HANDOFF's claim that "Postman can no longer tie Sentry" was false —
    both still read 10/10 High while Postman's coverage was 2/5 and Sentry's 5/5.

    The function is unchanged and correct at what it does. Only the NAME was
    wrong, and a number named after a question it does not answer is how defects
    15, 36 and 41 all started. Callers now report it as `evidence_score`, beside
    `vendor_confidence` and coverage — three numbers, three questions.

    Coverage still travels with it, for the reason it always did: neither is safe
    to read alone.
    """
    total = sum(field_score.get(f["confidence"], 0)
                for f in fields if f["name"] in core_field_names)
    band = ("High" if total >= thresholds["High"]
            else "Medium" if total >= thresholds["Medium"] else "Low")
    return {"score": total, "band": band, "coverage": field_coverage(fields, core_field_names)}


def vendor_confidence(fields: list[dict], core_field_names: list[str],
                      dictionary: dict, unusable_types: list[str]) -> dict:
    """
    The vendor-level view of the CLIENT'S confidence axis. Defect 42's other half.

    WHY THIS RETURNS COUNTS AND NOT A 0-10 SCORE
    --------------------------------------------
    Compressing three levels into a score needs two thresholds, and we would be
    choosing them while looking at our own seven vendors. Any cut-off that made
    the table read well would be fitted to the answer — the same mistake the
    locked decisions already forbid for the field dictionary ("avoids over-fitting
    to one vendor"). A count needs no threshold and cannot be tuned.

    The counts are also the figure that does the work the client's rule was for.
    Measured on the real corpus, 18 Aug: Sentry, GitLab and GitHub each have TWO
    core fields at High; Postman and Atlassian have ZERO. The 0-10 evidence score
    calls all five of those vendors 10/10 High. This is the separation that was
    missing.

    `band` is the weakest link — a first-pass brief is only as trustworthy as the
    weakest core field a reviewer will act on. That is a stated principle, not a
    tuned cut-off, which is the whole point. Read it as a floor, and read the
    counts for the shape.
    """
    core = [f for f in fields if f["name"] in core_field_names]
    levels = [confidence(f, dictionary, unusable_types)[0] for f in core]
    counts = {
        "High": levels.count("High"),
        "Medium": levels.count("Medium"),
        "Low": levels.count("Low") + levels.count("NOT_FOUND"),
    }
    band = ("Low" if counts["Low"] else
            "Medium" if counts["Medium"] else
            "High" if counts["High"] else "NOT_FOUND")
    return {"counts": counts, "band": band, "total": len(core),
            "high": counts["High"]}


# ---------------------------------------------------------------------------
# WEAK-EVIDENCE PREDICATES
#
# The client's guidance of 13 August asked Agent 3 to "highlight conflicts or
# weak evidence". Everything below is the weak-evidence half, and every one of
# these fires on the real corpus — see `conflicting_values` for the other half
# and for why it does not.
# ---------------------------------------------------------------------------

def off_home_evidence(field: dict, dictionary: dict) -> list[str]:
    """
    All the evidence came from somewhere other than where this fact belongs.

    The match is real; the finding is weak. On GitLab, three of five core fields
    draw their strongest evidence from the PRIVACY POLICY — a page that is both
    authoritative and unusually full of complete sentences. A reviewer needs to
    know that "GitLab's support commitment" was found in a privacy policy.

    Returns the page types the evidence actually came from, or [] if at least one
    piece came from the right place.
    """
    ev = real_evidence(field)
    home = home_types(field["name"], dictionary)
    if not ev or not home:
        return []
    if any(e.get("source_type") in home for e in ev):
        return []
    return sorted({e.get("source_type", "?") for e in ev})


def unread_home_page(field: dict, unusable_types: list[str], dictionary: dict) -> list[str]:
    """
    The page this fact belongs on was collected and could not be read.

    Defect 24, Postman: the privacy field reported FOUND / High quoting the
    SECURITY page while Postman's actual privacy policy returned zero readable
    characters. A confident answer whose primary source was never read is more
    dangerous than a blank one, because nothing about it invites checking.
    """
    return [t for t in unusable_types if t in home_types(field["name"], dictionary)]


# A vendor that publishes "we hold SOC 2, ask us for the report" has told you
# less than it appears to. Sentry does exactly this. The evidence is real and the
# document behind it is not public, so the field cannot be closed from public
# sources alone — which is a review flag, not a defect.
GATED_PHRASES = (
    "upon request", "available to customers", "available on request",
    "contact us for", "under nda", "request access", "sign in to view",
    "customers can request", "available to prospects",
)


def gated_evidence(field: dict) -> list[str]:
    """The vendor says the proof exists but is not published. Which phrase said so."""
    hits = []
    for e in real_evidence(field):
        text = f"{e.get('snippet','')} {e.get('heading','')}".lower()
        hits += [p for p in GATED_PHRASES if p in text]
    return sorted(set(hits))


def terms_not_visible(evidence: dict) -> list[str]:
    """
    Terms this card cites that a reader cannot find in the text it prints.

    20 of 122 cards do this. All 42 such terms ARE on the source page — they fall
    outside the 600-character snippet window — so this is a presentation defect,
    not a fabrication. It still matters: a reviewer shown "matched: SOC 2,
    ISO 27001, PCI DSS, HIPAA" above a quote containing only "SOC 2" cannot check
    the other three without leaving the brief.

    Agent 3 uses this to cite only what is visible and count the rest.
    """
    shown = f"{evidence.get('snippet','')} {evidence.get('heading','')}".lower()
    return [t for t in (evidence.get("matched_terms") or [])
            if not term_in(t.lower(), shown)]


def claim_not_in_matched_sentence(evidence: dict, min_claim_chars: int) -> int | None:
    """
    The confidence label was earned by a sentence that does not carry the term.

    Defect 37. `evidence_level` measures the longest sentence anywhere in the
    block. In 9 of 122 blocks that sentence contains no matched term at all.
    Atlassian's security field is the clearest case: `hipaa` appears only in the
    39-character terms-of-service section title "Sensitive Health Information and
    HIPAA.", while the High came from a 322-character sentence about something
    else in the same section.

    DELIBERATELY NOT FIXED IN THE SCORING. Tightening the rule to score only the
    term-carrying sentence would also demote Sentry's "High Availability" heading
    with a full paragraph beneath it, and GitLab's "Trust Center Documents" —
    vendors do not repeat a heading inside its own paragraph. That trades a
    cosmetic over-score for a false negative, which is the mistake the defect 28
    route-not-taken already taught us. Whether a block coheres is a judgement,
    so we measure it and hand it to the human.

    Returns the length of the longest term-carrying sentence when it falls short,
    or None when there is nothing to report.
    """
    terms = [t.lower() for t in (evidence.get("matched_terms") or [])]
    snippet, heading = evidence.get("snippet", ""), evidence.get("heading", "")
    if not terms or longest_sentence_length(snippet) < min_claim_chars:
        return None
    pool = split_sentences(snippet) + split_sentences(heading) + [heading]
    carrying = max((len(s) for s in pool
                    if any(term_in(t, s.lower()) for t in terms)), default=0)
    return carrying if carrying < min_claim_chars else None


# ---------------------------------------------------------------------------
# CONFLICTS — the other half of the client's request
# ---------------------------------------------------------------------------

_PERCENT = re.compile(r"\b(\d{2,3}(?:\.\d+)?)\s*%")
_SOC_TYPE = re.compile(r"\btype\s*(i{1,3}|1|2|3)\b", re.I)

# A NEGATION HEURISTIC WAS TRIED HERE AND REMOVED THE SAME HOUR, 13 Aug 2026.
# The idea was that one page saying "we do not X" while another says "we X" is a
# conflict. Run over the corpus it fired on three of seven vendors and every hit
# was false — the flags read "negative on privacy, plain on privacy", because it
# was comparing three blocks of the SAME privacy policy against each other. A
# privacy policy naturally contains both "we do not sell your data" and ordinary
# positive statements; that is what a privacy policy IS.
#
# A detector that produces false positives is worse than one that produces
# nothing, because it teaches the reviewer to skim past flags — and the flags are
# the entire product. Deleted rather than tuned: there is no threshold that turns
# "this paragraph contains the word not" into evidence of contradiction.


def conflicting_values(field: dict) -> list[str]:
    """
    Two official pages of the same vendor stating different things.

    WHAT THIS CAN AND CANNOT SEE, STATED HONESTLY.
    A rule-based system cannot detect semantic contradiction. What it can detect
    is disagreement in the small number of value shapes that appear verbatim in
    due-diligence prose: a percentage (99.9% vs 99.95% uptime), an audit level
    (SOC 2 Type I vs Type II), and a negation appearing on one page and not
    another for the same field.

    **On the 13 August corpus this returns nothing for all seven vendors.** That
    is reported rather than hidden, and it is why the function ships with a unit
    test that proves it fires on a constructed case. Defect 34 was a safeguard
    that had never once executed because nothing exercised it; a detector whose
    zero-count is measured and tested is a different thing from one nobody ever
    ran. If a later collection run surfaces a genuine conflict, this catches it.

    Returns human-readable descriptions, one per disagreement.
    """
    ev = real_evidence(field)
    if len(ev) < 2:
        return []

    out: list[str] = []
    for label, rx in (("uptime/percentage figure", _PERCENT),
                      ("audit level", _SOC_TYPE)):
        by_page: dict[str, set[str]] = {}
        for e in ev:
            vals = {m.group(0).strip().lower() for m in rx.finditer(e.get("snippet", ""))}
            if vals:
                by_page[e.get("source_type", "?")] = vals
        distinct = set().union(*by_page.values()) if by_page else set()
        if len(by_page) > 1 and len(distinct) > 1:
            detail = "; ".join(f"{p}: {', '.join(sorted(v))}" for p, v in sorted(by_page.items()))
            out.append(f"{label} differs between pages — {detail}")
    return out


# ---------------------------------------------------------------------------
# CONFIDENCE — the client's definition, mechanically approximated
# ---------------------------------------------------------------------------

def extraction_quality(field: dict) -> str:
    """
    HOW the evidence was written: prose, a list, a bare label, or a logo.

    This is Agent 2's existing `confidence` value, renamed to what it actually
    measures. First Quadrant Labs asked on 13 August that confidence not rest
    primarily on sentence length — and they are right, because length answers a
    narrower question than the name claimed. It is a good measure of "is this a
    claim or a label"; it was the wrong thing to call confidence.

    Their own guidance supplies the fix: *"You can additionally track extraction
    quality separately … complete sentence, bullet list, table, etc."* So the old
    single axis becomes this one, unchanged in logic, honest in name.
    """
    return field.get("confidence", "NOT_FOUND")


def confidence(field: dict, dictionary: dict, unusable_types: list[str]) -> tuple[str, str]:
    """
    Confidence on the client's definition. Returns (level, one-line reason).

    Their wording, from the guidance of 13 August:
        High   — direct, explicit evidence from an authoritative official source,
                 with the requested field clearly answered.
        Medium — relevant official evidence exists, but it is incomplete,
                 indirect, spread across multiple sections, or requires limited
                 interpretation.
        Low    — evidence is weak, ambiguous, outdated, inaccessible, or the field
                 cannot be confidently established.

    "Clearly answered" and "requires limited interpretation" are semantic
    judgements, and this prototype has no language model by design — a decision
    the same email endorsed. So each level is approximated by structure:

        High   — the evidence sits on one of the field's own preferred
                 authoritative pages, the matched term is visible in the text we
                 print, and no caveat is attached.
        Medium — official evidence exists but something above is untrue: it came
                 from the wrong page, its home page was unreadable, or the reader
                 cannot see the cited term in the quote.
        Low    — a bare label, a logo, or extraction quality of Low.

    THE POINT OF THE "no caveat" CLAUSE: it makes defect 31 unrepresentable.
    A field whose home page could not be read can no longer be called High, so
    Postman can no longer tie Sentry on the strength of pages nobody opened.
    The client prescribed this fix without knowing the defect existed.
    """
    ev = real_evidence(field)
    if not ev:
        # DEFECT 40, 18 Aug 2026. The old single line said "nothing matched on
        # any page we could read" for EVERY empty field — which asserts the pages
        # were read. Delete the HTML cache, as the submitted archive does at the
        # client's request, and that sentence appeared under all eight fields of
        # all seven vendors about pages nobody opened.
        #
        # When a caveat is attached, the pages were NOT read, and the caveat
        # already says why. Leading with the client's own phrase keeps their
        # two-way distinction visible in the brief itself (guidance of 18 Aug,
        # item 2): information NOT FOUND on the vendor's public sources, versus
        # information that COULD NOT BE EVALUATED because the page could not be
        # reached or reliably extracted.
        notes = caveats(field)
        if notes:
            return "NOT_FOUND", ("could not be evaluated — "
                                 + notes[0].get("heading", "a collection "
                                                "limitation applies"))
        return "NOT_FOUND", "nothing matched on any page we could read"

    quality = extraction_quality(field)
    if quality == "Low":
        return "Low", "only a label, a fragment or an image — nothing quotable was written"

    reasons = []
    if is_caveated(field):
        unread = unread_home_page(field, unusable_types, dictionary)
        reasons.append(f"the {', '.join(unread)} page could not be read"
                       if unread else "a collection limitation applies")
    off_home = off_home_evidence(field, dictionary)
    if off_home:
        home = home_types(field["name"], dictionary)
        reasons.append(f"evidence came from {', '.join(off_home)}, "
                       f"never from {'/'.join(home)}")
    if terms_not_visible(ev[0]):
        reasons.append("the top card cites terms its quoted text does not show")

    if reasons:
        return "Medium", "; ".join(reasons)
    return "High", (f"stated directly on the vendor's own "
                    f"{ev[0].get('source_type','official')} page, quoted in full, "
                    f"with no collection limitation")
