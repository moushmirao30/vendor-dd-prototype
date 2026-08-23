# Code walkthrough — how to defend this code in a review

**Written 23 August 2026. Deliberately short.** This is not a line-by-line annotation of
3,674 lines of `src/`; the code carries its own comments and each one names the defect it
exists to prevent. This is the map, plus the answer to every question a reviewer is likely
to ask and the file and function that answers it. **It is not a brief deliverable** — it
exists so the author can defend the code in a review without re-reading it.

---

## The shape, in one screen

```
config/vendors.yaml        seeds and URL patterns, one entry per vendor
config/settings.yaml       every threshold and cap, nothing hardcoded in src/
config/field_dictionary.yaml   the eight fields, their terms and their home pages
        |
        v
src/fetch.py         robots.txt, rate limit, cache        -> data/cache/html/*.html
src/agent1_collect.py    which URLs to try, what was got  -> data/corpus/<v>.json
src/parse.py         HTML -> blocks -> matched evidence    (no network, no model)
src/agent2_extract.py    field values, quotes, confidence -> data/corpus/<v>_fields.json
src/review_rules.py  every judgement, in ONE place
src/agent3_review.py     scores, coverage, review flags   -> data/briefs/<v>_brief.json
src/export.py            JSON / CSV / Markdown + manifest -> data/exports/
src/orchestrator.py      the three modes that chain 1->2->3
app.py                   five Streamlit tabs, reading the saved artifacts
tools/verify_corpus.py   the independent checker, importing src/review_rules
```

**`requests` appears in exactly one file: `src/fetch.py`.** Agent 2, Agent 3, `parse.py`
and `review_rules.py` import nothing that can reach the network, which is why replay is
offline by construction rather than by promise.

---

## Ten questions, and where the answer lives

| A reviewer asks | Answer, and where to point |
|---|---|
| **Is there a language model anywhere?** | No. Extraction is term matching over HTML blocks. `config/settings.yaml` had a `backend: "rules" \| "llm"` key that nothing read; it was removed as defect 47 rather than left as an advertisement for a path that does not exist. |
| **Where does a printed quote come from?** | `parse.page_to_blocks` (HTML → heading + body blocks) → `parse.find_evidence` (term match, negative terms, noise stripping) → `agent2_extract.best_sentence` (the sentence in the block carrying the most matched terms). The value is copied character-for-character; nothing is written. |
| **How is a confidence label decided?** | `parse.score_field_confidence`, with `parse.evidence_level` deciding whether a block is a sentence, a bare heading or alt text. Plain English in `docs/confidence_rules.md`. `agent2_extract.status_from_confidence` maps the label to FOUND / PARTIAL / NOT_FOUND — `NOT_FOUND` is a sentinel, never printed as a fourth confidence level. |
| **Why does a vendor have three different numbers?** | Because one number hid a real problem (defect 42). `review_rules.vendor_score` = how much quotable evidence was found. `review_rules.vendor_confidence` = the client's weakest-link definition. `review_rules.field_coverage` = how much could actually be checked. Postman scores 10/10 on the first and 2 of 5 on the third; a single number would have called that a strong vendor. |
| **Do you scrape aggressively?** | `src/fetch.py`. `RobotsPolicy` reads `robots.txt` before every request, with our own honest user agent, following RFC 9309 rather than `urllib`'s stricter reading — an unreachable or failed `robots.txt` is treated as disallowed. Delay, caps and the user agent are all in `config/settings.yaml` under `fetch`. |
| **Can I reproduce your figures?** | `tools/run_workflow.py --mode replay` re-runs 1 → 2 → 3 from the frozen HTML cache with no network request. The reconciliation is in `docs/evaluation.md` §3.1: on 23 August the replay changed 28 artifact files and every changed byte was a timestamp. |
| **What happens when a page cannot be read?** | Agent 1 records `content_usable: false`; Agent 2 skips it, records an `unusable-page` step, and adds a caveat to the affected field's *evidence list* — not only to the audit trail, because a reviewer reads the brief. *"We looked and found nothing"* and *"there was nothing to look at"* are different findings and only the first is about the vendor. |
| **What if the cached HTML is missing?** | `agent2_extract.resolve_html_path` returns `None`, a `missing-html` step is recorded, and the field carries a *NOT SEARCHED* caveat (defect 40). That path only trusts an absolute path as written — a relative one is resolved against the repository it was handed, never the shell's working directory (defect 55). |
| **Who checks the checker?** | `tools/verify_corpus.py` imports the same predicates from `src/review_rules.py` that Agent 3 uses. One rule, one place: four defects in this project came from a single rule implemented twice and drifting apart. |
| **What is the Streamlit app computing?** | Nothing. `app.py` reads the saved artifacts under `data/` and renders them. If a number differs between the screen and the JSON, the screen is wrong. |

---

## Three things that look like bugs and are decisions

1. **Nine evidence blocks earn their label from a sentence that does not contain the matched
   term** — and this is flagged, not fixed. The obvious tightening also demotes Sentry's
   *"High Availability"* heading with a full paragraph beneath it, and GitLab's *"Trust Center
   Documents"*, because vendors do not repeat a heading inside its own paragraph. Whether a
   block coheres is a judgement, not a rule, so `verify_corpus` raises
   `claim-not-in-matched-sentence` and a human decides. `docs/evaluation.md` §3.
2. **`data/cache/html/` ships empty.** The client asked on 18 August that the 22 MB of
   verbatim third-party HTML not be shipped. Every check therefore has to tell *excluded by
   instruction* apart from *broken* — `run_workflow --mode replay` refuses and explains,
   `verify_corpus.py` raises one `cache-absent` WARN per vendor rather than 49 FAILs
   (defect 53), and the test suite skips its one replay test rather than failing it
   (defect 54).
3. **A vendor can show `NOT_FOUND` beside a `WARN` saying the page was unreadable.** That
   pairing is the point. The dangerous output is not a missing answer; it is a confident
   answer about a company that nobody checked.

---

## The two commands that prove all of it

```powershell
pytest -q                       # 154 where the HTML cache exists, 153 + 1 skipped on a clone
python tools\verify_corpus.py   # 0 FAIL across all seven vendors; READ THE WARN ROWS
```

The suite has caught exactly one defect first, and one more was a defect in the suite itself.
Everything else in `docs/evaluation.md` §5 was found by opening an artifact and reading it.
That ratio is the most honest thing in this repository.
