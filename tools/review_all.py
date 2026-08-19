"""
review_all.py — run Agent 3 over every collected vendor and write the briefs.

WHY THIS EXISTS BEFORE THE UI DOES
----------------------------------
Agent 3 is finished; `app.py`'s Vendor brief tab is not, and `src/orchestrator.py`
is scheduled for 17-18 August. Without something to run it, Agent 3 would sit in
the repository unexercised until the UI catches up — and this project has already
shipped one safeguard that nobody ever ran (defect 34: a caveat wired to an audit
step Agent 1 never emitted, discovered only when someone printed the list it was
built from). Code that has never been executed against real data is not finished,
it is only written.

So this is the same shape as `tools/verify_corpus.py`: a small command-line entry
point over library code, useful to a developer and harmless to the deliverable.
The UI will call `review_vendor` directly; it will not call this file.

    python tools/review_all.py            # every vendor with a corpus on disk
    python tools/review_all.py postman    # one vendor

Writes `data/briefs/<slug>_brief.json`, which is also what the export step will
read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent3_review import review_vendor, save_brief          # noqa: E402

CORPUS = ROOT / "data" / "corpus"
BRIEFS = ROOT / "data" / "briefs"


def _load(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / name).read_text(encoding="utf-8"))


def review(slug: str, vendor: dict, field_dictionary: dict, settings: dict,
           category: str) -> bool:
    """Review one vendor. Returns False if its corpus is not on disk yet."""
    corpus_path = CORPUS / f"{slug}.json"
    fields_path = CORPUS / f"{slug}_fields.json"
    if not corpus_path.exists() or not fields_path.exists():
        print(f"  {slug:10s} SKIPPED — run Agents 1 and 2 for this vendor first")
        return False

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    records = corpus["records"] if isinstance(corpus, dict) and "records" in corpus else corpus
    fields = json.loads(fields_path.read_text(encoding="utf-8"))["fields"]

    trail_path = CORPUS / f"{slug}_run.json"
    steps = (json.loads(trail_path.read_text(encoding="utf-8"))["steps"]
             if trail_path.exists() else [])

    brief, review_steps = review_vendor(vendor, fields, records, steps,
                                        field_dictionary, settings, category)
    save_brief(brief, BRIEFS, review_steps)

    # The score is never printed alone. See src/schema.py, defects 31 and 42:
    # evidence, confidence and coverage answer three different questions.
    print(f"  {slug:10s} ev {brief.evidence_score:2d}/10 {brief.evidence_band:6s} "
          f"conf {brief.confidence_band:6s} ({brief.confidence_counts.get('High',0)} High)   "
          f"coverage {brief.coverage_verified}/{brief.coverage_total}   "
          f"{len(brief.missing_or_unclear)} missing   "
          f"{len(brief.review_flags)} flag(s)")
    return True


def main() -> int:
    settings = _load("settings.yaml")
    fdy = _load("field_dictionary.yaml")
    field_dictionary = fdy.get("fields", fdy)
    cfg = _load("vendors.yaml")
    category = cfg.get("category", "")

    wanted = sys.argv[1:]
    vendors = [v for v in cfg["vendors"] if not wanted or v["slug"] in wanted]
    if not vendors:
        print(f"no vendor matching {wanted} in config/vendors.yaml")
        return 1

    print(f"\n{'=' * 78}\n  AGENT 3 — Brief Review\n{'=' * 78}")
    reviewed = sum(review(v["slug"], v, field_dictionary, settings, category)
                   for v in vendors)
    print(f"{'=' * 78}")
    print(f"  {reviewed} brief(s) written to data/briefs/")
    print("  COVERAGE is not the score. A vendor can score 10/10 on pages nobody")
    print("  could read — read both numbers, and read the flags.")
    print(f"{'=' * 78}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
