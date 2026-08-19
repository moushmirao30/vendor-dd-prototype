"""
export.py — turn the workflow's output into the files that get submitted.

WHAT THE BRIEF ASKS FOR
-----------------------
    "export the result as JSON, CSV, or Markdown"
    "structured public-source vendor corpus in CSV/JSON/SQLite format"

WHAT THE CLIENT ADDED IN WRITING, 18 August 2026
------------------------------------------------
They asked us NOT to ship the 22 MB cache of verbatim third-party HTML, and to
submit instead:

    the structured CSV/JSON/SQLite corpus · source URLs and page titles · date
    collected · relevant extracted sections/evidence snippets · source type and
    tags · collection/retrieval code · **a source manifest showing which pages
    were successfully or unsuccessfully collected**

That last item is a NEW DELIVERABLE, not in the original brief, and it is the
reason this file has a fourth exporter. Every field it needs is already in
Agent 1's audit trail; nothing new has to be collected.

THE MANIFEST IS THE HONEST HALF OF THE SUBMISSION
-------------------------------------------------
Without the HTML cache, a reviewer cannot re-derive what we saw. The manifest is
what replaces it: one row per page we TRIED, not per page we kept — including the
404s, the pages that returned megabytes of JavaScript and no words, and the page
types we never located at all. A corpus alone shows what worked. A corpus plus a
manifest shows what was attempted, which is the only way a reader can judge
whether "not found" means the vendor is silent or means we could not look.

WHY CSV IS AN EXPORT AND NEVER THE STORE
----------------------------------------
Page text contains commas, quotation marks and newlines. Using CSV as the primary
store corrupts data silently — a locked decision from day 2. JSON stays canonical;
these functions read it and write CSV out. `csv.writer` quotes correctly; the
round-trip test in `tests/test_export.py` proves a quote survives a comma and a
newline in the same cell.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

# Exactly the corpus columns the project brief names, in the order it names them.
# Extra fields Agent 1 records for auditability follow after, so a reviewer
# reading left to right sees the required set first.
CORPUS_COLUMNS = [
    "vendor_name", "source_url", "source_type", "page_title", "collected_text",
    "date_collected", "tags", "evidence_note",
    # --- auditability, beyond the brief ---
    "http_status", "fetch_ok", "robots_allowed", "content_usable", "block_count",
    "content_sha256", "text_extractor",
]

MANIFEST_COLUMNS = [
    "vendor", "source_type", "attempted_url", "outcome", "http_status",
    "usable_as_evidence", "page_title", "date_collected", "readable_blocks",
    "content_sha256", "note",
]


def _row(record: dict, columns: list[str]) -> list:
    out = []
    for c in columns:
        v = record.get(c, "")
        out.append(", ".join(v) if isinstance(v, list) else v)
    return out


def _write_csv(path: Path, columns: list[str], rows: list[list]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="" is required by the csv module on Windows; without it every row
    # is followed by a blank line and the file looks corrupt in Excel.
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        w.writerow(columns)
        w.writerows(rows)
    return path


# utf-8-sig, not utf-8, above: Excel on Windows opens a plain UTF-8 CSV as
# Latin-1 and turns every quotation mark in a vendor's prose into mojibake. The
# BOM costs three bytes and prevents the reviewer's first impression of this
# corpus being "the text is broken" (defect 8 taught this the hard way, in the
# other direction).


# ---------------------------------------------------------------------------
# 1. The corpus
# ---------------------------------------------------------------------------

def export_corpus_csv(records: list[dict], out_path: Path) -> Path:
    """One row per collected page, carrying the brief's named fields."""
    return _write_csv(out_path, CORPUS_COLUMNS, [_row(r, CORPUS_COLUMNS) for r in records])


# ---------------------------------------------------------------------------
# 2. The source manifest — the client's new deliverable
# ---------------------------------------------------------------------------

