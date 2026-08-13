"""
verify_corpus.py — check a collected vendor corpus before you trust it or commit it.

WHY THIS TOOL EXISTS
--------------------
Every defect in this project so far was found by a human opening the artifact and
reading it: the screen, then the JSON, then the raw HTML. That worked, and it does
not scale. Reading seven vendors' corpora by hand, once per collection run, is
slow, it is inconsistent, and — the part that matters for a deliverable — it
leaves no evidence that the checks happened and no way for a reviewer to repeat
them.

So the checks that have caught real bugs are written down here as code. Each one
below names the defect it descends from. Run it after collecting a vendor and
before committing:

    python tools/verify_corpus.py atlassian     # one vendor
    python tools/verify_corpus.py               # every corpus on disk

WHAT THE SEVERITIES MEAN
------------------------
    FAIL  something is wrong with OUR pipeline. Do not commit this corpus.
    WARN  something is unusual about the VENDOR. Probably a real finding — read
          it, decide, and expect to quote it in the evaluation summary.
    INFO  context worth seeing, no action.

A WARN is not a lesser FAIL. The distinction is the whole point: this project's
central risk is confusing "our tool could not read it" with "the vendor does not
publish it", and a checker that blurred the two would be reproducing the bug it
is meant to catch.

Exit code is 1 if any FAIL was raised, so this can gate a commit.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent2_extract import resolve_html_path                    # noqa: E402
from src.parse import term_in, visible_text                         # noqa: E402

CORPUS = ROOT / "data" / "corpus"

# Sequences that appear when UTF-8 bytes are decoded as ISO-8859-1 (defect 8).
MOJIBAKE_MARKERS = ("â€", "Â\xa0", "â€™", "â€œ", "Ã©", "Ã¢")


class Report:
    """Collects findings for one vendor and prints them in a fixed order."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.rows: list[tuple[str, str, str]] = []   # (severity, check, message)

    def add(self, severity: str, check: str, message: str) -> None:
        self.rows.append((severity, check, message))

    def fail(self, check: str, message: str) -> None:
        self.add("FAIL", check, message)

    def warn(self, check: str, message: str) -> None:
        self.add("WARN", check, message)

    def info(self, check: str, message: str) -> None:
        self.add("INFO", check, message)

    @property
    def failed(self) -> bool:
        return any(sev == "FAIL" for sev, _, _ in self.rows)

    def print(self) -> None:
        order = {"FAIL": 0, "WARN": 1, "INFO": 2}
        icon = {"FAIL": "x", "WARN": "!", "INFO": "-"}
        counts = {s: sum(1 for sev, _, _ in self.rows if sev == s)
                  for s in ("FAIL", "WARN", "INFO")}

        print(f"\n{'=' * 78}")
        print(f"  {self.slug}   "
              f"{counts['FAIL']} FAIL   {counts['WARN']} WARN   {counts['INFO']} INFO")
        print("=" * 78)
        for sev, check, message in sorted(self.rows, key=lambda r: order[r[0]]):
            print(f"  [{icon[sev]}] {sev:4} {check:<26} {message}")


# ---------------------------------------------------------------------------
# Collection checks — Agent 1's output
# ---------------------------------------------------------------------------

