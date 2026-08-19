"""
test_export.py — tests for the export layer and the client's source manifest.

Each test names the requirement or the defect it guards. Two guard decisions
that look cosmetic and are not: the CSV round-trip (because "CSV as the store
corrupts data silently" is a locked decision that only means something if the
export is proven not to), and the coverage-beside-score rule (because a brief
that prints 10/10 alone reproduces the failure the whole project reports).
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.export import (BRIEF_COLUMNS, CORPUS_COLUMNS, brief_to_markdown,
                        export_brief, export_brief_csv, export_corpus_csv,
                        export_source_manifest, source_manifest_rows)


def _brief(**over) -> dict:
    b = {
        "vendor_name": "Postman", "vendor_slug": "postman", "generated_on": "2026-08-19",
        "vendor_overview": "Postman API Platform - Build, Test & Manage",
        "product_category": "developer productivity tools",
        "key_sources": ["https://www.postman.com/"],
        "evidence_score": 10, "evidence_band": "High",
        "confidence_band": "Medium",
        "confidence_counts": {"High": 0, "Medium": 5, "Low": 0},
        "coverage_verified": 2, "coverage_total": 5,
        "coverage_caveated": ["privacy_data_handling"],
        "missing_or_unclear": [], "review_flags": [],
        "disclaimer": "FIRST-PASS INTERNAL RESEARCH AID. …",
        "fields": {
            "security_trust": {
                "label": "Security and trust information", "status": "FOUND",
                "confidence": "High", "extraction_quality": "High",
                "confidence_reason": "stated directly on the vendor's own security page",
                "value": "All compliance documents are available.",
                "evidence": [{
                    "heading": "Compliance", "snippet": "We hold SOC 2.",
                    "matched_terms": ["soc 2", "iso 27001", "hipaa"],
                    "terms_not_shown": ["iso 27001", "hipaa"],
                    "match_location": "body", "source_type": "security",
                    "source_url": "https://www.postman.com/trust/security/",
                }],
            },
        },
    }
    b.update(over)
    return b


# ---------------------------------------------------------------------------
# CSV is an export, never the store — the locked decision, proven
# ---------------------------------------------------------------------------

def test_page_text_survives_a_csv_round_trip(tmp_path):
    """
    Page text contains commas, quotation marks and newlines. That is why JSON is
    canonical and CSV is only ever written out. This proves the export does not
    corrupt what the store protects.
    """
    nasty = 'GitLab said: "we maintain SOC 2, Type 2".\nAcross\r\nlines, with, commas.'
    records = [{"vendor_name": "GitLab", "source_url": "https://about.gitlab.com/",
                "source_type": "security", "page_title": 'Security | "GitLab", Inc.',
                "collected_text": nasty, "date_collected": "2026-08-13",
                "tags": ["security", "human-verified"], "evidence_note": "x, y",
                "http_status": 200, "content_usable": True}]
    path = export_corpus_csv(records, tmp_path / "corpus.csv")

    with path.open(encoding="utf-8-sig", newline="") as fh:
        back = list(csv.DictReader(fh))
    assert len(back) == 1, "embedded newlines must not split one page into two rows"
    assert back[0]["collected_text"] == nasty
    assert back[0]["page_title"] == 'Security | "GitLab", Inc.'
    assert back[0]["tags"] == "security, human-verified"
    assert back[0]["source_url"].startswith("http"), "no column drift"


def test_corpus_csv_leads_with_the_columns_the_brief_names():
    """The brief lists eight corpus fields by name. A reviewer reading left to
    right should meet those first, and our additions after."""
    assert CORPUS_COLUMNS[:8] == ["vendor_name", "source_url", "source_type",
                                  "page_title", "collected_text", "date_collected",
                                  "tags", "evidence_note"]


# ---------------------------------------------------------------------------
# THE SOURCE MANIFEST — new deliverable, client instruction of 18 Aug 2026
# ---------------------------------------------------------------------------

def test_manifest_records_a_page_type_that_was_never_collected():
    """
    JetBrains' terms page 404'd three times and has NO corpus row. Built from the
    corpus alone the manifest would silently claim we never wanted it — which is
    the whole reason the client asked for a manifest rather than a file listing.
    """
    steps = [{"action": "discovered", "source_type": "terms",
              "url": "https://www.jetbrains.com/terms", "status": 404, "outcome": "HTTP 404"},
             {"action": "skip", "source_type": "terms",
              "url": "(no seed - discovery only)", "status": 0,
              "outcome": "NOT COLLECTED - flag for manual follow-up"}]
    rows = source_manifest_rows("JetBrains", [], steps)
    outcomes = [r[3] for r in rows]
    assert "FAILED" in outcomes, "each failed URL attempt must be visible"
    assert "NOT COLLECTED" in outcomes, "the conclusion must be visible too"
    never = next(r for r in rows if r[3] == "NOT COLLECTED")
    assert "not evidence the vendor publishes nothing" in never[-1]


def test_manifest_marks_a_collected_but_unreadable_page_as_unusable():
    """Postman's privacy policy: HTTP 200, cached cleanly, zero readable text.
    'Collected' and 'usable' are different facts and the manifest says both."""
    rec = {"source_url": "https://www.postman.com/legal/privacy-policy/",
           "source_type": "privacy", "page_title": "Privacy Policy | Postman",
           "date_collected": "2026-08-13", "http_status": 200, "block_count": 0,
           "content_sha256": "abc123", "content_usable": False}
    steps = [{"action": "curated-seed", "source_type": "privacy",
              "url": rec["source_url"], "status": 200, "outcome": "found"}]
    row = source_manifest_rows("Postman", [rec], steps)[0]
    assert row[3] == "COLLECTED BUT UNREADABLE"
    assert row[5] == "no"
    assert "OUR limit" in row[-1]


def test_manifest_marks_a_good_page_usable(tmp_path):
    rec = {"source_url": "https://about.gitlab.com/security/", "source_type": "security",
           "page_title": "Security", "date_collected": "2026-08-13", "http_status": 200,
           "block_count": 22, "content_sha256": "deadbeefdeadbeef", "content_usable": True}
    steps = [{"action": "curated-seed", "source_type": "security",
              "url": rec["source_url"], "status": 200, "outcome": "found"}]
    rows = source_manifest_rows("GitLab", [rec], steps)
    assert rows[0][3] == "COLLECTED" and rows[0][5] == "yes"
    path = export_source_manifest(rows, tmp_path / "m.csv")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        assert list(csv.DictReader(fh))[0]["usable_as_evidence"] == "yes"


# ---------------------------------------------------------------------------
# THE BRIEF — the score is never alone, the citation is never unverifiable
# ---------------------------------------------------------------------------

def test_markdown_never_prints_the_score_without_coverage():
    """
    Defect 31, at the last possible moment, extended for defect 42.

    Postman scores 10/10 on evidence with core fields resting on pages nobody
    could read, and ZERO core fields at the client's High. A brief showing only
    the 10/10 reproduces the exact failure this project exists to report.

    This used to assert that coverage sat on the SAME LINE as the score — the
    mechanism, not the property. The property is that a reader cannot reach a
    single field without passing all three axes, and asserting the mechanism made
    the correct fix look like a regression (defect 35's lesson). So the test now
    asserts the property: evidence, confidence and coverage all appear in the
    header, ABOVE the first field.
    """
    md = brief_to_markdown(_brief())
    header = md.split("## Fields")[0]

    assert "10/10" in header, "the evidence score belongs in the header"
    assert "2/5" in header, "coverage must be unavoidable before any field is read"
    assert "0 of 5 core fields High" in header, (
        "the client's confidence axis must appear at vendor level — its absence "
        "there IS defect 42")
    assert "Read all three" in header
    assert "privacy_data_handling" in md, "name the caveated fields, do not just count them"

    # And the ordering: no field may be readable before all three axes have been.
    assert md.index("10/10") < md.index("## Fields")
    assert md.index("0 of 5 core fields High") < md.index("## Fields")
    assert md.index("2/5") < md.index("## Fields")


def test_markdown_cites_only_terms_the_reader_can_see():
    """
    20 of 122 cards cite a term outside the 600-character snippet. All 42 are on
    the page — not fabrication — but unverifiable from the card. Agent 3 marks
    them; the export must not print them as if they were quoted.
    """
    md = brief_to_markdown(_brief())
    assert "matched soc 2 (+2 more term(s) on the page, outside this quote)" in md
    assert "matched soc 2, iso 27001, hipaa" not in md, (
        "a term the reader cannot find in the quote must not be cited as if visible")


def test_markdown_carries_the_disclaimer_and_the_overview_provenance():
    md = brief_to_markdown(_brief())
    assert "FIRST-PASS INTERNAL RESEARCH AID" in md
    assert "quoted from the vendor's own product page" in md
    assert "_(curated, not extracted)_" in md, (
        "the category is a human judgement and must not read as evidence")


def test_markdown_shows_caveats_as_warnings_not_as_evidence():
    b = _brief()
    b["fields"]["security_trust"]["evidence"].append({
        "heading": "The page this fact belongs on could not be read",
        "snippet": "Verify by hand.", "matched_terms": [],
        "match_location": "tool_limitation", "source_type": "-", "source_url": ""})
    md = brief_to_markdown(b)
    assert "⚠ *The page this fact belongs on could not be read*" in md


def test_brief_csv_carries_the_source_url_on_every_row(tmp_path):
    """The brief names "review notes not always linked back to the original
    public source" as a flaw of the manual process. A CSV row without its URL
    would reintroduce it."""
    path = export_brief_csv(_brief(), tmp_path / "b.csv")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["source_url"].startswith("https://")
    assert rows[0]["confidence"] == "High" and rows[0]["extraction_quality"] == "High"
    assert "confidence_reason" in BRIEF_COLUMNS


@pytest.mark.parametrize("fmt,suffix", [("json", ".json"), ("csv", ".csv"),
                                        ("markdown", ".md")])
def test_export_brief_dispatches_by_format(tmp_path, fmt, suffix):
    path = export_brief(_brief(), tmp_path, fmt)
    assert path.name == f"postman_brief{suffix}" and path.exists()


def test_unknown_export_format_fails_loudly(tmp_path):
    """A silent no-op would let a missing deliverable reach submission."""
    with pytest.raises(ValueError, match="unknown export format"):
        export_brief(_brief(), tmp_path, "pdf")


def test_the_ui_download_and_the_file_on_disk_are_the_same_bytes(tmp_path):
    """
    The Export tab tells the reviewer, on screen, that the file they download is
    byte-identical to the one `tools/export_all.py` writes. That sentence is a
    claim, and an unverified claim printed in the product is the shape of every
    defect in this project.

    Verified against all seven real briefs on 18 Aug 2026 before the sentence was
    written. This test keeps it true: the encoding (utf-8-sig, for Excel) and the
    line terminator (\\r\\n, from csv.writer's default) both have to match, and
    either could drift silently.
    """
    from src.export import brief_to_csv, export_brief_csv

    brief = _brief()
    on_disk = export_brief_csv(brief, tmp_path / "b.csv").read_bytes()
    from_ui = brief_to_csv(brief).encode("utf-8-sig")
    assert from_ui == on_disk, (
        "the CSV offered by the download button diverged from the exported file")
