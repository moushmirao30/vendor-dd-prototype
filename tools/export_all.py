"""
export_all.py — write every submittable artifact for every vendor.

Produces, under `data/exports/`:

    corpus.csv                 every collected page, the brief's named fields
    source_manifest.csv        every page ATTEMPTED — the client's new deliverable
    <slug>_brief.json/.csv/.md one per vendor, per format the brief allows

Run it after Agents 1-3:

    python tools/review_all.py      # writes data/briefs/*_brief.json
    python tools/export_all.py      # writes data/exports/*

WHY THE MANIFEST MATTERS MORE THAN IT LOOKS
-------------------------------------------
First Quadrant Labs asked us not to ship the 22 MB HTML cache. Without it a
reviewer cannot re-derive what we saw, so the manifest is what replaces it: one
row per page we TRIED, including the 404s, the JavaScript shells and the page
types never located at all. A corpus shows what worked; a manifest shows what was
attempted, and only the second lets a reader judge whether a missing field means
the vendor is silent or means we could not look.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.export import (export_brief, export_corpus_csv,          # noqa: E402
                        export_source_manifest, source_manifest_rows)

CORPUS = ROOT / "data" / "corpus"
BRIEFS = ROOT / "data" / "briefs"
EXPORTS = ROOT / "data" / "exports"


def main() -> int:
    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    cfg = yaml.safe_load((ROOT / "config" / "vendors.yaml").read_text(encoding="utf-8"))
    formats = settings.get("output", {}).get("export_formats", ["json", "csv", "markdown"])

    wanted = sys.argv[1:]
    vendors = [v for v in cfg["vendors"] if not wanted or v["slug"] in wanted]
    if not vendors:
        print(f"no vendor matching {wanted} in config/vendors.yaml")
        return 1

    print(f"\n{'=' * 78}\n  EXPORT\n{'=' * 78}")
    all_records: list[dict] = []
    manifest: list[list] = []
    briefs_written = 0

    for v in vendors:
        slug = v["slug"]
        corpus_path = CORPUS / f"{slug}.json"
        if not corpus_path.exists():
            print(f"  {slug:10s} SKIPPED — no corpus; run Agent 1 first")
            continue

        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        records = corpus["records"] if isinstance(corpus, dict) and "records" in corpus else corpus
        all_records += records

        trail_path = CORPUS / f"{slug}_run.json"
        steps = (json.loads(trail_path.read_text(encoding="utf-8"))["steps"]
                 if trail_path.exists() else [])
        rows = source_manifest_rows(v["name"], records, steps)
        manifest += rows

        brief_path = BRIEFS / f"{slug}_brief.json"
        if brief_path.exists():
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            for fmt in formats:
                export_brief(brief, EXPORTS, fmt)
            briefs_written += 1
            written = "/".join(formats)
        else:
            written = "no brief — run tools/review_all.py"

        attempted = len(rows)
        collected = sum(1 for r in rows if str(r[3]).startswith("COLLECTED"))
        unreadable = sum(1 for r in rows if r[3] == "COLLECTED BUT UNREADABLE")
        print(f"  {slug:10s} {attempted:2d} attempted, {collected:2d} collected "
              f"({unreadable} unreadable)   brief: {written}")

    export_corpus_csv(all_records, EXPORTS / "corpus.csv")
    export_source_manifest(manifest, EXPORTS / "source_manifest.csv")

    failed = sum(1 for r in manifest if r[3] in ("FAILED", "NOT COLLECTED", "NOT ATTEMPTED"))
    unreadable = sum(1 for r in manifest if r[3] == "COLLECTED BUT UNREADABLE")
    print(f"{'=' * 78}")
    print(f"  corpus.csv           {len(all_records)} page(s)")
    print(f"  source_manifest.csv  {len(manifest)} attempt(s): "
          f"{failed} never collected, {unreadable} collected but unreadable")
    print(f"  briefs               {briefs_written} vendor(s) x {len(formats)} format(s)")
    print(f"  -> {EXPORTS}")
    print("  The HTML cache is NOT part of the submission (client instruction,")
    print("  18 Aug). The manifest is what lets a reviewer see what was attempted.")
    print(f"{'=' * 78}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
