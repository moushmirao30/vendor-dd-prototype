# Test Cases and Sample Test Queries

**Vendor Due-Diligence Research Workflow Prototype — First Quadrant Labs**
Moushmi Rao · corpus frozen 13 August 2026, GitLab 19 August, JetBrains 22 August ·
written 20 August 2026, revised 22 August

This is the brief's *"sample test queries or test cases"* deliverable. It is organised in the
brief's own order — **Expected Input → Expected Output → Streamlit interface → Scope Boundaries →
Success Criteria** — so that each requirement can be checked against a case rather than against a
description.

Every case is real and has been run. Cases are numbered `TQ-` (a sample query a reviewer types or
clicks) or `TC-` (a test case with a fixed expected result). The **Ships?** column answers the
question the client raised on 18 August: the submitted archive excludes the 22 MB HTML cache, so
each case states whether a reviewer can run it from the archive as delivered.

| Ships? | Meaning |
|---|---|
| **Yes** | Runs in a fresh clone of the submitted archive. No network, no cache. |
| **Cache** | Needs the local HTML cache, which is excluded from the archive by client instruction. Re-collect first — see README, *Re-collecting the public sources*. |
| **Network** | Makes live requests to vendor sites. |

---

## How to run everything below

```powershell
cd vendor-dd-prototype
.venv\Scripts\activate
pip install -r requirements.txt

pytest -q                                    # 152 passed
python tools\run_workflow.py                 # review mode — the default, and the mode
                                             # that needs neither network nor cache
python tools\verify_corpus.py                # 0 FAIL across all seven vendors
streamlit run app.py                         # http://localhost:8501
```

**123 test functions across 9 files; parametrisation expands six of them, so `pytest -q` reports
152.** No API key, no account, no GPU, no paid service.

---

## A · Sample test queries — the brief's three Expected Inputs

The brief asks the prototype to accept *a vendor name or vendor list*, *collected public URLs or a
pre-prepared vendor source file*, and *an optional research category filter*.

| ID | Query | How to run it | Expected result | Ships? |
|---|---|---|---|---|
| **TQ-1** | One vendor by name | `python tools\run_workflow.py sentry` — or pick **Sentry** in the sidebar | One brief. Evidence 10/10, confidence **Medium** (2 of 5 core fields High), coverage **5/5**, 5 review flags | Yes |
| **TQ-2** | A vendor list | `python tools\run_workflow.py sentry linear jetbrains` | Three briefs in one run, each printed with its own three axes. Unknown slugs are refused by name, not ignored | Yes |
| **TQ-3** | Every vendor | `python tools\run_workflow.py` | Seven briefs. This is the command a reviewer runs first | Yes |
| **TQ-4** | A pre-prepared vendor source file | Add a vendor block to `config\vendors.yaml` — three are pre-written under `alternates:` (Docker, CircleCI, Vercel) — then `python tools\run_workflow.py --mode collect docker` | Agent 1 reads `robots.txt`, walks the curated seeds before any guessed URL pattern, and writes `data\corpus\docker.json`. **No code change is required to add a vendor** | Network |
| **TQ-5** | Category filter — *security* | Sidebar → **Research focus** → `security` | Tabs 3 and 4 narrow to **3 of 8** fields: `security_trust`, `encryption`, `uptime_reliability`. A caption states *"Showing 3 of 8 fields… this is a view, not a re-run"* | Yes |
| **TQ-6** | Category filter — *privacy* | Research focus → `privacy` | **2 of 8**: `privacy_data_handling`, `data_residency` | Yes |
| **TQ-7** | Category filter — *support* / *pricing* / *product capability* | Research focus → each in turn | **1 of 8** each: `support_documentation`, `pricing_availability`, `integrations_api` | Yes |
| **TQ-8** | Clearing the filter | Remove all selections | All 8 fields return **with no re-run**. The filter discards nothing; it is a reading lens over data already computed | Yes |

> **TQ-5 to TQ-8 exist because this control was a defect.** For nine days the dropdown was rendered
> and its return value discarded, under a help line promising it narrowed extraction — a control
> that changed nothing. It is now wired, and `FOCUS_TO_FIELDS` in `app.py` maps the brief's five
> category words directly. `tests/test_app_smoke.py` proves the wiring; the visual behaviour is
> confirmed by hand, because AppTest verifies data and not rendering.