def check_collection(rep: Report, records: list[dict], trail: dict, vendor: dict) -> None:
    if not records:
        rep.fail("corpus-empty", "the corpus file contains no records at all")
        return

    rep.info("pages", f"{len(records)} page(s) collected: "
                      f"{', '.join(r['source_type'] for r in records)}")

    # --- every page type either collected, or explicitly accounted for -------
    # Defect 11: a page type must never disappear without a trace.
    steps = trail.get("steps", [])
    collected_types = {r["source_type"] for r in records}
    accounted = collected_types | {s["source_type"] for s in steps
                                   if s["action"] in ("skip", "budget-stop")}
    for stype in vendor.get("seeds", {}):
        if stype not in accounted:
            rep.fail("silent-omission",
                     f"'{stype}' is a seed but appears in neither the corpus nor "
                     f"the audit trail — it vanished without explanation")

    missing = [s["source_type"] for s in steps if s["action"] == "skip"]
    if missing:
        rep.warn("not-collected",
                 f"{', '.join(missing)} — flagged for manual follow-up. Confirm "
                 f"the vendor really has no such page before reporting it as absent")

    for s in steps:
        if "REDIRECTED" in s.get("outcome", ""):
            rep.info("redirect", f"{s['source_type']}: {s['outcome'][:90]}")
        if s["action"] == "budget-stop":
            rep.warn("budget-stop", f"{s['source_type']}: {s['outcome'][:90]}")

    for r in records:
        stype, url = r["source_type"], r["source_url"]

        # --- fetch actually succeeded ---------------------------------------
        if not r.get("fetch_ok", False):
            rep.fail("fetch-failed", f"{stype}: fetch_ok is False but the record was kept")
        if r.get("http_status") != 200:
            rep.warn("http-status", f"{stype}: HTTP {r.get('http_status')} — {url}")
        if not r.get("robots_allowed", True):
            rep.fail("robots", f"{stype}: kept a page robots.txt disallowed — {url}")

        # --- the corpus must be portable (defect 16) ------------------------
        raw = r.get("raw_html_path", "")
        if not raw:
            rep.fail("no-cache-path", f"{stype}: no raw_html_path, so the text cannot be proven")
        elif raw[1:3] == ":\\" or raw.startswith("/home") or raw.startswith("/Users"):
            rep.fail("absolute-path",
                     f"{stype}: raw_html_path is absolute ({raw[:42]}...). This corpus "
                     f"replays only on the machine that wrote it — re-run Agent 1")

        path = resolve_html_path(raw, ROOT)
        if raw and path is None:
            rep.fail("cache-missing",
                     f"{stype}: cached page not found on this machine — offline replay "
                     f"and Agent 2 will both fail for this page")
            continue
        if path is None:
            continue

        html = path.read_text(encoding="utf-8", errors="replace")

        # --- the text is provably from this page (defect: replay integrity) --
        recorded = r.get("content_sha256", "")
        actual = hashlib.sha256(html.encode("utf-8")).hexdigest()
        if recorded and recorded != actual:
            rep.warn("page-changed",
                     f"{stype}: content_sha256 does not match the cached file. Either "
                     f"the vendor changed the page or the cache was edited")

        # --- mojibake (defect 8) --------------------------------------------
        text = r.get("collected_text", "")
        found = [m for m in MOJIBAKE_MARKERS if m in text]
        if found:
            rep.fail("mojibake",
                     f"{stype}: corrupted characters in collected_text ({found[0]!r}) "
                     f"— an encoding regression, quotes will be wrong in evidence")

        # --- usable at all? (defect 23) -------------------------------------
        readable = len(visible_text(html))
        blocks = r.get("block_count")
        if r.get("content_usable") is False:
            rep.warn("unusable-page",
                     f"{stype}: {readable} readable chars, {blocks} blocks from "
                     f"{len(html):,} bytes — JavaScript-rendered. Correctly recorded "
                     f"as unusable; any NOT_FOUND here is OUR limit, not the vendor's")
        elif blocks is None:
            rep.fail("stale-corpus",
                     f"{stype}: no block_count — this corpus predates the usability "
                     f"check. Re-run Agent 1 before trusting any NOT_FOUND")
        elif blocks == 0:
            rep.fail("unusable-unflagged",
                     f"{stype}: 0 heading blocks but content_usable is not False. "
                     f"Every field from this page will be a FALSE NOT_FOUND")

        # --- content density: a JS-rendering signal the usable flag misses --
        # Postman's docs page produced 2 heading blocks from 1.24 MB of HTML. It
        # cleared the usability threshold on character count, so Agent 1 called
        # it usable, and it is - barely. Two blocks from a megabyte still means
        # most of that page was never read.
        if blocks is not None and blocks <= 3 and len(html) > 300_000:
            rep.warn("thin-density",
                     f"{stype}: only {blocks} heading block(s) from {len(html):,} "
                     f"bytes of HTML. Passed the usability threshold, but most of "
                     f"this page is probably JavaScript we never rendered")

        # --- the cleaner kept a fair share (defects 7 and 12) ---------------
        if readable > 1200 and len(text) < readable * 0.5:
            rep.warn("thin-text",
                     f"{stype}: collected_text is {len(text)} of {readable} readable "
                     f"chars ({len(text)/readable:.0%}). Agent 2 reads raw HTML so "
                     f"evidence is safe, but the corpus reads poorly for a human")

    # --- one page doing two jobs -------------------------------------------
    urls: dict[str, list[str]] = {}
    for r in records:
        urls.setdefault(r["source_url"].rstrip("/"), []).append(r["source_type"])
    for url, types in urls.items():
        if len(types) > 1:
            rep.warn("duplicate-page",
                     f"one URL serves {', '.join(types)} — {url}. Its evidence will "
                     f"be double-counted across page types")


