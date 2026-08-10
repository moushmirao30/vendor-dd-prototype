"""
test_parse.py — proves the extraction core behaves on the FIVE page shapes we
actually observed on real vendor sites on 2026-08-10.

These double as the project's "sample test cases" deliverable. Each test states
the vendor shape it represents and what the correct behaviour is.

Run with:  pytest -v
"""

from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.parse import page_to_blocks, find_evidence, score_field_confidence  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
CONFIG = Path(__file__).resolve().parents[1] / "config"

DICT = yaml.safe_load((CONFIG / "field_dictionary.yaml").read_text(encoding="utf-8"))
SETTINGS = yaml.safe_load((CONFIG / "settings.yaml").read_text(encoding="utf-8"))
AUTHORITATIVE = SETTINGS["confidence"]["authoritative_source_types"]


def evidence_for(fixture: str, field_name: str, source_type: str = "security"):
    """Helper: run the full parse -> match pipeline over one fixture file."""
    html = (FIXTURES / fixture).read_text(encoding="utf-8")
    blocks = page_to_blocks(html)
    spec = DICT[field_name]
    return blocks, find_evidence(
        blocks,
        terms=spec["terms"],
        negative_terms=spec.get("negative_terms"),
        snippet_max_chars=SETTINGS["extraction"]["snippet_max_chars"],
        source_type=source_type,
    )


# --------------------------------------------------------------------------
# SHAPE 1 — clean headings with real sentences (Linear)
# --------------------------------------------------------------------------
def test_linear_shape_gives_high_confidence_with_readable_evidence():
    blocks, ev = evidence_for("linear_style.html", "security_trust")
    assert len(blocks) >= 4, "should split into one block per <h2>"
    assert ev, "should find certification evidence"

    top = ev[0]
    assert top.heading == "SOC 2 compliance"
    assert "Service Organization Controls" in top.snippet
    assert top.match_location == "body"
    # Both spellings must be caught by the dictionary, not by a regex.
    assert "soc 2 type ii" in top.matched_terms or "soc 2" in top.matched_terms

    assert score_field_confidence(ev, AUTHORITATIVE) == "High"


def test_linear_shape_also_yields_residency_and_encryption():
    _, residency = evidence_for("linear_style.html", "data_residency")
    _, crypto = evidence_for("linear_style.html", "encryption")
    assert any("European Union" in e.snippet for e in residency)
    assert any("TLS 1.2" in e.snippet for e in crypto)


# --------------------------------------------------------------------------
# SHAPE 2 — certifications published as images (Atlassian). THE KEY TEST.
# --------------------------------------------------------------------------
def test_atlassian_shape_never_scores_high_on_alt_text_alone():
    _, ev = evidence_for("atlassian_style.html", "security_trust")
    assert ev, "alt-text should still be captured as a hint"
    assert all(e.match_location == "alt_text_only" for e in ev), (
        "certifications are images here; nothing should be reported as prose"
    )
    assert score_field_confidence(ev, AUTHORITATIVE) == "Low", (
        "REGRESSION GUARD: if this ever returns High, the extractor is "
        "presenting a picture as a written claim."
    )


# --------------------------------------------------------------------------
# SHAPE 3 — prose plus a bare list, unusual spelling (Postman)
# --------------------------------------------------------------------------
def test_postman_shape_matches_the_soc_2_and_3_spelling():
    _, ev = evidence_for("postman_style.html", "security_trust")
    all_terms = {t for e in ev for t in e.matched_terms}
    assert "soc 2 and 3" in all_terms, (
        "a regex written for 'SOC 2 Type II' would miss this entirely"
    )
    assert score_field_confidence(ev, AUTHORITATIVE) == "High"


def test_postman_shape_is_the_only_source_of_an_uptime_figure():
    _, ev = evidence_for("postman_style.html", "uptime_reliability")
    assert any("99.9% SLA" in e.snippet for e in ev)


# --------------------------------------------------------------------------
# SHAPE 4 — a heading names the standard, nothing explains it
# --------------------------------------------------------------------------
def test_heading_only_match_scores_medium_not_high():
    _, ev = evidence_for("headingonly_style.html", "security_trust")
    assert ev and ev[0].match_location == "heading_only"
    assert score_field_confidence(ev, AUTHORITATIVE) == "Medium"


# --------------------------------------------------------------------------
# SHAPE 5 — no headings anywhere; fallback path
# --------------------------------------------------------------------------
def test_div_only_page_still_captures_sentences():
    blocks, ev = evidence_for("divonly_style.html", "security_trust")
    assert all(b.heading == "(no heading)" for b in blocks)
    assert any("SOC 2 Type 2" in e.snippet for e in ev), (
        "GitLab spells it 'Type 2'; the dictionary must carry both spellings"
    )


# --------------------------------------------------------------------------
# NEGATIVE CASE — absence must be reported as absence, never invented
# --------------------------------------------------------------------------
def test_absent_information_returns_not_found():
    _, ev = evidence_for("headingonly_style.html", "pricing_availability")
    assert score_field_confidence(ev, AUTHORITATIVE) == "NOT_FOUND", (
        "the brief requires missing information to be flagged, not guessed"
    )


def test_secondary_page_type_caps_confidence_at_medium():
    """The same strong evidence found on a blog instead of a trust page is worth less."""
    _, ev = evidence_for("linear_style.html", "security_trust", source_type="blog")
    assert score_field_confidence(ev, AUTHORITATIVE) == "Medium"