---

## B · Expected Output — the twelve items the brief names, in all three formats

The brief lists twelve items a vendor brief must contain, and the interface must export **JSON,
CSV, or Markdown**. **The brief itself carries all twelve. JSON and Markdown carry all twelve;
the CSV carries ten.**

The CSV is one row per field, so it has no row shape for the two vendor-level prose items — the
overview and the curated category. It repeats the other vendor-level context on **every** row
instead, so that a reader who sorts, filters or copies a single row out of the sheet still takes
the confidence, the coverage and the disclaimer with them. **A reviewer who needs the overview or
the category should open the JSON or the Markdown**, both of which are exported alongside it.

| # | Brief item | JSON key | CSV column | Markdown |
|---|---|---|---|---|
| 1 | Vendor overview | `vendor_overview` | *not carried — see above* | **Overview**, labelled *quoted from the vendor's own product page* |
| 2 | Product or service category | `product_category` | *not carried — see above* | **Category**, labelled *curated, not extracted* |
| 3 | Key public sources used | `sources` | `source_url`, `source_type` | Sources section |
| 4 | Security and trust | `fields[security_trust]` | `field` row | Field card |
| 5 | Privacy and data-handling | `fields[privacy_data_handling]` | `field` row | Field card |
| 6 | Support and documentation | `fields[support_documentation]` | `field` row | Field card |
| 7 | Integration or API | `fields[integrations_api]` | `field` row | Field card |
| 8 | Pricing or plan | `fields[pricing_availability]` | `field` row | Field card |
| 9 | Missing or unclear information | `missing_or_unclear` | `vendor_missing_or_unclear` | Missing section |
| 10 | Review flags | `review_flags` | `review_flags_for_this_field` | Review flags section |
| 11 | Source-backed evidence snippets | `value` + `source_url` | `value`, `source_url`, `matched_terms` | Quoted with its URL |
| 12 | Confidence level | `confidence_band`, `confidence_counts` | `vendor_confidence`, `vendor_coverage` | Printed with coverage, never alone |