# ---------------------------------------------------------------------------
# Extraction checks — Agent 2's output
# ---------------------------------------------------------------------------

def check_extraction(rep: Report, fields: list[dict], records: list[dict],
                     field_dictionary: dict, settings: dict) -> None:
    if not fields:
        rep.info("extraction", "no extraction on disk yet — run Agent 2")
        return

    unusable = [r["source_type"] for r in records if r.get("content_usable") is False]
    scores = settings["confidence"]["field_score"]
    core = settings["confidence"]["core_fields"]
    total = 0

    for f in fields:
        name, ev = f["name"], f.get("evidence", [])
        if name in core:
            total += scores.get(f["confidence"], 0)

        real_ev = [e for e in ev if e.get("match_location") != "tool_limitation"]

        # --- a citation must contain what it cites (defects 20, 22) ---------
        for e in real_ev:
            shown = f"{e.get('snippet', '')} {e.get('heading', '')}".lower()
            if e.get("matched_terms") and not any(term_in(t, shown)
                                                  for t in e["matched_terms"]):
                rep.fail("orphan-citation",
                         f"{name}: card cites {e['matched_terms']} but the quoted "
                         f"text does not contain it — {e.get('snippet','')[:50]!r}")

        # --- a logo is never a claim (the Atlassian guard) ------------------
        if real_ev and real_ev[0].get("match_location") == "alt_text_only" \
                and f["confidence"] in ("High", "Medium"):
            rep.fail("logo-as-claim",
                     f"{name}: {f['confidence']} confidence resting on image "
                     f"alt-text. This is the exact failure the project exists to "
                     f"avoid — an image presented as a written claim")

        # --- the quote must have earned the label (defect 15b) -------------
        if real_ev and f["status"] == "NOT_FOUND":
            rep.fail("status-mismatch", f"{name}: NOT_FOUND but carries real evidence")
        if not real_ev and f["status"] != "NOT_FOUND":
            rep.fail("status-mismatch",
                     f"{name}: status {f['status']} with no evidence behind it")

        # --- NOT_FOUND must be honest about which kind it is (defect 23) ----
        if f["status"] == "NOT_FOUND":
            hedged = any(e.get("match_location") == "tool_limitation" for e in ev)
            if unusable and not hedged:
                rep.fail("unhedged-not-found",
                         f"{name}: reported as a clean negative while "
                         f"{len(unusable)} page(s) were unreadable")
            if not unusable and hedged:
                rep.fail("over-hedged",
                         f"{name}: hedged although every page was readable — this is "
                         f"a genuine finding and must not be softened")

        # --- FOUND, but its primary document was never read (defect 24) -----
        home_types = field_dictionary.get(name, {}).get("preferred_source_types", [])
        unread_home = [s for s in unusable if s in home_types]
        if real_ev and unread_home:
            hedged = any(e.get("match_location") == "tool_limitation" for e in ev)
            if not hedged:
                rep.fail("unread-home-page",
                         f"{name}: reported {f['status']}/{f['confidence']} from "
                         f"elsewhere while its own {', '.join(unread_home)} page was "
                         f"unreadable, with no caveat attached. A confident answer "
                         f"whose primary source was never read invites no checking")
            else:
                rep.warn("unread-home-page",
                         f"{name}: {f['status']} from another page because the "
                         f"{', '.join(unread_home)} page was unreadable — caveat "
                         f"present, verify by hand")

        # --- evidence from outside the field's home ------------------------
        home = field_dictionary.get(name, {}).get("preferred_source_types", [])
        if real_ev and home and all(e.get("source_type") not in home for e in real_ev):
            rep.warn("off-home-evidence",
                     f"{name}: all evidence came from "
                     f"{', '.join(sorted({e.get('source_type','?') for e in real_ev}))}, "
                     f"never from {'/'.join(home)}. The match is real; the finding is "
                     f"weak. Agent 3 must flag this")

    thresholds = settings["confidence"]["vendor_thresholds"]
    band = ("High" if total >= thresholds["High"]
            else "Medium" if total >= thresholds["Medium"] else "Low")
    rep.info("vendor-score", f"{total}/10 core → {band}")

    found = sum(1 for f in fields if f["status"] == "FOUND")
    partial = sum(1 for f in fields if f["status"] == "PARTIAL")
    nf = sum(1 for f in fields if f["status"] == "NOT_FOUND")
    rep.info("field-status", f"{found} FOUND, {partial} PARTIAL, {nf} NOT_FOUND")