def source_manifest_rows(vendor_name: str, records: list[dict],
                         collection_steps: list[dict]) -> list[list]:
    """
    One row per page ATTEMPTED, built from Agent 1's audit trail.

    The trail is the right source rather than the corpus, because the corpus by
    definition contains only what succeeded. JetBrains' terms page — three 404s
    and never resolved — has no corpus row and must still appear here, or the
    manifest would quietly claim we never wanted it.
    """
    by_url = {r.get("source_url", ""): r for r in records}
    rows: list[list] = []
    seen: set[tuple[str, str]] = set()

    for step in collection_steps:
        stype = step.get("source_type", "?")
        url = step.get("url", "")
        action = step.get("action", "")
        outcome = step.get("outcome", "")
        key = (stype, url)

        if action == "skip":
            rows.append([vendor_name, stype, url or "(no seed - discovery only)",
                         "NOT COLLECTED", step.get("status", 0), "no", "", "", "",
                         "", "every candidate URL failed - our URL guess was wrong, "
                         "which is not evidence the vendor publishes nothing"])
            continue
        if action == "budget-stop":
            rows.append([vendor_name, stype, url, "NOT ATTEMPTED", 0, "no", "", "",
                         "", "", outcome])
            continue
        if action == "unusable-page":
            continue  # folded into the collected row below, not a separate attempt

        rec = by_url.get(step.get("url", "")) or by_url.get(url)
        if step.get("status") == 200 and rec:
            if key in seen:
                continue
            seen.add(key)
            usable = rec.get("content_usable") is not False
            rows.append([
                vendor_name, stype, rec.get("source_url", url),
                "COLLECTED" if usable else "COLLECTED BUT UNREADABLE",
                rec.get("http_status", 200), "yes" if usable else "no",
                rec.get("page_title", ""), rec.get("date_collected", ""),
                rec.get("block_count", 0), rec.get("content_sha256", "")[:16],
                "" if usable else "JavaScript-rendered: any missing field from this "
                                  "page is OUR limit, not the vendor's silence",
            ])
        else:
            rows.append([vendor_name, stype, url, "FAILED", step.get("status", 0),
                         "no", "", "", "", "", outcome])
    return rows


def export_source_manifest(rows: list[list], out_path: Path) -> Path:
    """Write the manifest. Pass rows from every vendor for one combined file."""
    return _write_csv(out_path, MANIFEST_COLUMNS, rows)


# ---------------------------------------------------------------------------
# 3. The brief — JSON, CSV, Markdown
# ---------------------------------------------------------------------------

BRIEF_COLUMNS = [
    "vendor_name", "field", "label", "status", "confidence", "extraction_quality",
    "confidence_reason", "value", "source_type", "source_url", "matched_terms",
]


