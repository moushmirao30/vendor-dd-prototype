"""
test_agent3.py — tests for the Brief Review Agent and the shared review rules.

READ THIS BEFORE ADDING A TEST HERE.
Of the 37 defects found in this project, the test suite caught one. The tests
that earn their place pin down a bug a human already found, so it cannot come
back quietly. Each test below names the defect or the client instruction it
guards.

Two of these guard something subtler than a bug: they guard a SAFEGUARD. Defect
34 was a caveat that had never once executed because nothing exercised the wiring
between Agent 1 and Agent 2. `test_conflict_detector_actually_fires` exists
because `conflicting_values` returns nothing on the whole real corpus — a
detector with a zero count is only trustworthy if something proves it can fire.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src.agent3_review import (product_category, review_vendor, save_brief,
                               load_brief, vendor_overview)
from src.review_rules import (claim_not_in_matched_sentence, conflicting_values,
                              confidence, field_coverage, gated_evidence,
                              off_home_evidence, terms_not_visible, vendor_score)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def settings() -> dict:
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def field_dictionary() -> dict:
    d = yaml.safe_load((ROOT / "config" / "field_dictionary.yaml").read_text(encoding="utf-8"))
    return d.get("fields", d)


def _field(name="security_trust", status="FOUND", conf="High", evidence=None):
    return {"name": name, "label": name.replace("_", " ").title(),
            "status": status, "value": "x", "confidence": conf,
            "evidence": evidence if evidence is not None else []}


def _card(source_type="security", snippet="We maintain a SOC 2 Type 2 report for our platform.",
          terms=("soc 2",), heading="Security", location="body"):
    return {"heading": heading, "snippet": snippet, "matched_terms": list(terms),
            "match_location": location, "source_url": "https://x/", "source_type": source_type}


CAVEAT = {"heading": "The page this fact belongs on could not be read", "snippet": "…",
          "matched_terms": [], "match_location": "tool_limitation",
          "source_url": "", "source_type": "-"}


# ---------------------------------------------------------------------------
# DEFECT 31 — the score counts what was found and never what was checked.
# Postman scored 10/10 High with four core fields resting on pages that returned
# no readable text; Sentry scored 10/10 High with every page read. Identical
# labels, entirely different evidence.
# ---------------------------------------------------------------------------

def test_coverage_separates_two_vendors_the_score_cannot_tell_apart():
    core = ["security_trust", "privacy_data_handling"]
    read = [_field("security_trust", evidence=[_card()]),
            _field("privacy_data_handling", evidence=[_card("privacy")])]
    unread = [_field("security_trust", evidence=[_card()]),
              _field("privacy_data_handling", evidence=[_card("security"), CAVEAT])]

    scores = {"High": 2, "Medium": 1, "Low": 0, "NOT_FOUND": 0}
    bands = {"High": 4, "Medium": 2}
    a = vendor_score(read, core, scores, bands)
    b = vendor_score(unread, core, scores, bands)

    assert a["score"] == b["score"] and a["band"] == b["band"], (
        "the premise of this test: the score cannot tell these apart")
    assert a["coverage"]["verified"] == 2
    assert b["coverage"]["verified"] == 1, "coverage must see what the score cannot"
    assert b["coverage"]["caveated"] == ["privacy_data_handling"]


def test_a_caveated_field_can_never_be_high_confidence(field_dictionary):
    """
    The client's confidence model, and the reason it closes defect 31.

    First Quadrant Labs, 13 Aug: High is "direct, explicit evidence from an
    authoritative official source, with the requested field clearly answered".
    A field whose own page could not be read does not meet that, whatever the
    sentence it quotes looks like.
    """
    f = _field("privacy_data_handling", evidence=[_card("security"), CAVEAT])
    level, why = confidence(f, field_dictionary, unusable_types=["privacy"])
    assert level == "Medium"
    assert "privacy" in why and "could not be read" in why


def test_evidence_on_its_own_home_page_with_no_caveat_is_high(field_dictionary):
    f = _field("security_trust", evidence=[_card("security")])
    level, why = confidence(f, field_dictionary, unusable_types=[])
    assert level == "High"
    assert "security" in why


def test_off_home_evidence_is_medium_not_high(field_dictionary):
    """GitLab: three of five core fields draw their strongest evidence from the
    privacy policy. Real match, weak finding."""
    f = _field("security_trust", evidence=[_card("pricing")])
    level, why = confidence(f, field_dictionary, unusable_types=[])
    assert level == "Medium"
    assert "pricing" in why
    assert off_home_evidence(f, field_dictionary) == ["pricing"]


def test_label_only_evidence_is_low(field_dictionary):
    f = _field("pricing_availability", status="PARTIAL", conf="Low",
               evidence=[_card("pricing", snippet="Pricing", terms=("pricing",),
                               location="heading_only")])
    level, _ = confidence(f, field_dictionary, unusable_types=[])
    assert level == "Low"


# ---------------------------------------------------------------------------
# CLIENT REQUEST, 13 Aug: "highlight conflicts or weak evidence"
# ---------------------------------------------------------------------------

def test_conflict_detector_actually_fires():
    """
    `conflicting_values` returns NOTHING across all seven real vendors. That is
    reported as a finding, not hidden — but a detector nobody has ever seen fire
    is exactly what defect 34 was. This proves it works on a constructed case.
    """
    f = _field("uptime_reliability", evidence=[
        _card("status", "We guarantee 99.9% monthly uptime.", ("uptime",)),
        _card("pricing", "Enterprise plans include a 99.99% uptime SLA.", ("uptime",)),
    ])
    conflicts = conflicting_values(f)
    assert conflicts, "differing uptime figures across two pages must be flagged"
    assert "99.9%" in conflicts[0] and "99.99%" in conflicts[0]
    assert "status" in conflicts[0] and "pricing" in conflicts[0]


def test_conflict_detector_is_silent_on_agreement():
    """The corresponding half: no false positives when the pages agree."""
    f = _field("uptime_reliability", evidence=[
        _card("status", "We guarantee 99.9% monthly uptime.", ("uptime",)),
        _card("pricing", "All plans carry a 99.9% uptime commitment.", ("uptime",)),
    ])
    assert conflicting_values(f) == []


def test_a_single_page_disagreeing_with_itself_is_not_a_conflict():
    """
    A NEGATION HEURISTIC WAS TRIED AND DELETED THE SAME HOUR. It fired on three
    of seven vendors and every hit was false — "negative on privacy, plain on
    privacy", because it compared three blocks of one privacy policy against each
    other. A privacy policy contains both "we do not sell your data" and ordinary
    positive statements; that is what a privacy policy is.
    """
    f = _field("privacy_data_handling", evidence=[
        _card("privacy", "We do not sell your personal data to third parties.", ("personal data",)),
        _card("privacy", "We share personal data with our sub-processors.", ("personal data",)),
    ])
    assert conflicting_values(f) == [], (
        "two blocks of the same page are not two sources disagreeing")


def test_gated_evidence_is_flagged():
    """Sentry publishes that its SOC 2 reports are available to customers on
    request. The evidence is real and the document is not public."""
    f = _field(evidence=[_card("security",
                               "Compliance reports are available to customers upon request.")])
    assert "upon request" in gated_evidence(f)


def test_cited_terms_the_reader_cannot_see_are_listed():
    """20 of 122 cards cite a term that falls outside the 600-character snippet.
    Not fabrication — all 42 are on the page — but unverifiable from the card."""
    card = _card(snippet="We hold SOC 2.", terms=("soc 2", "iso 27001", "hipaa"))
    assert terms_not_visible(card) == ["iso 27001", "hipaa"]


def test_claim_not_in_matched_sentence_detects_the_atlassian_shape():
    """
    Defect 37. `hipaa` appears only in a 39-character section title while the
    High was earned by a long sentence about something else in the same block.
    """
    card = _card(
        source_type="terms",
        snippet=("Customer is responsible for determining whether the Cloud Products are "
                 "appropriate for its regulatory obligations and intended use. "
                 "Sensitive Health Information and HIPAA."),
        terms=("hipaa",), heading="6. Customer Obligations")
    assert claim_not_in_matched_sentence(card, 40) == 39


def test_claim_in_matched_sentence_reports_nothing():
    card = _card(snippet="GitLab maintains a SOC 2 Type 2 report for the Security, "
                         "Confidentiality and Availability Trust Services Criteria.",
                 terms=("soc 2",))
    assert claim_not_in_matched_sentence(card, 40) is None


# ---------------------------------------------------------------------------
# The overview, and why it is a page title
# ---------------------------------------------------------------------------

def test_overview_is_the_product_page_title_not_mined_prose():
    """
    The first implementation mined the product page body and returned a CHANGELOG
    ENTRY for Linear. The title is written by the vendor to describe itself.
    """
    records = [{"source_type": "product", "page_title": "Linear – The system for product development",
                "source_url": "https://linear.app/", "content_usable": True}]
    text, url, readable = vendor_overview(records)
    assert text == "Linear – The system for product development"
    assert url == "https://linear.app/" and readable is True


def test_overview_survives_a_javascript_rendered_product_page():
    """
    Atlassian's product page yields 52 readable characters from 898 KB. A <title>
    lives in the HTML head and is served before any JavaScript runs, so the
    overview is still the vendor's own — and the caller is told the body was not.
    """
    records = [{"source_type": "product",
                "page_title": "Jira | Project Management for the AI Era | Atlassian",
                "source_url": "https://www.atlassian.com/software/jira",
                "content_usable": False}]
    text, _, readable = vendor_overview(records)
    assert "Atlassian" in text
    assert readable is False, "the caller must be able to say the body was unreadable"


def test_no_product_page_means_no_overview_not_a_substitute():
    assert vendor_overview([{"source_type": "pricing", "page_title": "Plans"}]) == ("", "", False)


def test_product_category_is_curated_not_extracted():
    assert product_category({"category": "developer productivity"}, "") == "developer productivity"
    assert product_category({}, "developer productivity tools") == "developer productivity tools"
    assert product_category({}, "") == "(not categorised)"


# ---------------------------------------------------------------------------
# End to end, on the real corpus if one is present
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not (ROOT / "data" / "corpus" / "postman_fields.json").exists(),
                    reason="no collected corpus on disk yet")
def test_postman_brief_warns_that_its_score_overstates_coverage(settings, field_dictionary):
    """
    The headline regression test for Agent 3, on real data. Postman scores
    10/10 -> High with core fields resting on a privacy policy of zero readable
    characters. The brief must say so where a reviewer will read it.
    """
    corpus = json.loads((ROOT / "data/corpus/postman.json").read_text(encoding="utf-8"))
    recs = corpus["records"] if isinstance(corpus, dict) and "records" in corpus else corpus
    fdata = json.loads((ROOT / "data/corpus/postman_fields.json").read_text(encoding="utf-8"))
    trail = json.loads((ROOT / "data/corpus/postman_run.json").read_text(encoding="utf-8"))

    brief, steps = review_vendor({"name": "Postman", "slug": "postman"}, fdata["fields"],
                                 recs, trail["steps"], field_dictionary, settings,
                                 "developer productivity tools")

    # DEFECT 42. Three axes, and Postman is the vendor that proves they differ:
    # maximum evidence, zero core fields at the client's High, coverage 2 of 5.
    assert brief.evidence_score == 10 and brief.evidence_band == "High"
    assert brief.confidence_counts["High"] == 0, (
        "Postman's five core fields all rest on caveated or off-home evidence; "
        "none may reach the client's High")
    assert brief.confidence_band != "High", (
        "the header must not call High what every field below calls Medium — "
        "that disagreement IS defect 42")
    assert brief.coverage_verified < brief.coverage_total, "coverage must be below the score"
    assert any("OVERSTATES COVERAGE" in f for f in brief.review_flags)
    assert any("unreadable" in f for f in brief.review_flags)
    assert any(s.action == "coverage" for s in steps)
    assert brief.disclaimer.startswith("FIRST-PASS")


@pytest.mark.skipif(not (ROOT / "data" / "corpus" / "jetbrains_run.json").exists(),
                    reason="no collected corpus on disk yet")
def test_jetbrains_brief_reports_the_page_that_was_never_located(settings, field_dictionary):
    """Defect 34, end to end: the `skip` step Agent 1 now emits must reach the
    reviewer as a sentence, not vanish."""
    corpus = json.loads((ROOT / "data/corpus/jetbrains.json").read_text(encoding="utf-8"))
    recs = corpus["records"] if isinstance(corpus, dict) and "records" in corpus else corpus
    fdata = json.loads((ROOT / "data/corpus/jetbrains_fields.json").read_text(encoding="utf-8"))
    trail = json.loads((ROOT / "data/corpus/jetbrains_run.json").read_text(encoding="utf-8"))

    brief, _ = review_vendor({"name": "JetBrains", "slug": "jetbrains"}, fdata["fields"],
                             recs, trail["steps"], field_dictionary, settings)
    assert any("terms" in f and "was ever located" in f for f in brief.review_flags), (
        f"expected the never-found wording; got {brief.review_flags}")


def test_brief_replays_from_disk(tmp_path):
    """Same replay contract as Agents 1 and 2 — the brief must survive a reload."""
    from src.schema import VendorBrief
    from src.agent3_review import ReviewStep
    brief = VendorBrief(vendor_name="X", vendor_slug="x", evidence_score=7,
                        evidence_band="Medium", confidence_band="Medium",
                        confidence_counts={"High": 1, "Medium": 3, "Low": 1},
                        coverage_verified=3, coverage_total=5)
    save_brief(brief, tmp_path, [ReviewStep("coverage", "-", "7/10 on 3 of 5")])
    back = load_brief(tmp_path, "x")
    assert back["evidence_score"] == 7 and back["coverage_verified"] == 3
    assert back["confidence_counts"]["High"] == 1, "all three axes must survive a reload"
    assert back["steps"][0]["action"] == "coverage"
    assert load_brief(tmp_path, "never-reviewed") is None