# ---------------------------------------------------------------------------

def verify(slug: str, vendors: dict, field_dictionary: dict, settings: dict) -> Report:
    rep = Report(slug)

    corpus_path = CORPUS / f"{slug}.json"
    if not corpus_path.exists():
        rep.fail("no-corpus", f"{corpus_path.name} does not exist — run Agent 1")
        return rep

    records = json.loads(corpus_path.read_text(encoding="utf-8"))

    run_path = CORPUS / f"{slug}_run.json"
    trail = json.loads(run_path.read_text(encoding="utf-8")) if run_path.exists() else {}
    if not trail.get("steps"):
        rep.fail("no-trail",
                 f"{slug}_run.json is missing or empty — the brief requires the audit "
                 f"trail to survive a replay")

    vendor = next((v for v in vendors if v["slug"] == slug), {})
    if not vendor:
        rep.fail("unknown-vendor", f"'{slug}' is not in config/vendors.yaml")

    check_collection(rep, records, trail, vendor)

    fields_path = CORPUS / f"{slug}_fields.json"
    fields: list[dict] = []
    if fields_path.exists():
        data = json.loads(fields_path.read_text(encoding="utf-8"))
        fields = data if isinstance(data, list) else data.get("fields", [])
        if isinstance(data, dict) and not data.get("steps"):
            rep.warn("no-extract-trail",
                     "the extraction has no saved audit trail — press Agent 2 again")
    check_extraction(rep, fields, records, field_dictionary, settings)

    return rep


def main(argv: list[str]) -> int:
    cfg = yaml.safe_load((ROOT / "config" / "vendors.yaml").read_text(encoding="utf-8"))
    field_dictionary = yaml.safe_load(
        (ROOT / "config" / "field_dictionary.yaml").read_text(encoding="utf-8"))
    settings = yaml.safe_load(
        (ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))

    slugs = argv[1:] or sorted(
        p.stem for p in CORPUS.glob("*.json")
        if not p.stem.endswith(("_run", "_fields")))

    if not slugs:
        print("No corpus files in data/corpus/. Run Agent 1 first.")
        return 0

    reports = [verify(s, cfg["vendors"], field_dictionary, settings) for s in slugs]
    for rep in reports:
        rep.print()

    failed = [r.slug for r in reports if r.failed]
    print(f"\n{'=' * 78}")
    if failed:
        print(f"  DO NOT COMMIT: {len(failed)} vendor(s) failed — {', '.join(failed)}")
        print("  Fix the FAIL rows, re-run Agent 1 and Agent 2, then verify again.")
    else:
        print(f"  {len(reports)} vendor(s) passed. Read the WARN rows before committing:")
        print("  they are usually real findings about the vendor and belong in the")
        print("  evaluation summary.")
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
