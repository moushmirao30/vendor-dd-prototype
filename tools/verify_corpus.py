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
from src.parse import term_in, visible_text                          # noqa: E402
# THE PREDICATES LIVE IN src/review_rules.py AND ARE IMPORTED, NOT COPIED.
# This tool decides whether a corpus may be committed; Agent 3 decides what the
# reviewer is told. If they computed "coverage" or "weak evidence" separately
# they would drift, and that is defect 15 (code disagreeing with its own
# documentation) and defect 36 (two docstrings disagreeing about one rule)
# wearing a third hat. One definition, two callers.
from src.review_rules import (claim_not_in_matched_sentence,        # noqa: E402
                              gated_evidence, off_home_evidence,
                              real_evidence, unread_home_page, vendor_confidence,
                              vendor_score)

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

    @property
    def cache_absent(self) -> bool:
        """True when this vendor ran with no local HTML cache at all."""
        return any(check == "cache-absent" for _, check, _ in self.rows)

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

def check_collection(rep: Report, records: list[dict], trail: dict, vendor: dict,
                     settings: dict) -> None:
    # `settings` added 13 Aug 2026 with defect 32 so this report can print the
    # thresholds it is judging against instead of a bare number the reader has
    # to go and look up. `.get` throughout: an older settings.yaml should make
    # the tool print less, never crash.
    fetch_cfg = settings.get("fetch", {})
    min_chars = fetch_cfg.get("min_usable_text_chars", 600)
    min_density = fetch_cfg.get("min_readable_chars_per_kb", 2.0)

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

    # --- IS THE CACHE PARTLY GONE, OR ENTIRELY ABSENT? ----------------------
    # These are different facts and they need different severities. A few pages
    # missing means this working tree is inconsistent -- that is our bug, and it
    # FAILS. EVERY page missing means the HTML cache is simply not here, which is
    # the documented shape of the submitted archive: the client asked on 18 Aug
    # 2026 that the 22 MB of verbatim third-party HTML not be shipped.
    #
    # Until 22 Aug 2026 this told the second story with the first story's words.
    # A reviewer who cloned the submission and followed the README saw 49 FAIL
    # rows and "DO NOT COMMIT: 7 vendor(s) failed" -- the checker announcing that
    # the deliverable was broken, when it was behaving exactly as instructed.
    # That is defect 40 in a second costume: the archive we ship making a tool
    # say something false. `run_workflow --mode replay` was taught to refuse
    # gracefully and explain; this was not. Found by running the fresh-clone test.
    _with_path = [r for r in records if r.get("raw_html_path")]
    _resolved = [r for r in _with_path
                 if resolve_html_path(r["raw_html_path"], ROOT) is not None]
    cache_absent = bool(_with_path) and not _resolved
    if cache_absent:
        rep.warn("cache-absent",
                 f"no cached HTML on this machine for any of the {len(_with_path)} "
                 f"collected page(s). This is the shape of the submitted archive — "
                 f"the cache is excluded by client instruction, not lost. The "
                 f"structured corpus below was still checked in full; the "
                 f"page-level text, hash and quote checks were SKIPPED, not "
                 f"passed. Re-collect the public sources (see the README) to run "
                 f"them.")

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
            # One row already said the cache is absent. Repeating it once per page
            # buries the WARN rows that are real findings about the vendor.
            if not cache_absent:
                rep.fail("cache-missing",
                         f"{stype}: cached page not found on this machine — this "
                         f"tree has SOME cached pages and not this one, so the "
                         f"corpus and the cache disagree. Re-run Agent 1")
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
        density = readable / max(len(html) / 1024, 0.001)
        unusable_page = r.get("content_usable") is False
        if unusable_page:
            # DEFECT 32 (13 Aug 2026), second half: this line used to print the
            # density to one decimal place. Postman's docs page is 2,370 readable
            # characters from 1,234,954 bytes — 1.965 chars/KB against a 2.0
            # threshold — and printed as "2.0 readable chars per KB", a number
            # that appears to contradict the rejection it is explaining. A
            # reviewer reading "2.0, threshold 2.0, rejected" concludes the tool
            # is broken. Two decimals and the threshold alongside.
            rep.warn("unusable-page",
                     f"{stype}: {readable} readable chars, {blocks} blocks from "
                     f"{len(html):,} bytes ({density:.2f} chars/KB, floor "
                     f"{min_chars}, min density {min_density}) — JavaScript-"
                     f"rendered. Correctly recorded as unusable; any NOT_FOUND "
                     f"here is OUR limit, not the vendor's")
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
        #
        # DEFECT 32 (13 Aug 2026), first half: `not unusable_page` was missing,
        # so this fired for pages already declared unusable and printed
        # "Passed the usability threshold" two lines under "recorded as
        # unusable". Atlassian's product and pricing pages and Postman's docs
        # page each produced that contradiction. This check is for pages that
        # PASSED and still look thin; a page that already failed is reported by
        # the branch above and does not need a second, opposite verdict.
        if (not unusable_page
                and blocks is not None and blocks <= 3 and len(html) > 300_000):
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
    # Pages Agent 2 could actually search. Zero of them is a different world from
    # "some page failed" — see the defect-41 note in the NOT_FOUND checks below.
    usable_pages = [r["source_type"] for r in records if r.get("content_usable") is not False]
    scores = settings["confidence"]["field_score"]
    min_body_high = settings["extraction"]["min_body_chars_for_high"]
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

        # --- DEFECT 37: the label was earned by a sentence that does not
        #     contain the matched term ---------------------------------------
        #
        # `evidence_level` measures the longest sentence anywhere in the block.
        # In 9 of 122 blocks (13 Aug 2026) that sentence does not carry the
        # matched term at all. Atlassian's security field is the clearest case:
        # the term `hipaa` occurs only in a 39-character section title,
        # "Sensitive Health Information and HIPAA.", while the block's High came
        # from a 322-character sentence about something else in the same
        # terms-of-service section.
        #
        # NOT FIXED IN CODE, DELIBERATELY. The obvious fix — score only the
        # longest sentence that carries the term — would also demote Sentry's
        # "High Availability" heading with a full paragraph under it, and
        # GitLab's "Trust Center Documents". Those are genuine, well-evidenced
        # claims; vendors do not repeat a heading inside its own paragraph.
        # Tightening the rule would trade a cosmetic over-score for a false
        # negative, which is the mistake the defect 28 route-not-taken already
        # taught us. Whether the block coheres is a judgement, not a rule — so
        # measure it, report it, and let a human decide.
        for e in real_ev:
            short = claim_not_in_matched_sentence(e, min_body_high)
            if short is not None:
                rep.warn("claim-not-in-matched-sentence",
                         f"{name}: scored on a longer sentence, but the longest sentence "
                         f"actually containing {e.get('matched_terms')} is {short} chars. "
                         f"The block matched; the sentence that earned the label may be "
                         f"about something else. Verify by hand")

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
        #
        # DEFECT 41, 18 Aug 2026. Both tests below used the vendor-wide
        # `unusable` list: ANY unreadable page anywhere demanded a hedge on EVERY
        # empty field. That is the pre-defect-39 rule, still alive here — a THIRD
        # copy of a rule that `src/review_rules.py` exists to hold exactly once.
        # It made this checker fail the very briefs Agent 3 was writing correctly:
        # JetBrains' data-residency page reads cleanly and JetBrains genuinely
        # does not publish it, so hedging it hides a real finding behind our own
        # excuse — the mirror image of defect 23, not a second helping of it.
        #
        # The test is the field's OWN home page, via the shared predicate rather
        # than a fourth hand-written copy of it. `not usable_pages` keeps the
        # defect-23 half honest: when NOTHING was readable, no field has a
        # readable home page, `unread_home_page` is empty for all of them, and an
        # unhedged NOT_FOUND would be a clean negative about a site we never read
        # a word of.
        if f["status"] == "NOT_FOUND":
            hedged = any(e.get("match_location") == "tool_limitation" for e in ev)
            blocked = unread_home_page(f, unusable, field_dictionary) or (
                unusable if not usable_pages else [])
            if blocked and not hedged:
                rep.fail("unhedged-not-found",
                         f"{name}: reported as a clean negative while its own "
                         f"{', '.join(blocked)} page(s) could not be read")
            if not blocked and hedged:
                rep.fail("over-hedged",
                         f"{name}: hedged although the pages this fact belongs on "
                         f"were readable — this is a genuine finding about the "
                         f"vendor and must not be softened")

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
        # Shared with Agent 3 via review_rules, so the WARN a committer sees and
        # the flag a reviewer reads are the same judgement, not two that happen
        # to agree today.
        off = off_home_evidence(f, field_dictionary)
        if off:
            home = field_dictionary.get(name, {}).get("preferred_source_types", [])
            rep.warn("off-home-evidence",
                     f"{name}: all evidence came from {', '.join(off)}, "
                     f"never from {'/'.join(home)}. The match is real; the finding is weak")

        # --- the vendor says the proof exists but does not publish it --------
        gated = gated_evidence(f)
        if gated:
            rep.warn("gated-evidence",
                     f"{name}: evidence is gated behind a request (\"{gated[0]}\"). "
                     f"The claim cannot be closed from public sources alone")

    # --- DEFECT 31: the score counts what was found, never what was unread ----
    #
    # Postman scores 10/10 → High with four of its eight fields carrying a
    # tool_limitation caveat, its privacy policy at 0 readable characters and
    # its docs page 98% JavaScript. Sentry scores 10/10 → High with no caveats
    # and every page readable. Identical labels, entirely different evidence.
    # Read without the caveats, those two vendors are indistinguishable — which
    # is the exact failure this project exists to report, reproduced by our own
    # scoring.
    #
    # The real fix — discounting caveated fields, or refusing to band a vendor
    # below a coverage floor — is a scoring policy and belongs to Agent 3, which
    # does not exist yet. What this tool can do today is refuse to let the score
    # be read alone. Agent 3 must IMPORT this calculation rather than write its
    # own; a build-time tool and a shipped brief that compute coverage
    # differently is defect 15 with new names.
    scored = vendor_score(fields, core, settings["confidence"]["field_score"],
                          settings["confidence"]["vendor_thresholds"])
    total, band = scored["score"], scored["band"]
    cov = scored["coverage"]
    core_caveated = cov["caveated"]
    # DEFECT 42, closed 18 Aug 2026. The line above used to print this figure as
    # "vendor-score … → High" with no other axis beside it, and Agent 3 shipped it
    # into the brief header under the word CONFIDENCE — while every field card
    # below carried the client's confidence rule and disagreed. Postman and Sentry
    # both read 10/10 High on coverage 2/5 and 5/5. Three numbers now, computed
    # from the same predicates Agent 3 uses, so the checker and the brief cannot
    # drift apart.
    vconf = vendor_confidence(fields, core, field_dictionary, unusable)
    rep.info("evidence-score",
             f"{total}/10 core → {band}   (how much quotable evidence was found)")
    rep.info("vendor-confidence",
             f"{vconf['band']} — {vconf['counts']['High']} of {vconf['total']} core "
             f"field(s) High, {vconf['counts']['Medium']} Medium, "
             f"{vconf['counts']['Low']} Low   (the client's definition; weakest link)")
    rep.info("coverage",
             f"{cov['verified']}/{cov['core_total']} core fields verified without a "
             f"caveat   (how much could actually be checked)")

    if core_caveated and band == "High":
        rep.warn("score-without-coverage",
                 f"evidence {total}/10 → High while {len(core_caveated)} core "
                 f"field(s) ({', '.join(sorted(core_caveated))}) rest on a page "
                 f"nobody could read. The evidence score measures what was found, "
                 f"not what was checked — do not compare this vendor against a "
                 f"fully-read one on that number alone. Read the confidence and "
                 f"coverage rows above it")

    found = sum(1 for f in fields if f["status"] == "FOUND")
    partial = sum(1 for f in fields if f["status"] == "PARTIAL")
    nf = sum(1 for f in fields if f["status"] == "NOT_FOUND")
    rep.info("field-status", f"{found} FOUND, {partial} PARTIAL, {nf} NOT_FOUND")

    # PARTIAL has never once been produced across seven vendors and 56 field
    # results (13 Aug 2026). Either the middle case does not occur on real
    # vendor pages, or the branch is unreachable. An unused value in a
    # three-state vocabulary is a defect until it is proven otherwise, so say so
    # rather than let a reader assume the state is exercised.
    if partial == 0:
        rep.info("no-partials",
                 "no field scored PARTIAL. Low confidence is the only route to "
                 "PARTIAL, and nothing reached it here — worth confirming the "
                 "state is reachable before the vocabulary is documented as "
                 "three-valued")


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

    check_collection(rep, records, trail, vendor, settings)

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
        absent = [r.slug for r in reports if r.cache_absent]
        if absent:
            print(f"  {len(reports)} vendor(s) passed every check that can run here, and")
            print(f"  {len(absent)} ran with NO local HTML cache. That is expected: the")
            print("  submitted archive excludes the 22 MB of verbatim third-party HTML at")
            print("  the client's instruction of 18 August 2026.")
            print("")
            print("  WHAT WAS CHECKED: the structured corpus, the audit trail, every page")
            print("  type accounted for, and every scoring and coverage rule.")
            print("  WHAT WAS SKIPPED, NOT PASSED: the page-level text, hash and quote")
            print("  checks, which need the cached HTML. To run them, re-collect the")
            print("  public sources — see the README, 'Re-collecting the public sources'.")
        else:
            print(f"  {len(reports)} vendor(s) passed. Read the WARN rows before committing:")
            print("  they are usually real findings about the vendor and belong in the")
            print("  evaluation summary.")
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
