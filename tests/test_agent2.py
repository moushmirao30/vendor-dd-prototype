"""
test_agent2.py — tests for the Evidence Extraction Agent.

READ THIS BEFORE ADDING A TEST HERE.
Every defect in this project so far was found by opening the artifact and
reading it, not by a test. The tests that earn their place are the ones that
pin down a bug AFTER a human found it, so it cannot come back quietly. Each
test below names the defect it guards.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src.agent2_extract import (best_sentence, dedupe_evidence, extract_for_vendor,
                                rank_evidence, resolve_html_path,
                                status_from_confidence)
from src.parse import Evidence, page_to_blocks, find_evidence, term_in

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def settings() -> dict:
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def field_dictionary() -> dict:
    return yaml.safe_load(
        (ROOT / "config" / "field_dictionary.yaml").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# DEFECT 13 — bare substring matching.
# "sla" matched "Slack" 11 times out of 13 across GitLab's pages; "cli" matched
# "click"/"client"/"decline" 9 times out of 9 and the command line interface
# zero times. The visible symptom was GitLab's uptime field reported FOUND/High
# quoting its privacy policy. These are the guards.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("term,text,expected", [
    ("sla", "we offer a 99.9% sla on enterprise", True),
    ("sla", "join our slack workspace", False),
    ("sla", "https://app.slack.com/client/t04sjbk1c/", False),
    ("cli", "install the cli and run it", True),
    ("cli", "click here to continue", False),
    ("cli", "the client may decline", False),
    ("soc 2", "we maintain a soc 2 type 2 report", True),
    ("soc 2", "soc 2 type ii", True),
    ("iso 27001", "certified to iso 27001:2022", True),      # trailing colon is fine
    ("aes 256", "aes 256-bit encryption at rest", True),     # trailing hyphen is fine
    ("% uptime", "99.99% uptime last month", True),          # leading punctuation term
    ("99.9", "a 99.9% sla", True),
    ("99.9", "priced at $99.99 per seat", False),            # 99.9 inside 99.99
])
def test_terms_match_whole_words_only(term, text, expected):
    assert term_in(term, text) is expected


def test_slack_url_does_not_become_sla_evidence():
    """End-to-end version of the same defect, through find_evidence."""
    html = ("<h2>Follow our status updates</h2>"
            "<p>Find the channel ID in your Slack workspace and click submit.</p>")
    hits = find_evidence(page_to_blocks(html), terms=["sla", "cli"])
    assert hits == [], f"Slack/click matched as SLA/CLI evidence: {hits}"


# ---------------------------------------------------------------------------
# DEFECT 14 — ranking by longest snippet surfaced boilerplate.
# GitLab's security field quoted 600 characters of status board while the
# "GitLab maintains a SOC 2 Type 2 report..." sentence ranked third.
# ---------------------------------------------------------------------------

def test_focused_claim_outranks_a_long_boilerplate_block():
    boilerplate = Evidence(
        heading="Status", snippet="Website Operational " * 30,
        matched_terms=["saml"], match_location="body",
        source_url="https://status.example.com/", source_type="status")
    claim = Evidence(
        heading="SOC Certification",
        snippet="Example maintains a SOC 2 Type 2 report for the Security, "
                "Confidentiality and Availability Trust Services Criteria.",
        matched_terms=["soc 2", "soc 2 type 2"], match_location="body",
        source_url="https://example.com/security/", source_type="security")

    ranked = rank_evidence([boilerplate, claim],
                           authoritative_types=["security", "status"],
                           preferred_types=["security", "terms"])
    assert ranked[0] is claim, "the boilerplate block outranked the actual claim"


def test_preferred_page_type_beats_the_same_evidence_elsewhere():
    on_security = Evidence(heading="Compliance", snippet="We hold SOC 2 Type 2.",
                           matched_terms=["soc 2"], match_location="body",
                           source_url="x", source_type="security")
    on_pricing = Evidence(heading="Ultimate tier", snippet="We hold SOC 2 Type 2.",
                          matched_terms=["soc 2"], match_location="body",
                          source_url="y", source_type="pricing")
    ranked = rank_evidence([on_pricing, on_security],
                           authoritative_types=["security", "pricing"],
                           preferred_types=["security"])
    assert ranked[0] is on_security


def test_ranking_orders_but_never_discards():
    """
    A claim on an unexpected page must still appear. GitLab genuinely states its
    FedRAMP position on the pricing page; dropping it would be the extractor
    overruling the vendor.
    """
    items = [
        Evidence("A", "SOC 2 stated here.", ["soc 2"], "body", "u1", "pricing"),
        Evidence("B", "SOC 2 stated here too.", ["soc 2"], "body", "u2", "security"),
    ]
    assert len(rank_evidence(items, ["security", "pricing"], ["security"])) == 2


# ---------------------------------------------------------------------------
# DEFECT 15 — the 40-character floor measured the block, not the claim.
# docs/confidence_rules.md always said "a fragment such as 'SOC 2 and 3' is a
# label, not a claim", but a bullet list concatenates past 40 characters and
# scored High. GitLab's uptime field scored High on the pricing feature bullet
# "Advanced CI/CD Team Project Management SLA Management Priority Support".
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("GitLab maintains a SOC 2 Type 2 report for the Security, Confidentiality "
     "and Availability Trust Services Criteria for GitLab.com.", 129),
    ("Advanced CI/CD Team Project Management SLA Management Priority Support", 0),
    ("Includes $12 in GitLab Credits per user per month*", 0),
    ("SOC 2 and 3. PCI DSS. HIPAA.", 12),
    ("", 0),
])
def test_a_claim_is_measured_as_a_sentence_not_as_a_block(text, expected):
    from src.parse import longest_sentence_length
    assert longest_sentence_length(text) == expected


def test_a_feature_bullet_list_cannot_score_high():
    from src.parse import score_field_confidence
    bullet_list = Evidence(
        heading="Everything from Free, plus:",
        snippet="Advanced CI/CD Team Project Management SLA Management Priority Support",
        matched_terms=["sla"], match_location="body",
        source_url="https://x/pricing/", source_type="pricing")
    assert score_field_confidence([bullet_list], ["pricing"]) == "Medium"


def test_a_real_sentence_on_an_authoritative_page_still_scores_high():
    from src.parse import score_field_confidence
    claim = Evidence(
        heading="SOC Certification",
        snippet="GitLab maintains a SOC 2 Type 2 report for the Security, "
                "Confidentiality and Availability Trust Services Criteria "
                "for GitLab.com.",
        matched_terms=["soc 2"], match_location="body",
        source_url="https://x/security/", source_type="security")
    assert score_field_confidence([claim], ["security"]) == "High"


def test_the_quote_and_the_confidence_never_disagree(settings, field_dictionary):
    """
    The coherence property. `value` is taken from evidence[0], and the field's
    confidence is the best level across ALL evidence — so unless ranking puts a
    top-scoring item first, a brief can print "High" above a quote worth only
    Medium. Ranking scores first for exactly this reason; this test pins it.
    """
    from src.parse import evidence_level
    authoritative = settings["confidence"]["authoritative_source_types"]
    min_high = settings["extraction"]["min_body_chars_for_high"]

    weak_but_preferred = Evidence("Tier", "SLA Management Priority Support",
                                  ["sla"], "body", "u1", "status")
    strong_elsewhere = Evidence(
        "Reliability",
        "We commit to a 99.9% uptime SLA for all Enterprise customers, measured "
        "monthly and published on our status page.",
        ["sla", "uptime"], "body", "u2", "security")

    ranked = rank_evidence([weak_but_preferred, strong_elsewhere],
                           authoritative, ["status", "security"], min_high)
    top = evidence_level(ranked[0], authoritative, min_high)
    overall = max((evidence_level(e, authoritative, min_high) for e in ranked),
                  key=["Low", "Medium", "High"].index)
    assert top == overall, "the quoted evidence is weaker than the printed confidence"


# ---------------------------------------------------------------------------
# DEFECT 16 — raw_html_path was absolute, so a corpus only replayed on the
# machine that produced it.
# ---------------------------------------------------------------------------

def test_resolve_html_path_rescues_a_foreign_absolute_path(tmp_path):
    cache = tmp_path / "data" / "cache" / "html"
    cache.mkdir(parents=True)
    (cache / "v2_abc.html").write_text("<h1>hi</h1>", encoding="utf-8")

    foreign = r"C:\Users\SomeoneElse\repo\data\cache\html\v2_abc.html"
    found = resolve_html_path(foreign, tmp_path)
    assert found is not None and found.name == "v2_abc.html"


def test_resolve_html_path_accepts_a_repo_relative_path(tmp_path):
    cache = tmp_path / "data" / "cache" / "html"
    cache.mkdir(parents=True)
    (cache / "v2_abc.html").write_text("<h1>hi</h1>", encoding="utf-8")
    assert resolve_html_path("data/cache/html/v2_abc.html", tmp_path) is not None


def test_missing_html_is_reported_not_silently_skipped(tmp_path, settings,
                                                       field_dictionary):
    records = [{"source_type": "security", "source_url": "https://x/",
                "raw_html_path": "data/cache/html/does_not_exist.html"}]
    fields, steps = extract_for_vendor(records, field_dictionary, settings, tmp_path)
    assert any(s.action == "missing-html" for s in steps)
    assert all(f.status == "NOT_FOUND" for f in fields)


# ---------------------------------------------------------------------------
# DEFECTS 20 and 22 — orphan citations: an evidence card whose quoted text does
# not contain the term it says it matched. Measured on the real GitLab corpus:
# 8 of 92 evidence blocks were orphans before these fixes, 0 after.
#   20: the snippet was text[:600], so a match at character 900 was cut away.
#   22: the snippet was `body or alt_texts`, so an alt-text-only match on a block
#       that also had prose was quoted with the prose.
# ---------------------------------------------------------------------------

def test_snippet_window_follows_the_match_instead_of_the_start_of_the_block():
    from src.parse import snippet_around
    text = "Filler about scanning. " * 60 + "Our SLA is 99.9% on Enterprise plans."
    assert len(text) > 600
    excerpt = snippet_around(text, ["sla"], 600)
    assert "SLA" in excerpt, "the quote does not contain the term it matched"
    assert len(excerpt) <= 602, "window must respect snippet_max_chars (+ ellipses)"
    assert excerpt.startswith("…"), "an excerpt must be marked as an excerpt"


def test_short_block_is_quoted_whole_with_no_ellipses():
    from src.parse import snippet_around
    text = "We maintain a SOC 2 Type 2 report."
    assert snippet_around(text, ["soc 2"], 600) == text


def test_alt_text_match_quotes_the_alt_text_not_the_prose():
    """
    GitLab's real "VPAT Compliance" block: prose about accessibility, image
    alt-text mentioning GDPR. Quoting the prose produced a card that read
    "matched gdpr" above a sentence with no GDPR in it.
    """
    html = ('<h3>VPAT Compliance</h3>'
            '<p>Our Accessibility Conformance Report shows our commitment.</p>'
            '<img alt="GDPR compliance badge">')
    hits = find_evidence(page_to_blocks(html), terms=["gdpr"])
    assert len(hits) == 1
    assert hits[0].match_location == "alt_text_only"
    assert "gdpr" in hits[0].snippet.lower(), hits[0].snippet


def test_no_evidence_card_cites_a_term_its_quote_does_not_contain(
        settings, field_dictionary):
    """
    The general property, asserted over every fixture. This is the test that
    would have caught both defects, and it is written as a property rather than
    as two examples so the next variant of the same mistake also fails here.
    """
    for fixture in sorted(FIXTURES.glob("*.html")):
        blocks = page_to_blocks(fixture.read_text(encoding="utf-8"))
        for name, spec in field_dictionary.items():
            for e in find_evidence(blocks, spec["terms"],
                                   spec.get("negative_terms"),
                                   settings["extraction"]["snippet_max_chars"]):
                shown = (e.snippet + " " + e.heading).lower()
                assert any(term_in(t, shown) for t in e.matched_terms), (
                    f"{fixture.name} / {name}: card cites {e.matched_terms} but "
                    f"shows {e.snippet[:80]!r}")


# ---------------------------------------------------------------------------
# value is a QUOTE, not a summary
# ---------------------------------------------------------------------------

def test_value_is_copied_verbatim_from_the_page():
    block = ("Our platform is fast and reliable. "
             "Example maintains a SOC 2 Type 2 report for the Security criteria. "
             "Contact sales for details.")
    chosen = best_sentence(block, ["soc 2 type 2"])
    assert chosen in block
    assert chosen.startswith("Example maintains")


def test_short_fragment_falls_back_to_the_whole_block():
    """
    "SOC 2 and 3" alone tells a reviewer nothing about what was claimed, so the
    surrounding block is returned instead. This is Postman's real page shape.
    """
    block = "We comply with: SOC 2 and 3. PCI DSS. HIPAA."
    assert best_sentence(block, ["soc 2 and 3"]) == block


# ---------------------------------------------------------------------------
# Housekeeping rules the brief depends on
# ---------------------------------------------------------------------------

def test_repeated_boilerplate_counts_once():
    same = [Evidence("Trust", "We are SOC 2 compliant.", ["soc 2"], "body",
                     f"https://x/{n}", "docs") for n in range(5)]
    assert len(dedupe_evidence(same)) == 1


@pytest.mark.parametrize("confidence,expected", [
    ("High", "FOUND"), ("Medium", "FOUND"),
    ("Low", "PARTIAL"), ("NOT_FOUND", "NOT_FOUND"),
])
def test_status_never_reports_a_hint_as_a_finding(confidence, expected):
    assert status_from_confidence(confidence) == expected


def test_atlassian_logos_never_reach_found(settings, field_dictionary):
    """
    The project's regression guard, restated at the Agent 2 level: a vendor
    whose certifications are images must come out PARTIAL, never FOUND.
    """
    from src.parse import score_field_confidence
    html = (FIXTURES / "atlassian_style.html").read_text(encoding="utf-8")
    hits = find_evidence(page_to_blocks(html),
                         terms=field_dictionary["security_trust"]["terms"],
                         source_type="security")
    alt_only = [e for e in hits if e.match_location == "alt_text_only"]
    assert alt_only, "the fixture should still produce an alt-text-only match"
    level = score_field_confidence(
        alt_only, settings["confidence"]["authoritative_source_types"])
    assert status_from_confidence(level) == "PARTIAL"


def test_every_field_declares_where_it_belongs(field_dictionary):
    """Ranking depends on this key; a field added without it silently loses."""
    for name, spec in field_dictionary.items():
        assert spec.get("preferred_source_types"), f"{name} has no preferred_source_types"


def test_not_found_is_recorded_with_the_effort_behind_it(tmp_path, settings,
                                                         field_dictionary):
    """
    A NOT_FOUND with no evidence of effort is a shrug, not a finding. The audit
    trail must say how many terms were tried across how many pages.
    """
    html_dir = tmp_path / "data" / "cache" / "html"
    html_dir.mkdir(parents=True)
    (html_dir / "p.html").write_text("<h1>Nothing relevant</h1><p>Hello.</p>",
                                     encoding="utf-8")
    records = [{"source_type": "product", "source_url": "https://x/",
                "raw_html_path": "data/cache/html/p.html"}]
    _, steps = extract_for_vendor(records, field_dictionary, settings, tmp_path)
    no_match = [s for s in steps if s.action == "no-match"]
    assert no_match
    assert "terms across" in no_match[0].detail and "page(s)" in no_match[0].detail


# ---------------------------------------------------------------------------
# Real corpus, if one is present. Skipped on a fresh clone.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not (ROOT / "data" / "corpus" / "gitlab.json").exists(),
                    reason="no collected corpus on disk yet")
def test_gitlab_security_field_quotes_the_soc_2_sentence(settings, field_dictionary):
    """
    The headline regression test: on the real GitLab corpus the security field
    must quote GitLab's own SOC 2 sentence — not a status board, not a pricing
    tier. This exact assertion would have caught defects 13 and 14 on day one.
    """
    records = json.loads((ROOT / "data" / "corpus" / "gitlab.json")
                         .read_text(encoding="utf-8"))
    fields, _ = extract_for_vendor(records, field_dictionary, settings, ROOT)
    security = next(f for f in fields if f.name == "security_trust")
    assert security.confidence == "High"
    assert "SOC 2 Type 2" in security.value
    assert security.evidence[0]["source_type"] == "security"


# ---------------------------------------------------------------------------
# DEFECT 23 — a page can be collected successfully and contain no readable text.
#
# Atlassian's Jira product page: 898 KB of HTML, 52 characters of visible text,
# ZERO heading blocks, HTTP 200, robots-allowed, cached cleanly. Its pricing
# page: 138 characters from 1.2 MB. Both are JavaScript-rendered, which this
# prototype deliberately does not run.
#
# Unrecorded, every field sourced from such a page reports NOT_FOUND, and the
# brief then tells a procurement team that Atlassian does not publish pricing.
# Atlassian publishes it perfectly well. Those are different findings and only
# one of them is true — so this is the one bug in this project that would put a
# false statement about a real company into a client-facing document.
# ---------------------------------------------------------------------------

def _unreadable_record(source_type: str = "product") -> dict:
    return {"source_type": source_type, "source_url": "https://x/", "raw_html_path": "",
            "content_usable": False, "block_count": 0}


def test_unusable_page_is_not_counted_as_searched(tmp_path, settings, field_dictionary):
    html_dir = tmp_path / "data" / "cache" / "html"
    html_dir.mkdir(parents=True)
    (html_dir / "real.html").write_text(
        "<h1>Security</h1><p>We maintain a SOC 2 Type 2 report for our platform "
        "covering security and availability criteria.</p>", encoding="utf-8")

    records = [
        {"source_type": "security", "source_url": "https://x/security",
         "raw_html_path": "data/cache/html/real.html", "content_usable": True,
         "block_count": 1},
        _unreadable_record("pricing"),
    ]
    fields, steps = extract_for_vendor(records, field_dictionary, settings, tmp_path)

    assert any(s.action == "unusable-page" for s in steps), \
        "an unreadable page must appear in the audit trail, not vanish"
    parsed = [s for s in steps if s.action == "parse-page"]
    assert len(parsed) == 1, "the unreadable page must not be reported as parsed"

    no_match = [s for s in steps if s.action == "no-match"]
    assert no_match, "some field should have found nothing here"
    assert "CAUTION" in no_match[0].detail, \
        "a NOT_FOUND alongside an unreadable page must not read as a clean negative"
    assert "readable page(s)" in no_match[0].detail


def test_not_found_carries_the_caveat_into_the_brief_itself(tmp_path, settings,
                                                            field_dictionary):
    """
    A reviewer reads the brief, not the audit trail. If the corpus was partly
    unreadable, the field must say so where it will actually be seen.
    """
    fields, _ = extract_for_vendor([_unreadable_record()], field_dictionary,
                                   settings, tmp_path)
    empty = [f for f in fields if f.status == "NOT_FOUND"]
    assert empty, "nothing was readable, so every field must be NOT_FOUND"
    for f in empty:
        assert f.evidence, f"{f.name} reported a bare NOT_FOUND with no caveat"
        assert f.evidence[0]["match_location"] == "tool_limitation"
        assert "JavaScript" in f.evidence[0]["snippet"]


def test_a_clean_not_found_stays_clean_when_every_page_was_readable(
        tmp_path, settings, field_dictionary):
    """
    The other half of the property, and the one that stops the caveat becoming
    noise: when the whole corpus was readable, NOT_FOUND is a real finding about
    the vendor and must not be hedged.
    """
    html_dir = tmp_path / "data" / "cache" / "html"
    html_dir.mkdir(parents=True)
    (html_dir / "p.html").write_text(
        "<h1>About us</h1><p>We build project management software for teams who "
        "care about shipping work on time.</p>", encoding="utf-8")
    records = [{"source_type": "product", "source_url": "https://x/",
                "raw_html_path": "data/cache/html/p.html",
                "content_usable": True, "block_count": 1}]

    fields, steps = extract_for_vendor(records, field_dictionary, settings, tmp_path)
    no_match = [s for s in steps if s.action == "no-match"]
    assert no_match
    assert all("CAUTION" not in s.detail for s in no_match)
    for f in fields:
        if f.status == "NOT_FOUND":
            assert not f.evidence, f"{f.name} was hedged when it should be a clean negative"