def export_brief_json(brief: dict, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def brief_csv_rows(brief: dict) -> list[list]:
    """
    One row per field. The top evidence card's URL travels with it, because a
    CSV row without its source is exactly the "review note not linked back to
    the original public source" the brief names as a problem with the manual
    process this prototype replaces.
    """
    rows = []
    for name, f in brief.get("fields", {}).items():
        top = next((e for e in f.get("evidence", [])
                    if e.get("match_location") != "tool_limitation"), {})
        rows.append([
            brief.get("vendor_name", ""), name, f.get("label", ""), f.get("status", ""),
            f.get("confidence", ""), f.get("extraction_quality", ""),
            f.get("confidence_reason", ""), f.get("value", ""),
            top.get("source_type", ""), top.get("source_url", ""),
            ", ".join(top.get("matched_terms", []) or []),
        ])
    return rows


def brief_to_csv(brief: dict) -> str:
    """
    The same CSV as `export_brief_csv`, returned as text.

    ADDED 18 Aug 2026 FOR THE UI DOWNLOAD BUTTON, AND FACTORED RATHER THAN
    RE-WRITTEN. Streamlit's `st.download_button` wants bytes, not a file on
    disk. Building the CSV a second time inside `app.py` would mean the file a
    reviewer downloads from the screen and the file in `data/exports/` could
    drift — and "two things that are supposed to agree, drifting apart because
    nobody made them share code" is defects 15, 36, 41 and 42 in this project
    already. One row builder, two destinations.

    utf-8-sig is applied by the caller writing bytes; this returns str.
    """
    buf = io.StringIO(newline="")
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    w.writerow(BRIEF_COLUMNS)
    w.writerows(brief_csv_rows(brief))
    return buf.getvalue()


def export_brief_csv(brief: dict, out_path: Path) -> Path:
    """One row per field, written to disk. See `brief_csv_rows` for the shape."""
    return _write_csv(out_path, BRIEF_COLUMNS, brief_csv_rows(brief))


def brief_to_markdown(brief: dict) -> str:
    """
    The reviewer-facing brief.

    It is laid out to walk the chain the client asked the interface to show —
    **Source → Extracted Evidence → Structured Field → Confidence → Review Flag →
    Final Brief** — because a reviewer reading a Markdown export should be able
    to follow the same path as one clicking through the app.

    THE SCORE IS NEVER PRINTED ALONE. Coverage sits on the same line, every time.
    Postman scores 10/10 with four core fields resting on pages nobody could
    read; Sentry scores 10/10 with every page read. A brief that showed only the
    number would reproduce the exact failure this project exists to report.
    """
    out = io.StringIO()
    w = out.write

    w(f"# Vendor research brief — {brief.get('vendor_name','')}\n\n")
    w(f"> {brief.get('disclaimer','')}\n\n")

    overview = brief.get("vendor_overview") or "_no overview could be quoted_"
    w(f"**Overview (quoted from the vendor's own product page):** {overview}\n\n")
    w(f"**Category:** {brief.get('product_category','')} _(curated, not extracted)_\n\n")
    w(f"**Generated:** {brief.get('generated_on','')}\n\n")

    # THREE NUMBERS, THREE QUESTIONS (defect 42). This header used to print a
    # single figure called "Confidence" that measured evidence VOLUME, sitting
    # above fields that each carried the client's confidence rule and frequently
    # disagreed with it — Postman's header said High while all five of its core
    # fields said Medium.
    score, band = brief.get("evidence_score", 0), brief.get("evidence_band", "")
    counts = brief.get("confidence_counts") or {}
    cband = brief.get("confidence_band", "")
    ver, tot = brief.get("coverage_verified", 0), brief.get("coverage_total", 0)
    w("## How to read this brief\n\n")
    w("| Measure | Value | What it answers |\n|---|---|---|\n")
    w(f"| **Evidence** | {score}/10 → {band} | how much quotable material was found |\n")
    w(f"| **Confidence** | {cband} — {counts.get('High', 0)} of {tot} core fields High, "
      f"{counts.get('Medium', 0)} Medium, {counts.get('Low', 0)} Low | how good that "
      f"evidence is, on the client's definition |\n")
    w(f"| **Coverage** | {ver}/{tot} core fields verified | how much we could actually "
      f"check |\n\n")
    w(f"> **Read all three.** A vendor can score {score}/10 on evidence while most of its "
      f"primary documents were never readable. Confidence is the WEAKEST core field, not an "
      f"average — a first-pass brief is only as trustworthy as the weakest field a reviewer "
      f"will act on.\n\n")
    if brief.get("coverage_caveated"):
        w(f"> {', '.join(brief['coverage_caveated'])} rest on pages that could not be read. "
          f"The evidence score counts what was found; it cannot count what was never "
          f"looked at.\n\n")

    w("## Fields\n\n")
    for name, f in brief.get("fields", {}).items():
        w(f"### {f.get('label', name)}\n\n")
        w(f"- **Status:** {f.get('status','')} · **Confidence:** {f.get('confidence','')} "
          f"· **Extraction quality:** {f.get('extraction_quality','')}\n")
        if f.get("confidence_reason"):
            w(f"- **Why:** {f['confidence_reason']}\n")
        if f.get("value"):
            w(f"\n> {f['value']}\n\n")
        for e in f.get("evidence", []):
            if e.get("match_location") == "tool_limitation":
                w(f"- ⚠ *{e.get('heading','')}* — {e.get('snippet','')}\n")
                continue
            shown = e.get("matched_terms") or []
            hidden = e.get("terms_not_shown") or []
            visible = [t for t in shown if t not in hidden]
            cite = ", ".join(visible) or "—"
            extra = f" (+{len(hidden)} more term(s) on the page, outside this quote)" if hidden else ""
            w(f"- `{e.get('source_type','')}` — matched {cite}{extra} — "
              f"[{e.get('source_url','')}]({e.get('source_url','')})\n")
        w("\n")

    if brief.get("missing_or_unclear"):
        w("## Missing or unclear\n\n")
        for m in brief["missing_or_unclear"]:
            w(f"- {m}\n")
        w("\n")

    if brief.get("review_flags"):
        w("## Review flags — a human must act on these\n\n")
        for fl in brief["review_flags"]:
            w(f"- {fl}\n")
        w("\n")

    w("## Sources read\n\n")
    for s in brief.get("key_sources", []):
        w(f"- {s}\n")
    return out.getvalue()


def export_brief_markdown(brief: dict, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(brief_to_markdown(brief), encoding="utf-8")
    return out_path


EXPORTERS = {"json": export_brief_json, "csv": export_brief_csv,
             "markdown": export_brief_markdown}
EXTENSIONS = {"json": ".json", "csv": ".csv", "markdown": ".md"}


def export_brief(brief: dict, out_dir: Path, fmt: str) -> Path:
    """Dispatch by format name, as `settings.output.export_formats` lists them."""
    fmt = fmt.lower()
    if fmt not in EXPORTERS:
        raise ValueError(f"unknown export format {fmt!r}; expected one of "
                         f"{', '.join(sorted(EXPORTERS))}")
    slug = brief.get("vendor_slug") or brief.get("vendor_name", "vendor")
    return EXPORTERS[fmt](brief, out_dir / f"{slug}_brief{EXTENSIONS[fmt]}")