| ID | Test case | Expected result | Ships? |
|---|---|---|---|
| **TC-1** | The CSV carries its ten items, vendor context included | `BRIEF_COLUMNS` in `src\export.py` is **17 columns**: the 11 per-field columns plus `vendor_evidence_score`, `vendor_confidence`, `vendor_coverage`, `review_flags_for_this_field`, `vendor_missing_or_unclear`, `disclaimer`. Before 19 August it was 11, and a reviewer could open an export with no disclaimer on it (defect 46) | Yes |
| **TC-1b** | JSON and Markdown carry all twelve | `vendor_overview` and `product_category` are present in both, each labelled with its provenance — *quoted from the vendor's own product page*, *curated, not extracted*. `test_markdown_carries_the_disclaimer_and_the_overview_provenance` | Yes |
| **TC-2** | The download and the file on disk are identical | Byte-for-byte equal. `test_the_ui_download_and_the_file_on_disk_are_the_same_bytes` | Yes |
| **TC-3** | The disclaimer survives every format | Present in JSON, on **every** CSV row, and in the Markdown. `test_the_csv_export_carries_the_disclaimer_and_the_vendor_numbers` | Yes |
| **TC-4** | Page text survives a CSV round trip | A cell containing a comma, a double quote and a newline returns unchanged. `test_page_text_survives_a_csv_round_trip` | Yes |
| **TC-5** | The corpus CSV leads with the brief's own eight fields | `vendor_name, source_url, source_type, page_title, collected_text, date_collected, tags, evidence_note` first, in that order. `test_corpus_csv_leads_with_the_columns_the_brief_names` | Yes |
| **TC-6** | **Release check — the shipped artifacts match the code that claims to produce them** | `python tools\export_all.py`, then confirm `data\exports\*_brief.csv` has **17 columns**. **Run this after any change under `src\`.** See §G | Yes |

---

## C · Streamlit interface — the seven capabilities the brief lists

Tabs are `1 · Sources`, `2 · Agent steps`, `3 · Evidence`, `4 · Vendor brief`, `Export`.

| ID | Brief capability | Where | Expected result | Ships? |
|---|---|---|---|---|
| **TC-7** | Select a vendor | Sidebar | Seven vendors by name; selection drives every tab | Yes |
| **TC-8** | View collected sources | Tab 1 | One row per page: URL, type, title, date, HTTP status, whether robots allowed it, whether the text was usable. Every vendor renders a non-empty table | Yes |
| **TC-9** | Run or replay the workflow | Sidebar buttons | **Agent 1 — Collect sources** (network), **Agent 2 — Extract evidence**, **Agent 3 — Review and brief**. Agent 2 and 3 replay from stored data | 1: Network · 2–3: Yes |
| **TC-10** | See each agent step | Tab 2 | The audit trail: every page kept, skipped, redirected or never located, each with its reason | Yes |
| **TC-11** | Inspect extracted evidence | Tab 3 | Every field with its verbatim quote, source URL, matched terms and confidence reason | Yes |
| **TC-12** | View the final vendor brief | Tab 4 | The client's chain rendered literally and labelled: **Source → Extracted Evidence → Structured Field → Confidence → Review Flag → Final Brief**, one numbered link per field | Yes |
| **TC-13** | Export as JSON, CSV or Markdown | Export tab | Three download buttons. `test_ui_shell_has_all_five_review_stages_and_three_exports` | Yes |
| **TC-14** | The score can never be shown alone | Tabs 4 and 5 | No panel, template or export renders the evidence score without confidence and coverage beside it. `test_the_brief_tab_never_shows_one_axis_alone` | Yes |
| **TC-15** | The disclaimer is always visible | Every tab | *First-pass internal research aid; final review remains manual.* `test_disclaimer_is_always_visible` | Yes |

---

## D · The cases that matter most — missing information is flagged, not guessed

This is the brief's sixth success criterion and the point of the whole prototype. Each case below
is a real vendor, not a fixture.

| ID | Test case | Expected result | Ships? |
|---|---|---|---|
| **TC-16** | A page type that was never located | **JetBrains `terms`** — the curated seed and all five URL patterns 404. Reported as *never collected*, never silently omitted. `test_unresolvable_page_types_are_flagged_not_dropped` | Yes |
| **TC-17** | A page collected but unreadable | **Atlassian product** — 898,035 bytes of HTML, **52 readable characters, 0 heading blocks**. Marked *could not be evaluated*, distinct from *not found* — the client's exact wording | Yes |
| **TC-18** | A field answered from outside its own home page | **Postman privacy** — the privacy policy yields 0 readable characters, so the answer comes from the security page. A caveat is written into the **brief a human reads**, not only the audit trail | Yes |
| **TC-19** | A heading with no body | **Linear security** — `<h2>SOC 2 compliance</h2>` with an empty body. Status **PARTIAL**, not FOUND, and not silently dropped | Yes |
| **TC-20** | A label rather than a claim | **Sentry `data_residency`** — status **PARTIAL**, confidence **Low**, reason *"only a label, a fragment or an image — nothing quotable was written"* | Yes |
| **TC-21** | **A high score resting on unread pages** | **Postman** — evidence **10/10**, confidence **Medium** (0 of 5 core fields High), coverage **2 of 5**, and a `SCORE OVERSTATES COVERAGE` flag naming `integrations_api`, `privacy_data_handling`, `support_documentation`. Compare **Sentry**: 10/10, Medium, coverage **5/5**, no such flag. **The two are distinguishable at a glance; until 19 August they were not** | Yes |
| **TC-22** | Conflict detection with nothing to find | Returns **zero** conflicts on this corpus, and says so. Absence of contradiction is reported as a finding, never presented as corroboration | Yes |
| **TC-23** | Replay with no cache | `python tools\run_workflow.py --mode replay` in a fresh clone **refuses and explains why**, naming the pages whose cache is missing and the mode that works instead. `test_replay_refuses_when_the_html_cache_is_missing` | Yes |
| **TC-23b** | Replay **with** the cache — offline replay demonstrated | `python tools\run_workflow.py --mode replay` re-extracts every field from the frozen HTML cache with **no network access at all**. This is the case the client asked to see demonstrated; it needs the cache the client asked us not to ship, which is why the README explains re-collection. `test_replay_runs_when_the_cache_is_present` | Cache |
| **TC-23c** | **The checker in a cacheless clone** | `python tools\verify_corpus.py` in a fresh clone raises **one `cache-absent` WARN per vendor**, not one FAIL per page, and the footer separates *what was checked* from *what was skipped, not passed*. **Before 22 August it printed 49 FAIL rows and "DO NOT COMMIT: 7 vendor(s) failed"** — the checker calling the submitted archive broken while it behaved exactly as the client instructed (defect 53). **No automated test covers this: the suite runs where the cache exists.** Run it by hand before packaging | Yes |
| **TC-24** | Review with no cache | `python tools\run_workflow.py` — the default — produces all seven briefs. `test_review_mode_works_with_no_cache_at_all` | Yes |
| **TC-25** | Stale data on disk | Artifacts written by older code are **reported, not hidden**. `test_a_stale_extraction_is_reported_not_hidden` | Yes |
| **TC-25b** | **A caveat is not evidence** | JetBrains → tab 3 → expand *Support and documentation availability*. Expect **"Could not be evaluated — a limit of our collection, not a statement about the vendor"** and the reason, with **no quote block**. The table row must read `NOT_FOUND · confidence - · Evidence 0 · Caveats 1`. Until 22 August this printed *"Quoted from the vendor's page:"* above an **empty blockquote** and counted the caveat as evidence (defect 48). Repeat for `integrations_api` and `uptime_reliability` — the only other affected fields in the corpus | Yes |
| **TC-25c** | **Agent 2's rating and Agent 3's reviewed rating are both shown** | Any vendor → tab 3. The table carries **Confidence (Agent 2)** and **After Agent 3 review**. On Atlassian, Postman, GitHub, GitLab, Sentry, JetBrains and Linear the two differ on **26 field/vendor pairs in total**, always High → Medium, because defect 43 requires the printed quote to sit on the field's own page. **The right-hand column is what every export carries.** Until 22 August only Agent 2's value was shown, so tab 3 displayed a rating the system had already rejected (defect 52) | Yes |
| **TC-27** | **The submitted archive contains what it should, and nothing it should not** | `git archive --format=zip -o ..\submission.zip HEAD`, then unpack it and confirm: **109 files** · `data\cache\html\` holds only `.gitkeep` · `docs\test_cases.md` present · `HANDOFF.md` and `START_HERE.md` **absent** (`.gitattributes` marks them `export-ignore`; they are internal working documents) · no `.git`, `.venv`, `__pycache__` or `_to_delete`. **`git archive` ships the last COMMIT, not the working tree** — commit first, or the archive silently ships older code | Yes |
| **TC-26** | An unknown mode | Rejected loudly with the valid modes listed. `test_an_unknown_mode_is_rejected_loudly` | Yes |

---

## E · Scope Boundaries — cases that prove what the system does *not* do

The brief lists seven prohibitions. These cases are negative by design.

| ID | Boundary | Expected result | Ships? |
|---|---|---|---|
| **TC-27** | No aggressive scraping | `robots.txt` read before every fetch, RFC 9309 semantics. A disallow is honoured **and recorded**. `test_robots_disallow_is_honoured_and_recorded` | Yes |
| **TC-28** | No restriction bypassing | An unreachable or failed `robots.txt` is treated as **disallow**, not as permission. A `403` on `robots.txt` does not disallow the whole site. Every refusal explains itself | Yes |
| **TC-29** | Honest identification | `robots.txt` is requested with the same User-Agent used for pages: `FQL-VendorDD-Prototype/0.1`. `test_robots_txt_is_requested_with_our_own_user_agent` | Yes |
| **TC-30** | Bounded collection | 2.0 s delay per domain; **10 pages kept**, **20 requests made** per vendor. The budget announces itself rather than silently dropping pages | Yes |
| **TC-31** | No private portals, no credentials | **No credential-handling code exists anywhere in `src\`.** Searched for `password`, `api_key`, `token`, `cookie`, `login`, `bearer` and `auth`: the only hits are the word *authoritative* in the ranking rules. There is no login, token, cookie-jar or auth-header path to misuse | Yes |
| **TC-32** | No paid tools, no heavy infrastructure | No API key, no account, no GPU, no hosted model, no vector store. `requirements.txt` is eight packages, all from the brief's own suggested stack: `streamlit`, `pandas`, `requests`, `beautifulsoup4`, `lxml`, **`trafilatura`**, `PyYAML`, `pytest` | Yes |
| **TC-33** | Not a decision system | Every export states it is a first-pass internal research aid and that final review remains manual. No risk score, rating or approval is produced anywhere | Yes |

---

## F · The automated suite

| File | Tests | What it protects |
|---|---|---|
| `test_agent1.py` | 15 | Seed URLs beat guessed patterns · unresolvable page types are flagged · caps and budgets hold · a run replays without refetching |
| `test_agent2.py` | 29 | Blocks not pages · quotes are verbatim · citations contain what they cite · loader noise is not evidence · PARTIAL is reachable |
| `test_agent3.py` | 21 | Coverage, missing categories, conflicts and flags · a field whose home page was unreadable cannot score High |
| `test_export.py` | 15 | All twelve brief items in all three formats · CSV round-trips hostile text · the download equals the file on disk |
| `test_app_smoke.py` | 12 | The five review stages and three exports exist · the six-link chain renders · no axis is ever shown alone |
| `test_parse.py` | 10 | HTML → blocks, on fixtures modelled on real vendor pages |
| `test_orchestrator.py` | 9 | The three modes, and what each refuses to do |
| `test_fetch_robots.py` | 6 | RFC 9309 semantics, including every failure path |
| `test_text_quality.py` | 6 | Readable-vs-unreadable, the measure everything else depends on |
| **Total** | **123 functions → 152 tests** | |

**Fifty-three defects have been found in this project. This suite caught one of them.** The rest
came from reading the output against the source page, from re-running the workflow end to end,
from reading the brief line by line rather than a summary of it — and, for the last six, from
opening the app and reading a tab, and from cloning the repository and following the README.
**All 152 tests passed through every one of those six.** Every UI test asserts what the app hands
to Streamlit and every export test writes to a temporary directory, so none of them can see a
heading above an empty quote or a checker's verdict in a directory that does not exist here.
**TC-6, TC-23c, TC-25b and TC-25c are the checks that cover them, and all four are manual by
necessity.** That is the
honest reason this document leads with runnable queries and real vendors instead of with the suite:
**a test proves the code does what it was written to do, and most of the defects here were the code
faithfully doing the wrong thing.**

---

## G · What this document is for, after submission

Two checks belong to every future change, and both are here because skipping them has already cost
this project a day:

1. **After any change under `src\`, run in this order:** `run_workflow --mode replay` →
   `verify_corpus` → `export_all`. Skipping the replay leaves `data\` written by older code.
2. **TC-6 is the one no automated test can replace.** Every export test writes to a temporary
   directory, so the suite verifies the *code* and never the *artifacts that ship*. On 19 August
   the CSV exporter was fixed to carry all twelve brief items and `data\exports\` was not
   regenerated — the code was correct and the delivered sample outputs were four hours old. **Run
   `tools\export_all.py` and re-check the column count before packaging.**

---

## Traceability — brief requirement to case

| Brief section | Requirement | Cases |
|---|---|---|
| Expected Input | vendor name or list | TQ-1, TQ-2, TQ-3 |
| Expected Input | collected URLs or pre-prepared source file | TQ-4 |
| Expected Input | optional research category filter | TQ-5 – TQ-8 |
| Expected Output | all twelve brief items | TC-1 – TC-5 |
| Streamlit interface | all seven capabilities | TC-7 – TC-13 |
| Scope Boundaries | all seven prohibitions | TC-27 – TC-33 |
| Success Criteria | runs locally on a standard laptop | TC-24, TC-32 |
| Success Criteria | simple, controlled, understandable agent structure | TC-10, TC-26 |
| Success Criteria | credible public sources | TQ-4, TC-27 – TC-29 |
| Success Criteria | structured, easy-to-review output | TC-1 – TC-5, TC-8 |
| Success Criteria | briefs include source references | TC-11, TC-12 |
| Success Criteria | missing information flagged, not guessed | TC-16 – TC-22 |
| Success Criteria | usable by a non-technical reviewer | TC-12, TC-14, TC-15, **TC-25b, TC-25c** |
| Success Criteria | the archive a reviewer actually receives behaves | TC-6, **TC-23c**, TC-23, TC-24 |
| Success Criteria | low-cost, no heavy infrastructure | TC-32 |
| Success Criteria | assumptions and manual-review boundaries documented | TC-21, TC-33, `docs\assumptions_limitations.md` |
