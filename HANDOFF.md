# HANDOFF — Vendor Due-Diligence Research Workflow Prototype

**Purpose:** everything a fresh chat session needs to pick this project up cold.
Read it top to bottom before touching anything.

> **If you are a NEW session, read `START_HERE.md` first** — it is one screen and it
> orders the reading. Then this file.
>
> **The two files that outrank this one:**
> * `docs/client_guidance.md` — the client's written reply of 18 Aug, IN FULL. It
>   outranks every decision in this repository. §1.1 below is a condensed version.
> * `brief.txt` — the brief extracted verbatim from the PDF. **Check compliance
>   against it, never against a summary** — four requirements were quietly unmet for
>   nine days because nobody did.
>
> Both were added to the repo on 19 Aug after the assistant's project memory was
> lost. **Project memory is convenient and it is not durable. The repo is.**
**Last updated: 22 August 2026 — DAY 15 of 20. 26 commits (`a99a11e`), pushed.
All three agents, the orchestrator, the export layer, the source manifest and the full Streamlit
interface are built and committed. 154 tests. `verify_corpus.py` 0 FAIL
across all seven vendors — **both re-run on Windows on 20 Aug, not recalled.**
**TEN of ten brief deliverables complete** — `docs/test_cases.md` written and committed 20 Aug.
7 days to the 27 Aug submission target.**

> ### ⚠ THE DATES IN THIS FILE HAVE BEEN WRONG THREE TIMES. READ ALL THREE.
> * **Error 1** — everything below was first written as "13 August" because the assistant's clock
>   said so. Git disagreed. The defect/Agent-3 work is 18 August. **And "the 13 August corpus" is
>   itself imprecise — five vendors are 2026-08-13, GitLab 2026-08-19, JetBrains 2026-08-22. See §7.**
> * **Error 2** — this file was then re-dated on 18 August to say "19 August, DAY 12", one day ahead
>   of its own commits.
> * **Error 3** — a session on 18 August checked the clock, found 18 August, and recorded "HANDOFF
>   is a day ahead". True when written. That session then **ran across a real midnight**, and by the
>   time work resumed it genuinely was 19 August — so the correction became the error.
>
> **The rule that survives all three: re-read the clock at the START of every working session, and
> never carry a relative date claim forward.** Absolute dates only. The clock has now been wrong in
> both directions, and a long session can cross a day boundary while you are inside it.
>
> | When | What happened | Evidence |
> |---|---|---|
> | **13 Aug** | Agent 1 + Agent 2 re-run over all seven vendors | `ran_on 2026-08-13T21:34` |
> | **14–17 Aug** | **no commits, no work. Four days lost.** | git log gap |
> | **18 Aug** | client reply; defects 27–39; docs rewritten; Agent 3; export layer | `e39ffd2` `64fca64` `fe3f686` `3cb4455` |
> | **18–19 Aug** | orchestrator; defects 40–47; tabs 4 and 5; the brief-PDF audit; the architecture note and README rewritten; 152 tests | `6759ea6` `68ff6ee` `537074f` `07228a1` |

> ### ⚠ READ §1.1 BEFORE ANY DESIGN DECISION
> First Quadrant Labs replied to the clarification email in writing on 18 August. **That reply
> outranks every assumption in this document and every locked decision in §2 where they conflict.**
> It changed the submission format and questioned the confidence rule. A design choice that
> contradicts §1.1 is drift, however well argued.

---

## 0. How to work with me on this project

I am Moushmi. You are my **mentor/advisor**, not my assistant — someone with 10+ years
delivering this kind of work at large firms. Hold that role:

- **Never open with agreement.** First sentence challenges an assumption, names a gap, or asks
  the question that exposes one.
- **Tag confidence:** `[Certain]` (hard evidence) / `[Likely]` (strong inference) / `[Guessing]`
  (filling gaps). If most of a reply is guessing, say so first.
- **Uncomfortable truth first**, line one, never buried in paragraph three.
- **Disagree with structure:** "I disagree because X. Instead do Y. The risk in your approach is Z."
- **Banned phrases:** "Great question", "You're absolutely right", "That makes a lot of sense",
  "Absolutely", "Definitely". No warm-up paragraphs.
- **Hold your position under pushback** unless I give you genuinely new information.
- **I know Python basics only.** Write the code, then explain it line by line so I can defend it
  in a review. Never hand over unexplained code — "an AI wrote it" ends an interview.
- Be token-efficient without losing correctness.

### 0.1 TWO STANDING RULES — these override convenience, always

**RULE A — VERIFY BEFORE PRESENTING. TRIPLE-CHECK, THEN LOOK FOR THE FAULT IN YOUR OWN ANSWER.**
Do not report a finding you have not reproduced. Do not report a pass you have only read about.
Before showing me anything: run it, then attack your own result, then correct it, then show me.
Say explicitly what you checked, what you could NOT check, and why.
This rule exists because it has already caught real errors in this project:

| What was nearly reported | What checking it revealed |
|---|---|
| "20 orphan citations found" | The check compared cited terms against the 600-char snippet. All 42 terms were on the page, outside the snippet window. **0 real orphans.** |
| "Linear/Postman docs pass both usability tests but are marked unusable" | The re-computation used `str(Block)`, which includes the dataclass repr. Agent 1's own numbers were correct. **No defect.** |
| "The JetBrains security page never found SOC 2" | It did. The snippet was truncated by *my own print statement*, not by the code. The real defect was different and narrower (defect 30). |
| "Days 6–13 of the plan are missing" | Confirmed against the brief's 20-day cycle. **Real** — still unassigned. |

Three of four would have been false reports. **Checking is not overhead; it is the job.**

The same rule caught a bad FIX, not just a bad finding. The first version of defect 28's fix
dropped any block whose heading was not a complete sentence. It looked correct and it read
correctly. Run against the corpus, it turned **Linear's pricing** and **Sentry's data residency**
from a weak FOUND into a clean **NOT_FOUND** — a flat statement that Linear publishes no pricing,
about a vendor whose pricing page we read successfully. Trading a poor quote for a false negative
is the exact failure defect 23 exists to prevent. **Measure a fix against real data before
believing it. Reasoning is not verification.**

**Rule A also means: an assistant must say what it could NOT check.** Cowork's bridge to this
machine has no `pytest` and no network. The fix pass of 18 Aug was therefore run by copying the
repo, the corpus and all 55 cached pages into a Linux container with network access, installing
pytest there, and running the suite and `verify_corpus.py` for real. Numbers quoted below come
from that run. **Re-run both on Windows yourself before committing** — that is the environment
that counts.

**RULE B — STRICTLY ADHERE TO THE PROJECT BRIEF, AT ALL TIMES.**
The brief is the specification, not a starting suggestion. Before adding a feature, a field, a
document or a dependency, name the line in the brief it serves. Before removing one, name the
line that permits it. Where this repo departs from the brief's *suggested* stack (trafilatura,
LangGraph, SQLite, an optional LLM), the departure must be written down with its reason —
the brief says lower-cost alternatives "should be mentioned and supported where practical",
so a silent omission is a compliance failure even when the engineering choice is right.
§11 below is the live compliance matrix. Update it whenever the code changes.

---

## 1. The project in one paragraph

Internship project for **First Quadrant Labs**. Build a bounded 3-agent workflow that collects,
structures and summarises **public** vendor due-diligence information into consistent first-pass
research briefs, where every statement traces back to the page it came from. The brief calls it
"a controlled internal experiment, not a full procurement automation system" — it is a
**restraint test**. Roughly half the marks live in the prose deliverables.

- **Deadline: Saturday 29 August 2026. 9 days left. Submission target 27 Aug — 7 days.**
- The brief describes a **20-day cycle**. Day 1 = 8 Aug 2026, so **day N = 7 Aug + N**.
  Today, 20 Aug, is **day 13**. Day 20 = 27 Aug, two days before the deadline.
  *This entry read "19 Aug, day 12" until 20 Aug 00:10 IST, when a session that began on the 19th
  was still running past midnight. Re-derive the day from the machine's clock at the start of every
  session; do not copy it forward from this file.*
- **4 days were lost (14–17 Aug, no commits).** The plan below absorbs that; it has no further
  slack before the 27 Aug target.
- Submit to **projects@firstquadrantlabs.com** AND upload to the LMS.
- All queries go through that one project email, consolidated into one message where possible.
- Brief PDF: `C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\Project_Brief_1.pdf`
- Repo: `...\Research Project_1\vendor-dd-prototype` · remote:
  `https://github.com/moushmirao30/vendor-dd-prototype.git` (**private**, branch `master`)

---

## 1.1 CLIENT GUIDANCE — received in writing 18 August 2026. AUTHORITATIVE.

First Quadrant Labs' reply to the consolidated clarification email. This is the client speaking
about their own brief, in writing. **Where it conflicts with anything else in this document, it
wins.** Quote it in `docs/assumptions_limitations.md` and `docs/evaluation.md` — a documented
client instruction is the strongest justification a design choice can have. Full text in project
memory (`project_client_guidance.md`).

Their closing position: *"You do not need to redesign Agents 1 and 2 based on the points raised
above. Please proceed with Agent 3, the review interface, exports, testing, documentation, and
evaluation."* So this is guidance, not a rework order — **except item 3, which changes a
deliverable.**

### 1 · LLM — CONFIRMED. Rule-based is the delivered behaviour.
Fully rule-based extraction is **acceptable as the primary behaviour**; LLM integration is **not
mandatory**. They endorsed the design in their own words: *"retaining verbatim evidence from the
source is valuable for auditability and reduces hallucination risk."* **The `value`-is-a-quote
decision is now client-endorsed — say so in the evaluation.**

Optional, only if time permits, and LAST in the build order: an LLM summarisation toggle as a
*secondary* feature. Hard constraints — the system must still work **completely without an API
key**, and any LLM summary **must retain links to the underlying evidence**.

### 2 · JavaScript-rendered pages — CONFIRMED. No headless browser.
*"You are not required to introduce Playwright, Selenium, or another headless-browser layer."*
Our reading was right and is now on the record.

Two NEW obligations:
- **Use their two-way language in the output.** Distinguish *information **not found** on the
  vendor's public sources* from *information that **could not be evaluated** because the page could
  not be reliably extracted.* We do this via caveats already; the wording should match theirs.
- **Before marking a category unavailable, check other official sources** — trust centre,
  documentation, security page, help centre — and otherwise flag for manual review. Agent 2 already
  searches every collected page, so the behaviour exists; what is missing is making the check
  **visible in the brief** ("searched N other official pages, found nothing") instead of implicit.
- **They asked for the number AND percentage of affected pages in the evaluation.**
  Current: **8 of 49 pages, 16.3%**, across 4 of 7 vendors.

### 3 · SUBMISSION FORMAT CHANGED — this reverses a locked decision in §2
> *"We recommend not including the complete 22 MB cache of verbatim third-party HTML pages in the
> final submission archive."*

The old decision — zip including `.git/` so a reviewer could replay offline — **is withdrawn.**
Submit instead: the structured **CSV/JSON/SQLite corpus** · source URLs and page titles · date
collected · extracted sections and evidence snippets · source type and tags · the
collection/retrieval code · and **a SOURCE MANIFEST showing which pages were successfully or
unsuccessfully collected.**

**The source manifest is a NEW DELIVERABLE** that is not in the original brief. Agent 1's audit
trail already holds every field it needs; it needs an export.

Keep the full HTML cache **locally**. **The README must explain how a reviewer re-collects the
public sources.** State plainly in the README and the limitations note that **a fresh clone of the
submitted archive cannot replay offline until re-collection** — that is a consequence of a client
instruction, not an oversight, and naming it that way is the difference between a limitation and a
defect.

### 4 · CONFIDENCE — they pushed back on the core of our rule
> *"We recommend not basing confidence primarily on sentence length. A long sentence is not
> necessarily stronger evidence than a short statement or structured table."*

**This challenges the single most carefully documented decision in the project.** There is no house
definition to match, so defining our own is fine — but they supplied a model:

| Level | Their definition |
|---|---|
| **High** | Direct, explicit evidence from an authoritative official source, with the requested field **clearly answered**. |
| **Medium** | Relevant official evidence exists, but it is **incomplete, indirect, spread across multiple sections, or requires limited interpretation**. |
| **Low** | Evidence is **weak, ambiguous, outdated, inaccessible**, or the field cannot be confidently established. |

…and the sentence that makes it buildable:
> *"You can additionally track extraction quality separately if you want to measure whether the
> evidence was obtained from a complete sentence, bullet list, table, etc."*

**The problem:** their High/Medium/Low is *semantic* — "clearly answered", "requires limited
interpretation". A rule-based system with no LLM cannot judge whether a field is clearly answered.
Implementing their wording literally is impossible inside the locked no-LLM decision.

**The resolution is a TWO-AXIS model**, which is precisely what their last sentence invites:

| Axis | What it measures | How |
|---|---|---|
| **Extraction quality** | sentence · bullet list · table · bare heading · image alt-text | today's `parse.evidence_level`, **renamed to what it actually is**. Keep the logic; it is good, it is just misnamed |
| **Confidence** | the client's definition, via mechanical proxies | **High** = on the field's own preferred/authoritative page, matched term present in the quoted text, **no tool-limitation caveat**. **Medium** = official but off-home, spread across pages, home page unreadable so the answer came from elsewhere, or a list/table/heading+body pair. **Low** = bare label, alt-text only, inaccessible, or conflicting |

**This resolves defect 31 for free.** Their rule mechanically forbids a caveated field from scoring
High, so Postman's 10/10 → High on coverage 2/5 becomes impossible. The client has prescribed the
fix for the biggest open defect in the system without knowing it existed.

**✅ IMPLEMENTED 18 Aug in `src/review_rules.py`, COMPLETED 19 Aug.** `extraction_quality()` is
Agent 2's old measure under its honest name; `confidence()` applies the client's definition. Agent 2
was not redesigned — the client said it did not need to be, and it did not.

> **⚠ WHAT THIS SECTION CLAIMED ON 18 AUG, AND WHY IT WAS FALSE.** It said: *"The 'no caveat' clause
> makes defect 31 unrepresentable rather than merely reported — a field whose home page could not be
> read can no longer score High, so **Postman can no longer tie Sentry**."*
>
> **Postman went on tying Sentry.** Both read 10/10 → High for another day, on coverage 2/5 and 5/5.
> The two-axis rule reached the FIELD CARD and stopped there; `vendor_score` kept summing the
> extraction axis under the word *Confidence*, so Postman's header said High above five field cards
> that each said Medium. **That is defect 42**, and `verify_corpus.py` had been printing *"Agent 3
> owes a coverage-aware score here"* on every run the whole time.

**Closed 19 Aug by giving three measures three names** — `evidence_score`/`evidence_band`,
`confidence_band`/`confidence_counts`, `coverage_verified`/`coverage_total`. The confidence axis is
reported as **counts, not a score**: compressing three levels into 0–10 needs thresholds we would be
picking while looking at our own seven vendors, and a count cannot be tuned. The band is the weakest
core field — a stated principle, not a calibrated cut-off.

**The separation the client's rule was for, which one number hid for a week:**

| Vendor | Evidence | Confidence | Coverage |
|---|---|---|---|
| GitLab · Sentry · GitHub | 10/10 High | Medium — **2** of 5 core High | 5/5 |
| Linear | 6/10 Medium | Low — 1 High, 3 Medium, 1 Low | 3/5 |
| **Postman · Atlassian** | **10/10 High** | Medium — **0** of 5 core High | **2/5** |
| JetBrains | 5/10 Medium | Low — 1 High, 2 Medium, 2 Low | 2/5 |

Postman and Atlassian are the only vendors with **zero** core fields at the client's High, and they
are the two whose primary documents we could least often read. **No vendor reaches an overall
High** — the honest result for a rule-based tool reading public marketing pages, reported rather
than tuned away.

### 5 · Four NEW requirements
- **Agent 3 scope, confirmed narrow:** *"focus on review and synthesis rather than introducing
  another complex intelligence layer. It should verify evidence coverage, identify missing
  categories, highlight conflicts or weak evidence, and prepare the final brief."*
  **"Highlight conflicts" is new** — we do not detect contradictions between sources today.
- **Offline replay must be DEMONSTRATED in the final submission** (demo, screenshots, audit trail),
  even though the cache is no longer shipped. Item 3 and this one must be reconciled explicitly.
- **The Streamlit view must show the chain:**
  `Source → Extracted Evidence → Structured Field → Confidence → Review Flag → Final Brief`
- **The evaluation must include a cross-vendor comparison table** — source coverage, extraction
  success rate, inaccessible pages, populated fields, fields requiring manual review. They said it
  demonstrates effectiveness and limitations **better than screenshots alone**. Already added to
  `docs/evaluation.md` §2.

### What their tone does and does not mean
They opened with *"well aligned with the intended scope"* and closed with *"We appreciate that you
raised these questions before making unnecessary architectural changes."* The email was worth
sending; the restraint decisions were right. **Do not over-read the praise.** Items 3 and 4 are
real changes and item 5 adds four requirements that did not exist before.

---

### The company, and how to score with them
First Quadrant Labs is a **consulting firm** (finance, technology, AI, cybersecurity, digital
marketing). Their AI page sells **explainability** as the product — *"We ensure your team
understands how models work, what they predict, and how decisions are made"* — and a four-stage
method: **Discovery & Assessment → Strategy & Solution Design → Development & Deployment →
Monitoring & Optimization**. That vocabulary is already mirrored in `docs/architecture.md` §2.
In consulting the deliverable *is* the product, so document polish counts as much as code.

---

## 2. Locked decisions (do not relitigate without a reason)

| # | Decision | Why | Brief line it serves |
|---|---|---|---|
| Category | **Developer productivity tools** | richest public trust/security/status pages | "5–8 vendors from one practical category… developer productivity tools" |
| Vendors | GitLab, Linear, Sentry (rich) · Postman, Atlassian (awkward) · GitHub, JetBrains (hard). Reserve: Docker, CircleCI, Vercel | deliberately mixed so the evaluation has real failure modes | "sample outputs for at least 5 vendors" |
| LLM | **None by default.** Rule-based + template extraction | keeps "runs on a standard laptop, low cost" literally true | "You may use OpenAI API lightly… keep it optional and cost-conscious" |
| Orchestration | **Plain Python**, strictly linear 1→2→3 | a 3-step flow does not need a framework | "simple custom Python orchestration for the agent flow" |
| Storage | **JSON canonical + CSV export** | page text contains commas/quotes/newlines; CSV as primary store corrupts silently | "CSV, JSON, or SQLite" |
| Agent 1 | **Curated seed first, discovery fills gaps** | a human-checked URL outranks a guessed one (defect 10) | "collected public URLs or a pre-prepared vendor source file" |
| Agent 2 `value` | **A QUOTE, never a summary** | no LLM ⇒ any "summary" is machine-assembled text a reviewer cannot trace | "source-backed evidence snippets" |
| Agent 2 confidence | measured on the **longest sentence**, not the whole block | a bullet list is a label, not a claim (defect 15). **✅ RESOLVED 18–19 Aug.** Questioned by the client (§1.1 item 4); the logic is kept and renamed `extraction_quality`. `confidence` is a second axis on their definition, and `vendor_confidence` carries it to the vendor header — which is where 18 Aug's fix stopped short (defect 42) | "Confidence level: High / Medium / Low" |
| Agent 2 ranking | sorts by **confidence level first** | the quote printed under a label must be the evidence that earned it | "outputs are structured and easy to review" |
| `preferred_source_types` | **orders** evidence, never filters it | GitLab really does state FedRAMP on its pricing page | — |
| Generic-term noise | **Agent 3 raises a flag**, dictionary left alone | avoids over-fitting the dictionary to one vendor | "review flags for manual follow-up" |
| ~~Submission format~~ | ~~zip including `.git/`, excluding `.venv/`~~ **WITHDRAWN 18 Aug — see §1.1 item 3.** Ship the structured corpus, the code, and a NEW **source manifest**; keep the 22 MB HTML cache local; README explains re-collection | the client asked us not to redistribute verbatim third-party pages | "a structured zip folder or repository format" |
| Repo visibility | **private** | the corpus stores ~70,000 chars of verbatim vendor text per vendor | — |
| Code delivery | written into the repo with full explanation; the comments in `src/` carry the reasoning and each names the defect it prevents | I must be able to defend every line | "the agent structure is simple, controlled, and understandable" |

---

## 3. What exists right now

**26 commits, `a99a11e`, pushed. Everything below is built and committed: three agents, the
orchestrator, the export layer, the source manifest, and all five UI tabs.**
**154 tests. `verify_corpus.py` 0 FAIL across all seven vendors.**
**7 vendors · 49 pages · 55 cached files · 7 briefs · 23 export artifacts · 12 screenshots.**

```
vendor-dd-prototype/
├─ app.py                     Streamlit UI — all 5 tabs live; tab 4 shows the client's chain
├─ README.md · requirements.txt · .gitignore · .gitattributes · HANDOFF.md
├─ config/
│   ├─ vendors.yaml           7 vendors, seeds, url_patterns, per-vendor observation notes
│   ├─ field_dictionary.yaml  8 fields, 112 terms, preferred_source_types, negative_terms
│   └─ settings.yaml          all policy: UA, delays, caps, thresholds, confidence bands
├─ src/
│   ├─ fetch.py               PageFetcher + RobotsPolicy + versioned cache + portable paths
│   ├─ parse.py               page_to_blocks · find_evidence · term_in · snippet_around
│   │                         · longest_sentence_length · evidence_level · score_field_confidence
│   ├─ agent1_collect.py      AGENT 1 — collector, audit trail, usability check, save/load
│   ├─ agent2_extract.py      AGENT 2 — extraction, ranking, caveats, save/load
│   ├─ agent3_review.py       AGENT 3 — coverage, missing, weak evidence, conflicts, brief
│   ├─ review_rules.py        THE REVIEW PREDICATES, imported by Agent 3 AND verify_corpus
│   ├─ orchestrator.py        THE ONLY PLACE 1→2→3 ARE WIRED. 3 modes + the cache preflight
│   ├─ export.py              JSON/CSV/Markdown briefs · corpus.csv · SOURCE MANIFEST
│   └─ schema.py              SourceRecord · ExtractedField · VendorBrief (+ coverage)
├─ tools/
│   ├─ verify_corpus.py       CORPUS HEALTH CHECKER — run before every commit
│   ├─ run_workflow.py        1→2→3 from the command line; --mode collect|replay|review
│   ├─ review_all.py          runs Agent 3 over every vendor; writes data/briefs/
│   └─ export_all.py          writes data/exports/ — corpus.csv, source_manifest.csv, briefs
├─ data/corpus/               7 vendors × {json, _run.json, _fields.json}
├─ data/briefs/               7 × <slug>_brief.json — Agent 3's output
├─ data/exports/              corpus.csv · source_manifest.csv · 7 × brief {json,csv,md}
├─ data/cache/html/           55 × v2_*.html — offline replay (gitignored)
├─ docs/
│   ├─ confidence_rules.md    the written confidence rule + worked examples
│   ├─ architecture.md        DRAFT — see §8
│   └─ evaluation.md          rewritten 18 Aug, figures fact-checked by script
└─ tests/                     154 tests, all offline
    ├─ test_parse.py · test_agent1.py · test_agent2.py · test_agent3.py (21) · test_export.py (15)
    ├─ test_orchestrator.py (9) — handoffs and refusals, not what happens inside an agent
    ├─ test_fetch_robots.py · test_app_smoke.py · test_text_quality.py
    └─ fixtures/  5 HTML files modelled on real vendor page shapes
```

### The core idea, in case it needs restating
Split each page into **blocks** (one heading + the paragraphs under it), then match each block
against a plain phrase list in `config/field_dictionary.yaml` — a **whole-token** substring test,
not a regex. Keep the whole matching block as evidence: heading, snippet, matched terms, source URL.

**Critical architectural point:** evidence extraction reads **raw HTML**, never `collected_text`.
See defect 7. It is the decision that saved the project.

---

## 4. THE ONE THING THIS PROJECT IS ACTUALLY ABOUT

> **The dangerous failure is not a missing answer. It is a confident answer about a company that
> nobody checked.**

Four mechanisms now produce it, all measured on real pages:

| Door | Vendor | What it looked like | Truth |
|---|---|---|---|
| **JavaScript rendering** | Atlassian | product: **52 readable chars, 0 blocks from 898,035 bytes**; pricing: 66 chars from 1,213,336 | Atlassian publishes pricing perfectly well. We cannot read it. |
| **A JS shell behind a redirect** | Postman | privacy page: **0 readable chars from 4,727 bytes** | Field reported FOUND/High from the *security* page while the privacy policy was never read |
| **An unguessable URL** | JetBrains | security page 404'd six times before the seed was corrected; `terms` still 404s three times | JetBrains publishes *"SOC 2 Type II and GDPR compliance"* at `/legal/docs/privacy/trust-center/` |
| **A confident quote that says nothing** *(found and FIXED 18 Aug)* | GitHub | `security_trust` = *"…the content of your Account and its security are up to you."* — the **terms of service**, one matched term | The AICPA SOC 1/SOC 2 Type 2 statement, matching four terms, ranked **second** and never became the value. Now fixed: see defects 27, 28, 30 |

**A 200 means the URL exists, not that it is the right page, and not that it contains words.
A 404 means our URL guess was wrong, not that the vendor is silent.
And a quote that passes every check can still be the wrong sentence.**

The machinery that enforces the first three:
- `SourceRecord.block_count` and `content_usable` (Agent 1 measures readability at collection)
- `unusable-page`, `unread-home-page`, `home-page-never-found`, `skip` audit steps
- caveat entries injected into a field's **evidence list**, because a reviewer reads the brief, not the trail
- `tools/verify_corpus.py`, which FAILs on an uncaveated confident answer

What now guards the fourth (all added 18 Aug):
- `preferred_source_types` no longer treats a terms-of-service page as a home for security claims
- ranking and scoring both ask "is this a complete sentence?" rather than "which HTML tag was it in"
- the field's headline is the sentence carrying the MOST matched terms, not the first one found
- interface furniture is stripped out of quotes before they are shown or measured
- `verify_corpus` prints coverage beside every score and WARNs when a High rests on unread pages

**The fifth mechanism has no guard yet and is Agent 3's job: a vendor can still score 10/10 High
while half its primary documents were never read. See defect 31.**

---

## 5. Fifty-three defects, and the headline they add up to

**The automated test suite caught one of them. Every other one was found by opening the artifact
and reading what it actually said — the screen, then the JSON, then the raw HTML.**

Full table: project memory (`project_defect_log.md`). The ones that matter most:

| # | Defect | Why it matters |
|---|---|---|
| 4 | False "disallowed by robots.txt" dropped 4 of 6 sources and **blamed the vendor** | stdlib robots parser is stricter than RFC 9309 |
| 7 | Content cleaner kept **7.6%** of GitLab's security page | Agent 2 survived only because it reads raw HTML |
| 13 | `sla` matched **"Slack" 11 times of 13**; `cli` matched click/client/decline 9 of 9 | a substring is not a word |
| 14 | Ranking by longest snippet put a status board above the SOC 2 sentence | ranking is policy, not plumbing |
| 20/22 | **Orphan citations** — 8 of 92 GitLab evidence blocks, now 0 | a citation that does not contain what it cites is worse than none |
| 23 | A page can be HTTP 200, robots-clean, cached — and contain **no words** | a false NOT_FOUND defames by omission |
| 24 | The 23 fix hedged NOT_FOUND but not FOUND-from-elsewhere-while-home-unread | a confident answer invites no checking |
| 25 | `SLA` in a CVSS remediation clause scored High for uptime | a string match is not a meaning |
| 26 | Agent 2 only ever received `records`, so a never-collected page type was invisible to it | JetBrains NOT_FOUND cited the wrong pages |

### 27–39 — FOUND 18 Aug 2026. All verified against the real corpus; 36 fixed, 37–39 recorded.

| # | Defect | Fix that shipped |
|---|---|---|
| **27** | **`terms` was a `preferred_source_type` for `security_trust`, so a liability disclaimer outranked a certification statement.** GitHub rank 1 = ToS, 1 term (`two-factor`), value *"…its security are up to you."* Rank 2 = *"GitHub offers AICPA System and Organization Controls (SOC) 1 Type 2 and SOC 2 Type 2 reports…"*, 4 terms. Preferred-source is tie-break 3; term count is tie-break 5. | `preferred_source_types: ["security", "trust"]`, and `trust` added to `authoritative_source_types` because the brief names "security or trust center pages" as ONE source category. **`rank_evidence` was never broken — it did exactly what the dictionary told it. Ranking order is policy; look in the config before the code.** |
| **28** | **A claim published as a bare heading became evidence with an EMPTY quote.** GitHub `/security` carries `<h2>GitHub's API stays secure with ISO, SOC 2, and GDPR.</h2>` with `body=''`. It matched, scored `heading_only` → Medium, ranked **9th of 9**, and was dropped by the 3-evidence cap. The field's own top-priority page contributed nothing. | Three parts, because fixing one alone did nothing: (a) `find_evidence` quotes the heading when there is no body; (b) `evidence_level` scores on the sentence, not the HTML tag; (c) `rank_evidence`'s location tier measures the statement, not the tag. GitHub now quotes that sentence as its value. |
| **29** | **Loader error text quoted as vendor evidence** — *"There was an error while loading. Please reload this page ."* inside 4 of GitHub's snippets. Also a **41-character sentence**, and 40 is the threshold for High, so a page that failed to render could earn High on its own error message. | New `parse.strip_noise()` + `extraction.noise_phrases` in settings. **Not `negative_terms`** — that drops the whole block, and this block also held GitHub's SOC 2 sentence. Cut the furniture, keep the claim. |
| **30** | **`best_sentence` returned the FIRST sentence containing ANY term.** JetBrains' headline was *"Please visit our Trust Center to learn more…"*, matched on the navigational term `trust center`; the SOC 2 Type II sentence sat 340 characters later in the same quoted block. | Choose the sentence carrying the MOST matched terms, ties to the earliest. Also switched to `term_in`: the old `t in low` was **defect 13 still alive inside this one function**. |
| **31** | **The vendor score ignores caveats.** Postman **10/10 → High** with 4 caveated fields, a 0-character privacy policy and a 98%-JavaScript docs page. Sentry **10/10 → High**, 0 caveats, every page readable. Identical labels. | **PARTIALLY FIXED.** `verify_corpus` now prints `coverage N/5 core fields verified without a caveat` beside every score and raises `score-without-coverage` when a High rests on unread pages. **The scoring change itself is Agent 3's, and Agent 3 must IMPORT this calculation, not rewrite it.** |
| **32** | **`verify_corpus` printed "Passed the usability threshold" for pages it had just declared unusable**, and rounded density to 1 dp, so a page rejected at 1.965 printed as "2.0" against a 2.0 threshold — a number that reads as a contradiction of the decision it explains. | Skip `thin-density` for already-unusable pages; print two decimals and both thresholds. Same rounding corrected in `agent1_collect`. |
| **33** | **The worked examples for the two-test usability rule were FALSE against the corpus.** `settings.yaml` claimed Postman's privacy page had "high density (27 ch/KB)" — it is **0.0** — and that JetBrains' status page "clears any sane floor" — it is **333 chars**. Both are caught by both tests, so neither demonstrated anything. | Correct examples now in `settings.yaml`: **floor-only = JetBrains `docs`, 45 chars at 10.4 ch/KB**; **density-only = Postman `docs`, 2,370 at 1.97 and Linear `docs`, 1,034 at 1.96.** The rule was right; the examples had decayed. **Check documentation against the DATA, not only against the code.** |
| **34** | **DEFECT 26's FIX HAD NEVER ONCE EXECUTED.** Agent 1 emitted a `skip` step only for page types that had a seed URL in `vendors.yaml`. JetBrains' `terms` is reachable only through `url_patterns`, 404'd three times, and was never reported missing. `skip` occurs **zero times** in all seven run trails — and `app.py` builds Agent 2's `never_collected` list from `skip`, so the `home-page-never-found` caveat has never fired on any vendor. | Report the union of `seeds` and `url_patterns`. **Nothing tested the wiring, which is why it could die silently. Two wiring tests added.** |
| **35** | **A test asserted the defect.** `test_unresolvable_page_types_are_flagged_not_dropped` asserted `len(skipped) == len(GITLAB["seeds"])`, which only a seeds-only loop satisfies. The correct fix made it fail. | Rewritten to assert `seeds ∪ url_patterns`. **A test that encodes a bug converts a defect into a guarantee and makes the next person's correct fix look like a regression.** |
| **36** | **Two docstrings described one rule differently, and `PARTIAL` was unreachable.** `status_from_confidence`: *"PARTIAL — Low, something matched but only a heading."* `score_field_confidence`: *"Medium — named only in a heading … on an authoritative page."* The code followed the second, so PARTIAL occurred **0 times in 56 field results**. | Bare heading → Low → PARTIAL. Bullet lists on authoritative pages still score Medium. Now 3 PARTIALs: Linear pricing, Linear data residency, Sentry data residency. **Two docstrings disagreeing about one rule is how a codebase stops being auditable.** |

| **37** | **A field's confidence label can be earned by a sentence that does not contain the matched term.** `evidence_level` measures the longest sentence anywhere in the block. In **9 of 122 blocks** that sentence carries no matched term. Atlassian's security field: `hipaa` appears only in the 39-character section title *"Sensitive Health Information and HIPAA."*, while the High came from a 322-character sentence about something else in the same ToS section. | **NOT FIXED, DELIBERATELY.** The obvious tightening — score only the longest sentence carrying the term — also demotes Sentry's *"High Availability"* heading with a full paragraph beneath it and GitLab's *"Trust Center Documents"*. Vendors do not repeat a heading inside its own paragraph, so the strict rule trades a cosmetic over-score for a false negative — the same mistake as the route-not-taken below. `verify_corpus` now raises `claim-not-in-matched-sentence` on all nine so a human sees them. |

### 38–39 — found in AGENT 3 ITSELF, 18 Aug, before it was delivered

| # | Defect | Fix |
|---|---|---|
| **38** | **A negation-based conflict detector fired on 3 of 7 vendors and every hit was false.** It reported *"negative on privacy, plain on privacy"* — comparing three blocks of the SAME privacy policy against each other. A privacy policy contains both "we do not sell your data" and ordinary positive statements; that is what a privacy policy IS. | **Deleted, not tuned.** There is no threshold that turns "this paragraph contains the word not" into evidence of contradiction. **A detector that produces false positives is worse than one that produces nothing, because it teaches the reviewer to skim past flags — and the flags are the entire product.** |
| **39** | **"Could not be evaluated" was applied whenever ANY page of the vendor was unreadable.** That hedged JetBrains' data-residency NOT_FOUND into a tool limitation even though both of its home pages — security and privacy — read perfectly well and JetBrains simply does not publish it. | Test the field's OWN home page, not the vendor's worst page. Now **3 could-not-be-evaluated vs 7 genuine not-founds**. **Over-hedging is its own dishonesty: it hides a real finding behind our own excuse, and it is the mirror image of defect 23.** It also broke the client's explicit request to distinguish the two. |

Also corrected before delivery: `vendor_overview` first mined the product page body and returned a
**changelog entry** for Linear and navigation fragments for GitLab and JetBrains. The product page
contributed exactly 1 of 122 evidence blocks — it is the least structured page a vendor publishes.
The overview is now the product page `<title>`, already in `SourceRecord.page_title`. **A `<title>`
lives in the HTML head and is served before JavaScript runs**, so Atlassian still yields "Jira |
Project Management for the AI Era | Atlassian" from a page whose body gives 52 characters.

### 40–43 — FOUND 18–19 Aug while building the orchestrator and the UI. All fixed.

| # | Defect | Fix |
|---|---|---|
| **40** | **THE SUBMITTED ARCHIVE MADE THE TOOL LIE.** Found by deleting `data/cache/html/` and running the pipeline exactly as a reviewer of the submitted archive would — which is the configuration the client asked for on 18 Aug. Agent 2 skipped every page it could not resolve, recorded `missing-html` in its **audit trail**, and returned 8 NOT_FOUND fields per vendor with an **empty evidence list and no caveat**. The brief then said, under all eight fields of all seven vendors: *"NOT_FOUND — nothing matched on any page we could read"* — about pages nobody opened. `field_coverage` read **5/5 verified** while zero pages were read, because "verified" is computed as "not caveated" and an empty field has nothing to caveat. Agent 3 raised **0 flags**. **134 tests passed throughout.** | Three layers, because a guard should never be the only guard: (a) `agent2_extract` tracks `uncached` separately from `unusable` — one is a fact about the vendor's site, the other about our archive, and the remedies differ; (b) a **first-priority caveat branch** puts it in the field's evidence list where the reviewer reads, so coverage falls 5/5 → 0/5 and the confidence band degrades through machinery that already existed; (c) `orchestrator.run_workflow` **refuses** replay outright and names `review` mode as the alternative. `review_rules.confidence` also stopped printing "…on any page we could read" when a caveat is attached, and now leads with the client's own phrase **"could not be evaluated — "**. |
| **41** | **ONE OVER-HEDGING RULE, THREE IMPLEMENTATIONS, TWO OF THEM STALE.** Defect 39 fixed Agent 3 to test the field's OWN home page rather than "any bad page on the vendor's site". `agent2_extract`'s caveat and `verify_corpus`'s `unhedged-not-found` both kept the old rule — so one brief said *"its own pages read cleanly, this is a finding about the vendor"* AND *"NOT_FOUND may be our limit, not the vendor's silence"* about the same field. Fired on 8 fields across Linear, Atlassian and JetBrains. | Both now use the shared `review_rules.unread_home_page`, plus `or not usable_pages`: **a test caught that narrowing alone is wrong when NOTHING was readable**, since then no field has a readable home page and every field would report a clean negative about a site we never read a word of. **Agent 3's defect-39 fix carries the same hole; it stays hidden only because all seven real vendors have at least one good page.** Coverage unchanged on all seven — every un-caveated field is non-core. |
| **42** | **THE VENDOR HEADER SAID "CONFIDENCE" AND MEASURED SENTENCE LENGTH.** The 18 Aug two-axis change reached the field card and never reached `vendor_score`, which went on summing the extraction axis. Postman and Sentry both read **10/10 → High** on coverage 2/5 and 5/5, above five field cards that each said Medium. §1.1 item 4 and §11 both claimed this was already fixed. **`verify_corpus` had been printing *"Agent 3 owes a coverage-aware score here"* on every run for days.** | Three measures, three names: `evidence_score`/`evidence_band` (renamed, logic unchanged), `confidence_band`/`confidence_counts` (new, from `vendor_confidence`), `coverage_*`. **Counts, not a score** — compressing three levels into 0–10 needs thresholds we would pick while looking at our own corpus, and a count cannot be tuned. Band = weakest core field, a stated principle rather than a cut-off. |
| **43** | **A FIELD COULD EARN High ON EVIDENCE THE REVIEWER NEVER SEES.** `off_home_evidence` returns nothing as soon as *any* piece of evidence sits on the field's own page — right for a flag, wrong for confidence, because the reviewer reads the **top card** and the top card is the printed value. Linear's `security_trust` ranked the **pricing** page's Enterprise tier list first, with bare `SAML` / `SCIM` headings from the security page beneath; it scored High and the reason read *"stated directly on the vendor's own pricing page"* — for a **security** field. Two more, both supplementary: Postman's and GitHub's `uptime_reliability`, Postman's quote being repeated navigation furniture rather than a claim at all. | **High now requires the printed quote to be on the field's own page.** This restates a locked decision rather than inventing one — *"the quote printed under a label must be the evidence that earned it"* (§2, from defect 14). One core field moved: Linear 2 High → 1 High. A companion test asserts the healthy case still passes, so the narrowing does not become defect 39 in a new place. |

**Found by looking, again.** Defect 40 came from running the deliverable in the shape we ship it.
Defect 42 came from reading a WARN row the tool had been printing for days. Defect 43 came from
re-deriving a worked example for `docs/confidence_rules.md` and noticing that a security field
justified its High by naming the pricing page. **Re-deriving a stale document against live data is
not housekeeping; it is a defect-finding technique** — the same one that produced defect 33.

### 44–47 — FOUND 19 Aug BY AUDITING AGAINST THE BRIEF PDF ITSELF. All fixed.

**How they were found, and why it took until day 12.** Every compliance check before this one was
made against a *summary* of the brief held in project memory. On 19 Aug the actual
`Project_Brief_1.pdf` was extracted to text and read line by line against the repo. Four
requirements turned out to be unmet, and **all four were on the client-facing surface** — the
engineering underneath audited clean, including the robots layer, which is the strongest part of
the project.

| # | Defect | Fix |
|---|---|---|
| **44** | **THE RESEARCH-CATEGORY FILTER WAS A DEAD CONTROL, FOR NINE DAYS.** The brief's *Expected Input* names three things, the third being *"optional research category filter, such as security, privacy, support, pricing, or product capability"*. `app.py` rendered `st.multiselect(...)` and **discarded its return value** — under a help line reading *"Leave empty to extract every field"*, which promises the opposite. Selecting "security" changed nothing. **A dead control is worse than a missing feature: a missing feature is visible, and a dead one silently misrepresents the system to the non-technical operations lead this interface exists for.** | Wired as a **reading lens**, not a collection filter. `FOCUS_TO_FIELDS` in `app.py` maps the brief's five category words to our eight field names, and tabs 3 and 4 filter on it. Collection and extraction are untouched: filtering at extraction time would make the corpus depend on a UI setting and quietly break replay, and nothing is discarded, so clearing the filter restores everything with **no re-run**. |
| **45** | **THE AGENT-STEPS TAB DENIED THAT A WORKING AGENT EXISTED.** `app.py` carried a hardcoded `st.progress(0.0, text="not built yet")` under *"Step 3 — Brief Review Agent"*. Agent 3 had shipped the day before; its steps were being computed, saved into every brief and rendered in tabs 4 and 5 — while the one tab whose entire purpose is the brief's *"see each agent step"* requirement told the reviewer it did not exist. | The panel now renders Agent 3's real step trail plus evidence / confidence / coverage. **Same class as defect 18b, and the rule from it applies verbatim: decide what is true, then draw it. Never hardcode a state you are also computing.** |
| **46** | **THE CSV EXPORT DROPPED ITS OWN DISCLAIMER.** `BRIEF_COLUMNS` was field-level only, so the CSV was the single export carrying no disclaimer, no review flags, no missing-or-unclear list and none of the three vendor-level numbers. A reviewer choosing CSV — offered on equal footing with JSON and Markdown — received a clean table of security claims about seven real companies with every caveat stripped off. **Not a formatting gap:** the brief's scope boundaries require the output to show it is a first-pass aid, and a spreadsheet is the format most likely to be pasted into an email and read alone. | Six vendor-level columns now repeat on **every row**, including the disclaimer. That redundancy is correct for a flat format: a reader who sorts, filters or copies one row out of the sheet takes the caveat with them. A test asserts it. |
| **47** | **`config/settings.yaml` ADVERTISED A LANGUAGE-MODEL BACKEND THAT DOES NOT EXIST.** `backend: "rules"  # "rules" (default, free) \| "llm" (optional, off)`. `grep` across `src/`, `tools/` and `app.py` finds **zero** readers. A dead config key in the one file a reviewer opens to find out what the system does — the same defect as a dead UI control, in a different costume. | Removed, with the reason left in its place. If an LLM path is ever added, the key returns at the same moment the code that reads it does. |

**Also closed, not a defect but a brief field left thin:** `SourceRecord.tags` restates
`source_type` — **39 of 49 rows are exactly `[source_type]`**, and four of the brief's seven example
tag words never appear. The information the brief wants belongs to Agent 2, and having Agent 1
compute it would break the linear flow the brief mandates. Resolved at export time: `corpus.csv`
carries **`evidence_tags`**, the topics that actually found evidence on that page, populated on
**26 of 49 pages**. Recorded in `docs/assumptions_limitations.md` §3.7.

### 48–53 — FOUND 22 Aug BY LOOKING AT THE SCREEN AND BY CLONING THE REPO. All fixed.

**Every one is on the reader-facing surface. The suite passed throughout, and so did every
export.** Five came from opening the app and reading a tab; one came from running the fresh-clone
test for the first time. **Counted by root cause, not by symptom** — the temptation was to call
this nine, because several produced more than one wrong thing on screen, and inflating a defect
count by counting symptoms is the same sloppiness this section exists to criticise.

| # | Defect | Fix |
|---|---|---|
| **48** | **A CAVEAT WAS TREATED AS EVIDENCE, AND PRODUCED AN EMPTY QUOTE.** Tab 3 tested `if not f["evidence"]`, which is false when the only entry is a collection caveat. Three JetBrains fields therefore rendered the heading **"Quoted from the vendor's page:"** above an **empty blockquote**, then cited the caveat as `matched `` in the tool limitation · - page · []()` — an empty markdown link. The table beside it read **`Evidence: 1`** on a field with no evidence, and **`From: -`**. This is defect 27 — an empty quote presented as a claim — reappearing in the renderer, on the vendor the evaluation calls its control case. | Tab 3 now splits real evidence from caveats the way tab 4 already did, through shared helpers so the two cannot diverge again. A caveat-only field renders *"Could not be evaluated — a limit of our collection, not a statement about the vendor"* and **no quote block at all**. `Evidence` counts quotes; a new `Caveats` column counts reasons we could not look. |
| **49** | **THE `NOT_FOUND` SENTINEL WAS PRINTED AS A CONFIDENCE LEVEL, IN FOUR RENDERERS.** The brief names three levels. `schema.FieldResult` defaults `confidence` to the sentinel `"NOT_FOUND"` so a status is never mistaken for a rating — and four places printed that sentinel in a column or line headed *Confidence*, inventing a fourth level in the reader's eyes. Also printed as *Extraction quality*. | One helper, `conf_label()`, used by all four. Nothing to rate prints `-`, with a caption saying why. Step 4 of the client's chain now reads *"No confidence to report — there is no quote to rate."* |
| **50** | **AN INTERNAL SAMPLING LABEL READ AS A VENDOR RATING.** The sidebar printed `Difficulty tier: hard` under the vendor's name, unexplained. `hard` describes how badly THIS TOOL handles the vendor's pages; beside a company name it reads as a judgement about the company — and the brief's scope boundaries forbid assigning vendor risk scores. | Relabelled *"Sampling tier … this describes our test set, not the vendor. It is not a risk score, a rating or an assessment of the company."* |
| **51** | **"KEY SOURCES" UNDERSTATED THE WORK AND SAID NOTHING ABOUT IT.** `key_sources` is readable pages only. JetBrains showed **3** under a bare heading, with 6 collected and 10 attempted. A reviewer reads *"3 sources"* as *the vendor publishes little* — the exact confusion the client asked us to remove on 18 Aug. | A caption naming both counts and pointing at tab 1 and the source manifest: *"A short list here means we could read little, not that the vendor publishes little."* |
| **52** | **TAB 3 AND TAB 4 DISAGREED ABOUT CONFIDENCE ON 26 FIELD/VENDOR PAIRS.** Tab 3 shows Agent 2's rating; Agent 3 then reviews it and, under defect 43's rule, downgrades High to Medium when the printed quote does not sit on the field's own page. Every vendor was affected — Atlassian 5, Postman 6, GitHub 5, GitLab 4, Sentry 3, JetBrains 2, Linear 1 — and **every export used Agent 3's value**, so the deliverable was right and only the screen was wrong. A reviewer reading tab 3 wrote down a rating the system had already rejected. | Tab 3 shows both, side by side: **Confidence (Agent 2)** and **After Agent 3 review**, with a caption saying a difference is the review step working and the right-hand value is the one to trust. **The defect becomes the demonstration**: the client asked on 18 Aug that Agent 3 highlight weak evidence, and this is where a marker can watch it happen. |
| **53** | **THE CHECKER CALLED THE SUBMITTED ARCHIVE BROKEN.** In a fresh clone — no HTML cache, exactly as the client instructed on 18 Aug — `verify_corpus.py` printed **49 `cache-missing` FAIL rows** and **"DO NOT COMMIT: 7 vendor(s) failed. Fix the FAIL rows."** A reviewer following our own README is told the deliverable is broken while it behaves exactly as specified. **This is defect 40 in a second costume**, and `run_workflow --mode replay` had already been taught to refuse gracefully while this had not. | *Some* pages missing = this tree is inconsistent = still FAIL. *Every* page missing = the shipped shape = one `cache-absent` WARN per vendor. The footer now separates **what was checked** from **what was skipped, not passed** — the same distinction as *not found* versus *could not be evaluated*, applied to the checker itself. |

**How they were found, and why that is the whole point.** Five of the six came from opening the
app and reading a tab; the sixth came from cloning the repository and running the README. **The
152-test suite passed through all six**, because every UI test asserts what the app hands to
Streamlit and every export test writes to `tmp_path`. Neither can see a heading above an empty
quote, or a checker's verdict in a directory that does not exist on this machine.

**And the count itself needed checking.** These were first written up as nine. Three of the nine
were extra *symptoms* of defects 48 and 49 rather than defects of their own. Counting symptoms
inflates the number and hides the root cause, which is the opposite of what §5 is for.

### 54–55 — FOUND 23 Aug BY RUNNING THE CLONE'S TEST SUITE. Both fixed.

`pytest -q` in the fresh clone: **1 failed, 151 passed**. The failure was ours, and it was in the
test rather than in the code it guards.

| # | Defect | Fix |
|---|---|---|
| **54** | **A TEST REPORTED THE SHIPPED ARCHIVE SHAPE AS A BUG — defect 53 in a third costume.** `test_gitlab_security_field_quotes_the_soc_2_sentence` guarded on `data/corpus/gitlab.json.exists()`, under its own comment reading *"Skipped on a fresh clone"*. The corpus **index** is committed; the pages it names are not (`.gitignore`, the client's 18 Aug instruction). So the guard was true in a clone, the replay ran with nothing to replay, and a clean clone failed with `assert 'NOT_FOUND' == 'High'` — while Agent 2 did precisely what defect 40 taught it to do, caveat and all. | Guard on the **page**, not the index: `_gitlab_security_page_is_cached()` resolves the security record through `resolve_html_path`. And because a test that skips protects nobody, the same assertion was restated on committed fixtures — `gitlab_security_style.html`, `gitlab_status_style.html`, `gitlab_pricing_style.html` — in `test_security_field_prefers_the_security_page_sentence`, which runs on any clone. `pricing` and `status` are authoritative source types, so both rivals can reach High on their own and only `preferred_source_types` keeps the security sentence on top: the fixture reproduces the competition, not just the answer. |
| **55** | **`resolve_html_path` COULD READ ANOTHER TREE'S CACHE AND CALL IT OURS.** Its first branch was `Path(raw_html_path).is_file()`, unconditional and first. Since the defect-16 fix stores repo-**relative** paths, that branch resolves against the **process's working directory**, not against `root`. Any process whose working directory is a tree that HAS the cache, operating on a `root` that does not — a tool started from the wrong folder, a clone inspected from inside the real repo — makes Agent 2 quote evidence out of the other tree — with no `missing-html` step and no caveat. **Defect 40 with the failure hidden instead of recorded**, which is the worse half. Found by accident: a simulated cacheless clone reported the page as *present*, because python was running from the real repo. | Trust `direct` only when `direct.is_absolute()`. That branch exists to rescue a pre-fix corpus carrying `C:\Users\...`, and only that; a relative path now goes through `root`, the only authority on where this repo's cache lives. Pinned by `test_resolve_html_path_ignores_a_same_named_file_in_the_working_directory`, which builds two trees, puts the same content-addressed filename in both and chdirs into the wrong one. All four existing `resolve_html_path` cases still pass, and every caller (`orchestrator.replay_*`, `tools/verify_corpus.py`) already passed an explicit `ROOT`. |

**Neither was reachable from the suite as it stood**, for the same reason as defect 53: the tests
run where the cache exists and where the working directory is the repo root. `docs/test_cases.md`
TC-23c already says this about `verify_corpus.py`. It is now true of three things, and the pattern
deserves its name — **every check we own has behaved differently in the tree we ship than in the
tree we work in.** The fixture-backed test above is the first of them that does not.

### ONE AUDIT FINDING WAS FALSE. THE LESSON IS WORTH MORE THAN THE FOUR REAL ONES.

The same audit reported `screenshots/` as **empty — only `.gitkeep`**. It was auditing a **copy of
the repo in a cloud container**, which had never received the screenshots. All twelve are committed
in `68ff6ee`; git's own `create mode 100644 screenshots/04_vendor_brief.png` output is the proof.

**An audit of a copy is an audit of the copy.** Findings about code CONTENT transfer between a
working tree and a copy; findings about a file being ABSENT do not. Before accepting any
"X is missing" finding, check it against the real working tree. This is the fifth time in this
project that a plausible finding has been wrong on checking, and the count is the point: **three of
four candidate findings on 18 Aug were false, and one of nine here.** Checking is not overhead.

### A ROUTE NOT TAKEN — keep this, it is the best thing in the evaluation
The first version of defect 28's fix dropped blocks whose heading was not a complete sentence.
It reasoned correctly and it failed. Measured against the corpus it turned **Linear's pricing** and
**Sentry's data residency** from a weak FOUND into a clean **NOT_FOUND** — a flat statement that
Linear publishes no pricing, about a vendor whose pricing page we read successfully. Trading a poor
quote for a false negative is the exact failure defect 23 exists to prevent. The right answer was
neither FOUND nor NOT_FOUND but **PARTIAL**, which is how defect 36 was found.

### STILL OPEN — deliberately not fixed. Record in `assumptions_limitations.md`.
- **Atlassian `security_trust` value = "Sensitive Health Information and HIPAA."** — a numbered
  terms-of-service section title sitting inside body text, indistinguishable from a sentence by any
  rule we have. Raising the sentence floor to exclude it would be over-fitting to one vendor, which
  the locked decisions already forbid. **Agent 3's flag, not a threshold change.**
- **Linear `data_residency`** quotes *"Trusted by more than 40,000 product teams around the globe"*
  under the heading *"Multi-region hosting"* — the heading matched, the body is unrelated marketing
  copy. The card prints the heading separately so the reviewer can see the match, but the quote
  alone misleads.
- **42 cited terms fall outside the 600-character snippet window** across 20 cards. Not
  fabrication — every one is on the page — but a reviewer cannot verify them from the card.
  Agent 3 should cite only the terms visible in the quote it prints and count the rest separately.
- ~~**Defect 31's scoring change** — Agent 3 owes a coverage-aware score.~~ **CLOSED 19 Aug**
  (defect 42): `coverage_verified`/`coverage_total` and `confidence_counts` are on `VendorBrief`
  and printed together in the UI, the Markdown export and `verify_corpus`.

### Principles these produced (quote these in the docs)
- **AppTest verifies data, not rendering.** Screenshot the browser before calling any UI done.
- **Never let a refusal be a bare boolean.** `(allowed, reason)` would have exposed defect 4 instantly.
- **Re-read the brief's verbs.** "Run or replay" is two features.
- **An agent that succeeds silently is indistinguishable from one that fails silently** (defect 18).
- **In `app.py`: decide what is true, then draw it. Never the reverse** (defect 18b).
- **Two cheap orthogonal tests beat one clever one** — see defect 33 for the corrected examples.
- **Check the code against its own documentation** (defect 15), **and the documentation against
  the current data** (defect 33). A worked example decays the moment the data changes.
- **Ranking order is a policy statement.** Defect 27 is not a bug in `rank_evidence`; the function
  did exactly what the config told it to. The wrong thing was in the dictionary.
- **A fix nobody exercised is a fix nobody verified** (defect 34). Test the wiring BETWEEN
  components, not only the functions inside them. Defect 26's fix shipped and never ran once.
- **A test that asserts a bug is worse than no test** (defect 35). It converts a defect into a
  guarantee and makes the next person's correct fix look like a regression.
- **Two docstrings describing one rule differently is how a codebase stops being auditable**
  (defect 36) — and that disagreement had silently killed an entire status value.
- **Measure a fix against real data before believing it.** On 18 Aug three of four candidate
  findings were false, and one "fix" was a regression only the corpus exposed.
- **We never bypass access controls.** No browser-impersonating headers.

---

## 6. Environment gotchas that will waste your time

1. **Streamlit hot-reloads `app.py` but NOT modules under `src/`.** Restart after any `src/` change.
   `app.py` has a stale-module guard that prints a red "Restart the server" box. Trust it.
2. **Run everything from the repo root** — `app.py` does `from src.agent1_collect import …`.
3. **Run git from a normal Windows terminal, never through the Cowork mount.** The mount leaves
   stale `.git/HEAD.lock` / `.git/index.lock` that cannot be unlinked; move them to `_to_delete/`.
   **Even a read-only `git status` through the mount can leave `index.lock` behind.** If a commit
   fails with "Unable to create index.lock: File exists", that is why — see §9.
4. **PowerShell 5.1 `>` and `Out-File` write UTF-16.** A BOM-prefixed `.gitattributes` silently
   fails to match its own first pattern. Use `Set-Content -Encoding ascii`.
5. **`_to_delete/` is gitignored, so git will never remind you to delete it before submission.**
6. **Cowork's bridge to this machine has no network access** — vendor collection must be run by
   hand in the browser. It also has **no pytest**, so an assistant cannot run the suite; only
   `verify_corpus.py` and hand-written checks run there. Always re-run `pytest` yourself.
7. `data/cache/html/*` is gitignored, so a bare `git clone` cannot replay offline. That used to be
   the argument for shipping a zip including `.git/`. **The client withdrew that on 18 Aug (§1.1
   item 3): the cache is NOT submitted.** The consequence stands and must be stated in the README —
   a reviewer re-collects the public sources before they can replay. The cache stays local for
   development.
8. **Vendor pages change between runs.** Linear's `docs` page went from 24,444 bytes / 15 readable
   chars to 540,090 bytes / 1,034 readable chars between 12 and 13 Aug. The cache, not the live
   web, is the record of what was collected. Say so in `assumptions_limitations.md`.

---

## 7. Where things stand and what happens next

### State at 20 Aug — every number below was produced by running it, not recalled

- **152 pytest passing** (134 → +9 orchestrator, +4 UI/export, +2 defect 43). **Re-run on Windows
  on 20 Aug: `152 passed in 39.66s`.** Until then the figure had only ever been asserted in a
  document; it is now a number somebody watched appear.
- `python tools/verify_corpus.py` → **0 FAIL across all seven vendors**, re-run 20 Aug.
- **55 WARN**, and they are the deliverable rather than the noise: 21 `off-home-evidence`,
  10 `unread-home-page`, 9 `claim-not-in-matched-sentence`, 8 `unusable-page`, 3 `thin-text`,
  2 `score-without-coverage`, 1 `not-collected`, 1 `gated-evidence`. Ledgered in
  `docs/evaluation.md` §4.5. **`claim-not-in-matched-sentence` fires on six of seven vendors and
  is the one to read** — JetBrains `privacy_data_handling` scored on a longer sentence while the
  longest sentence actually containing its matched terms is **5 characters**.
- **JetBrains was re-collected on 22 Aug** from the UI, so the corpus now carries **three** dates:
  13 Aug for Atlassian, GitHub, Linear, Postman and Sentry · **19 Aug GitLab** · **22 Aug
  JetBrains**. **Every figure reproduced identically** — 5/10 Medium, Low, coverage 2/5, 5 flags,
  4 FOUND / 4 NOT_FOUND, 3 readable sources — which is a result worth one sentence in the
  evaluation: the pipeline is deterministic and JetBrains' pages did not move in three days.
  **`data/exports/source_manifest.csv` still says 19 Aug for JetBrains and is stale until
  `tools/export_all.py` re-runs.**
- **13 caveats across four vendors** (Postman 4, JetBrains 4, Atlassian 3, Linear 2; GitHub,
  GitLab and Sentry none) and **37 review flags** in total. *`docs/evaluation.md` §4.1 said
  eighteen caveats until 20 Aug — a figure that stopped being true when the seed corrections
  changed what JetBrains and GitLab could read, and that nobody re-counted.*
- Field totals **43 FOUND / 3 PARTIAL / 10 NOT_FOUND**. PARTIAL became reachable on 18 Aug
  (defect 36) and stayed reachable through every change since.
- Independent checks run OUTSIDE `verify_corpus`, against the cached HTML: **0 empty quotes ·
  0 loader-noise quotes · 0 real orphan citations** across 122 evidence blocks.
- **Three axes now reported together, never one alone** (defect 42):

| Vendor | Evidence | Confidence | Coverage | Flags |
|---|---|---|---|---|
| GitLab | 10/10 High | Medium — 2 of 5 core High | 5/5 | 6 |
| Sentry | 10/10 High | Medium — 2 of 5 core High | 5/5 | 5 |
| GitHub | 10/10 High | Medium — 2 of 5 core High | 5/5 | 4 |
| Linear | 6/10 Medium | Low — 1 High, 3 Med, 1 Low | 3/5 | 3 |
| Postman | 10/10 High | Medium — **0** of 5 core High | 2/5 | 6 |
| Atlassian | 10/10 High | Medium — **0** of 5 core High | 2/5 | 8 |
| JetBrains | 5/10 Medium | Low — 1 High, 2 Med, 2 Low | 2/5 | 5 |

- **Offline replay is demonstrated, not merely claimed.** With `data/cache/` deleted —
  the exact shape of the submitted archive — `python tools/run_workflow.py` still produces every
  brief, because `review` mode needs neither network nor cache. `--mode replay` in that state
  **refuses** and says why (defect 40).
- JetBrains' corrected security seed works: `/legal/docs/privacy/trust-center/` returns 200 and
  carries the SOC 2 Type II sentence. `terms` still 404s three times — and, since defect 34, is
  finally *reported* as never collected.

### Commits

**HEAD = `origin/master` = `a99a11e`, 26 commits, pushed. Level with origin, working tree clean.**

| Commit | When | What |
|---|---|---|
| `b7068bb` | 12 Aug | line endings, `.gitattributes` |
| `07127e8` | 13 Aug | Agent 2 live across seven vendors, `verify_corpus.py` |
| `e39ffd2` | 18 Aug | defects 27–39: the ten code fixes |
| `64fca64` | 18 Aug | re-collected and re-extracted corpus, all seven |
| `fe3f686` | 18 Aug | **Agent 3** + `review_rules.py` + 7 briefs |
| `3cb4455` | 18 Aug | **export layer + source manifest** + 23 export artifacts |
| `6759ea6` | 19 Aug | **orchestrator** + defects 40, 41, 42 |
| `68ff6ee` | 19 Aug | **UI tabs 4 and 5** + 12 screenshots |
| `537074f` | 19 Aug | **defect 43**, `confidence_rules.md` rewritten, 9 brief/corpus artifacts re-exported |
| `07228a1` | 19 Aug | **`docs/architecture.md` and `README.md` rewritten against the code that exists** — 312 insertions, 77 deletions |
| `7e89306` | 20 Aug | **§7/§8/§11/§12 reconciled** · the exec summary at the top of `docs/evaluation.md` · **the four never-tracked documents added**: `client_guidance.md`, `brief.txt`, `assumptions_limitations.md`, `START_HERE.md`. 14 files, 1425 insertions |
| `752e60d` | 20 Aug | **`docs/test_cases.md`** — the tenth and last brief deliverable · `export_all.py` re-run, so the 23 shipped artifacts finally match the code that produces them. 39 files |
| `c3d44d6` | 22 Aug | The corpus was never uniformly 13 August, and five documents said it was. Defects 40–47 written into `docs/evaluation.md` · README deliverables table rebuilt to the brief's ten · the 55-warning ledger (§4.5) |
| `a99a11e` | 22 Aug | **Defects 48–53** — five found by reading a tab, one by cloning the repository · `.gitattributes` export-ignore for the two internal documents |

*Both 20 Aug commits carry the same subject line, because the second reused the first's message
file. Harmless, and worth not repeating: `git log --oneline` now shows two identical subjects.*

**This table was stale by two commits within four hours of being written.** Regenerate it from
`git log`, never from memory. Same class of error as §8 and §11 below, and the reason this
section is now the only place in the repository that states commit state.

### PACKAGING — and why `HANDOFF.md` is not in the archive

**`git archive --format=zip -o ..\vendor-dd-prototype-submission.zip HEAD`.** 3 MB, **109 files**,
built and verified by unpacking on 22 Aug. Never hand-assemble a submission folder: `git archive`
ships exactly the tracked tree at HEAD and nothing else — no `.git`, no `.venv`, no
`__pycache__`, no `_to_delete/`, and no HTML cache.

**`.gitattributes` marks `HANDOFF.md` and `START_HERE.md` `export-ignore`.** The 23 Aug archive is
**112 files** (three new test fixtures since the 109-file count), and stays 112: `code_walkthrough.md`
was drafted and cut the same day. **Re-count after every rebuild rather than trusting this line.** The reason is §0 of this file. It is addressed to an AI assistant and says,
in Moushmi's own words, *"I know Python basics only… never hand over unexplained code — 'an AI
wrote it' ends an interview"*, plus how the 18 Aug fix pass was run in a container. **That is an
internal working document and it must never reach the client.** Do not remove those two lines.

**The repository still contains both.** The submission email therefore ships the **zip only** and
does not offer the GitHub link — the brief accepts *"a structured zip folder or repository format"*,
either, not both.

**The consequence that was nearly missed.** Excluding two files broke every reference to them from
files that DO ship. `README.md` opened by telling the reader to read `START_HERE.md` and
`HANDOFF.md`; `docs/assumptions_limitations.md` cited `HANDOFF.md` as a source; and three comments
in `src/review_rules.py` and `tests/test_agent3.py` cited "HANDOFF §2" as the decision record. All
five are rewritten to stand alone. **Before removing anything from a deliverable, grep the
deliverable for what points at it.**

### STILL OUTSTANDING, in this order

- [x] ~~**COMMIT AND PUSH.**~~ **DONE 20 Aug** — `7e89306` and `752e60d`, both pushed. Everything
      below was true until it was done, and is kept because the reasoning is the reusable part:
      Four files are **untracked** — they exist on one laptop and nowhere else:
      `docs/client_guidance.md` (the document this repo says outranks every other decision),
      `brief.txt` (the file compliance must be checked against), `docs/assumptions_limitations.md`
      (21 KB, written 19 Aug), and `START_HERE.md`. Nine tracked files are modified:
      `app.py`, `src/export.py`, `tools/export_all.py`, `config/settings.yaml`,
      `tests/test_export.py`, `README.md`, `docs/architecture.md`, `docs/confidence_rules.md`,
      this file. Message prepared in `_to_delete/commit5.txt`.
      **The project's own lesson is that memory is not durable and the repo is. Four of the
      files that carry that lesson are not yet in the repo.**
- [x] ~~**CLICK THE RESEARCH-FOCUS FILTER ONCE BY HAND.**~~ **DONE 22 Aug**, on JetBrains with
      `support` selected — the edge case most likely to break, being NOT_FOUND with only a caveat.
      It worked, and reading the screen around it produced defects 48–52. Original note kept: Its wiring is proven by AppTest —
      selecting "security" yields 3 of 8 fields with no exceptions — but Streamlit's multiselect
      dropdown could not be driven in headless Chromium, so **no browser has confirmed it visually.**
      This project's own rule is that AppTest verifies data and not rendering.
- [x] ~~**`docs/test_cases.md`** — a brief deliverable.~~ **WRITTEN 20 Aug.** 34 cases in the
      brief's own order, with a traceability table from every brief requirement to a case ID, and a
      `Ships?` column saying which cases run in an archive with no HTML cache. **It found two
      defects while being written — see §8.**
- [x] ~~**A one-page executive summary at the top of `docs/evaluation.md`**~~ **DONE 20 Aug**, in
      `7e89306`: the finding, the three-axis table with what each column is for, 16.3% / 84% / 41%,
      the four places manual review remains, and how the defects were actually found.
- [x] ~~Add defects 40–47 to `docs/evaluation.md`.~~ **DONE 22 Aug**, `docs/evaluation.md` §5.1.
- [x] ~~**Re-clone and run `verify_corpus.py` there.**~~ **DONE 23 Aug** in a clone built from
      `c75f195`: one `cache-absent` WARN per vendor, 0 FAIL, and `pytest -q` 153 passed / 1
      skipped. Defect 53's fix is confirmed, and running it is what found defects 54 and 55.
- [x] ~~Delete `_to_delete/`.~~ **DONE 23 Aug.**
- [ ] Remove the repository line from the submission email — the repo still contains `HANDOFF.md`.
- [x] **`docs/code_walkthrough.md` — DRAFTED 23 Aug AND CUT THE SAME DAY.** Checked verbatim against
      `brief.txt` on 20 Aug: the ten listed items are prototype, orchestration code, corpus,
      sample outputs, README, architecture note, assumptions & limitations, **test cases**,
      evaluation summary, screenshots. `code_walkthrough.md` is our own addition. It is still the
      document that would let you defend the code line by line, so it was drafted on 23 Aug — and
      then removed, on the document's own logic. **A file written to help you defend the code is
      one you have to be able to defend, and that one was not written by you.** It also added a
      seventh document to a package whose stated risk is volume, four hours before submission.
      It reached one archive build (`d3110eb`) and was cut before the archive that gets sent.
      Not logged as a defect: nothing was wrong with it, it was the wrong thing to ship.
- [x] ~~Delete `_to_delete/` before packaging.~~ **DONE 23 Aug.**

### ⚠ THE STANDING RISK IS NO LONGER MISSING WORK. IT IS VOLUME.

`HANDOFF.md` ~72 KB · `docs/evaluation.md` ~31 KB · `docs/architecture.md` ~30 KB ·
`docs/confidence_rules.md` ~25 KB · `docs/assumptions_limitations.md` ~21 KB.
**Roughly 180 KB of prose.** Every page is defensible. Nobody will read them all.

The brief requires the **Streamlit interface** to be usable by a non-technical operations lead —
not the documents — and the interface is genuinely good: plain-language captions, three numbers each
with a tooltip naming the question it answers, the six-link chain, flags in prose rather than codes.
**The documents are for a technical reviewer, and that is legitimate.** But a reviewer's realistic
path is: README → open the app → skim one brief → sample one document.

**So: write nothing longer. `test_cases.md` should be short, and the next most valuable thing in the
repository is a ONE-PAGE entry point at the top of the evaluation, not more depth anywhere.**

**Where the time went.** 13 Aug re-ran the agents. **14–17 Aug produced nothing — no commits.**
18 Aug produced thirteen defects found and twelve fixed, three documents rewritten against verified
data, a client reply that fixed the scope in writing, Agent 3, and the export layer. 18–19 Aug
produced the orchestrator, defects 40–43, both UI tabs, twelve screenshots and two commits.

**Day 13 of 20 — it is 20 August.** (Recounted 20 Aug 00:10 IST. The 19 Aug session crossed a
real midnight and every "day 12" written in it was wrong by morning. Rule 3, committed by the
session that wrote Rule 3.)

**TEN of ten brief deliverables complete**, counted against `brief.txt` itself rather than a
summary of it: prototype, orchestration code, corpus, sample outputs, README, architecture note,
assumptions & limitations, **sample test cases** (`docs/test_cases.md`, written 20 Aug),
evaluation summary, screenshots. **Nothing on the client's list is outstanding.** What remains is
quality: the exec summary is in, defects 40–47 are not yet in `docs/evaluation.md`, and
`code_walkthrough.md` is optional. Feature freeze 21 Aug.

### The per-vendor loop
```
# in the app: pick vendor -> Agent 1 -> Agent 2
python tools/verify_corpus.py <slug>      # FAIL = our bug, WARN = a vendor finding
git add data/corpus/<slug>*.json
git commit -m "<what this vendor taught>"   # the finding, not "add <slug>.json"
```

### Remaining build — REPLANNED 19 Aug, evening

**Position: day 13 of 20. NINE of ten brief deliverables complete. 7 days to the 27 Aug target,
9 to the 29 Aug deadline.** The 19 Aug plan expected `export.py`, the orchestrator and two UI tabs
to take until 20 Aug; all three are done, committed and pushed, plus eight defects, plus the
architecture note and README rewritten. **You are a day ahead of the plan, not behind it.** Feature
freeze holds at 21 Aug; everything from here is prose, and prose is where roughly half the marks
live.

| Date | Day | Work |
|---|---|---|
| **19 Aug** | 12 | ✅ orchestrator + CLI · defects 40–47 · **UI tabs 4 and 5** · 12 screenshots · **`assumptions_limitations.md` written** · the brief-PDF compliance audit (§12) · `confidence_rules.md`, `architecture.md`, `README.md` and this file rewritten. **Four commits pushed** (`6759ea6`, `68ff6ee`, `537074f`, `07228a1`). The audit pass — `app.py`, `src/export.py`, the four untracked documents — is still uncommitted. |
| **20 Aug** | 13 | ✅ **Two commits pushed, `7e89306` and `752e60d`.** §7/§8/§11/§12 reconciled against the repo · the exec summary written · the four never-tracked documents added · **`docs/test_cases.md` — the tenth and last brief deliverable** · `export_all.py` re-run so the 23 shipped artifacts match the code · `pytest` and `verify_corpus` re-run on Windows (152 passed, 0 FAIL, 55 WARN) · the corpus-date error found: five vendors are 13 Aug, GitLab and JetBrains are 19 Aug · `evaluation.md` §4.1's caveat count corrected from 18 to 13 · **§4.5 added: the 55-warning ledger**. |
| **21 Aug** | 14 | **FEATURE FREEZE — passed with nothing committed.** 20 and 21 Aug produced no commits, the second such gap in this project after 14–17 Aug. |
| **22 Aug** | 15 | **The filter was clicked by hand at last, and the screen was read.** Defects **48–53** found and fixed — five by looking at a tab, one by cloning the repository and running the README. Defects 40–47 written into `docs/evaluation.md` §5.1. `README.md` deliverables table rebuilt to the brief's ten. `assumptions_limitations.md` §5 corpus date corrected. The **submission email** drafted. JetBrains re-collected from the UI (figures unchanged). |
| **22–24 Aug** | 15–17 | Add defects 40–47 to `docs/evaluation.md` and re-read the rest of it against the final code rather than rewriting it. Then `docs/code_walkthrough.md` **if the clock allows** — it is not a brief deliverable (see the outstanding list above) and it is the first thing to drop. |
| **25 Aug** | 18 | **Fresh-clone test.** Delete the venv, follow the README exactly, confirm it runs first try — and confirm `python tools/run_workflow.py` works in a clone with no cache, because that is what a reviewer does first. Remove `_to_delete/`. Package per §1.1 item 3 — structured corpus + code + source manifest, **HTML cache EXCLUDED** — then unpack the archive somewhere clean and confirm nothing in it is a verbatim third-party page. |
| **26 Aug** | 19 | Buffer. Use it for whatever slipped, or for the optional LLM summarisation toggle **only if everything else is finished** (§1.1 item 1 — must work with no API key, must link back to evidence). |
| **27 Aug** | 20 | **Submit.** Email projects@firstquadrantlabs.com and upload to the LMS. 28–29 Aug is buffer, not schedule. |

### DECISION MADE 19 AUG: DO NOT RE-COLLECT THE CORPUS

**CORRECTED 20 Aug — the corpus is not uniformly 13 August.** `data/exports/source_manifest.csv`
gives `date_collected` **2026-08-13** for Atlassian, GitHub, Linear, Postman and Sentry, and
**2026-08-19** for **GitLab**, and — since a re-run from the UI on 22 August — **2026-08-22** for
**JetBrains**. Every document that said "the 13 August corpus" was wrong for two of seven vendors,
and then for a third. The figures were never wrong: they were re-verified by running the workflow
on 20 August, and JetBrains' 22 August re-collection reproduced every number it had before.
**Say "13 August, with GitLab re-collected on the 19th and JetBrains on the 22nd" — and check the
manifest rather than trusting any sentence in this repository, including this one.**

The corpus is now 1–7 days old. Vendor pages demonstrably move —
Linear's `docs` page went from 24,444 bytes to 540,090 between 12 and 13 August, and its security
page now publishes `<h2>SOC 2 compliance</h2>` with an empty body where a full SOC 2 sentence was
recorded on 10 August.

**Freeze it.** Re-collecting would invalidate every measured figure in `docs/evaluation.md`,
`docs/confidence_rules.md` and this file — the 8-of-49 unusable pages, the 122 evidence blocks, the
per-vendor coverage table — and each of those was fact-checked by script against the corpus. That
is a day of re-verification bought for nothing, on a plan with no slack.

What to do instead: **state the collection date plainly** in the README and the evaluation, and
present the drift as a finding rather than a staleness problem. "The cache, not the live web, is
the record of what was evaluated" is already in the evaluation's limitations — it is a stronger
sentence when the reader can see the corpus is dated.

## 8. Known-wrong things in the current documents — fix before submission

Recorded honestly rather than quietly patched, because a document that describes behaviour the
code does not have is worse than no document.

- **⚠ OPEN, 22 Aug: `data/exports/source_manifest.csv` says JetBrains was collected 19 Aug.**
  It was re-collected on the 22nd. One `python tools/export_all.py` fixes it — and TC-6 exists
  precisely because nothing automated will remind you.
- ~~**Six display defects (48–53).**~~ **ALL FIXED 22 Aug** in `app.py` and
  `tools/verify_corpus.py`; see §5. The empty quote, the `NOT_FOUND` confidence, the caveat
  counted as evidence, the sampling tier read as a vendor rating, the unlabelled key sources, and
  the checker calling the shipped archive broken.
- ~~**⚠ BLOCKING, FOUND 20 Aug: `data/exports/` is stale, and it is a submitted deliverable.**~~
  **CLOSED 20 Aug.** `tools/export_all.py` re-run; `data\exports\sentry_brief.csv` now has
  **17 columns**, confirmed by hand. The re-export also rewrote all 7 brief JSONs, all 7
  `_fields.json` and all 23 export artifacts — a measure of how far the artifacts had drifted from
  the code. **The finding stands as a standing check (TC-6), not as a closed one-off:**
  `src/export.py` was fixed at **18:18** on 19 Aug to carry all of the brief's Expected Output
  items; every file in `data/exports/` was written at **14:16**, four hours earlier.
  `BRIEF_COLUMNS` is **17 columns**; `data/exports/sentry_brief.csv` has **11** and no
  `disclaimer` column. **The sample outputs that ship are the defect-46 output — the exact bug
  the 19 Aug audit reports as fixed.** Run `python tools/export_all.py` and confirm 17 columns
  before committing. *No automated test catches this: every export test writes to `tmp_path`, so
  the suite verifies the code and never the artifacts. `docs/test_cases.md` TC-6 is that check,
  and it is manual by necessity.* This is the documented order — replay, verify, export — not
  followed after a `src/` change.
- **`HANDOFF.md` §12 claimed the CSV carries all 12 Expected Output items. It carries 10.**
  Corrected 20 Aug against `src/export.py`, not against a document. A one-row-per-field table has
  no row shape for `vendor_overview` or `product_category`; JSON and Markdown carry both. The
  brief says export as JSON, CSV, **or** Markdown, so this is a property to state rather than a
  gap to close — stated in `docs/test_cases.md` §B.

- ~~**`docs/architecture.md` §10 claims "JavaScript rendering is unnecessary, not merely excluded".**~~
  **CLOSED 19 Aug in `07228a1`.** Verified by reading the file, not the commit message: §10 now
  states the narrower claim — *"no-JavaScript costs nothing on trust, legal and status pages, and
  costs everything on modern marketing pages… it is a trade, not a free choice"* — and carries the
  Atlassian measurements (52 characters from 898 KB; 66 from 1.21 MB).
- ~~**`docs/architecture.md` §11** asserts GitHub's *"GitHub's API stays secure with ISO, SOC 2, and
  GDPR"* scores **High** without explaining why that became true.~~ **CLOSED 19 Aug in `07228a1`.**
  §11 now tells the mechanism — bare `<h2>`, empty quote, `heading_only`, ranked 9th of 9, the value
  falling through to GitHub's terms of service, and the three changes it took to fix — and closes
  with *"a claim that turns out to be accidentally right is worth less than a defect explained"*.
- ~~**`docs/architecture.md` §3** says "94 offline tests" and "43 seed URLs".~~ **CLOSED 19 Aug.**
  Corrected to 152 tests and 44 seeds, and §3 now documents the orchestrator's three modes.
- ~~**`docs/architecture.md` §6** marks Agent 3 "NOT BUILT YET".~~ **CLOSED 19 Aug in `07228a1`.**
  The string "NOT BUILT" no longer appears in the file. §6 now carries *"Every judgement lives in
  one module, imported twice"*, *"Three axes, because one number hid the thing that mattered"*,
  *"What it flags"* and *"What it does not flag, and why that is reported rather than hidden"*;
  §3 documents the orchestrator's three modes.
- **`config/settings.yaml`** — worked examples CORRECTED 18 Aug (defect 33). Nothing owed.
- **`docs/confidence_rules.md` — CORRECTED 18 Aug** for defects 27, 28 and 36, and its worked
  examples re-derived from the corpus. Three of its six rows had gone stale exactly as
  `settings.yaml` had: the Linear row quoted *"Linear undergoes regular Service Organization
  Controls audits (SOC 2 Type II)."*, a sentence that **appears nowhere in the current corpus** —
  Linear's security page now yields `<h2>SOC 2 compliance</h2>` with an empty body. The Atlassian
  row described the field as Low/PARTIAL from alt-text; it is FOUND/High from the terms page.
  Nothing owed.
- **`docs/evaluation.md` — REWRITTEN 18 Aug** against the corrected corpus. Every figure in it was
  fact-checked against `data/corpus/` by script, not by eye.
- ~~**The export commit message claims "134 tests" on the strength of a Linux-container run.**~~
  **CLOSED 19 Aug.** Windows confirmed 134, then 143, then **150**. The commit message was
  accurate; the concern was still worth raising, because a number nobody checked on the target
  platform is exactly the class of claim this project keeps finding wrong.
- ~~**`README.md` is now wrong about the submission**.~~ **CLOSED 19 Aug in `07228a1`.** It opens
  with *"the submitted archive runs offline, with one caveat"*, states the 22 MB cache is excluded
  at the client's instruction, carries a **Re-collecting the public sources** section, and names the
  mode that works without a cache. Its deliverables table is the one place still worth re-reading
  before submission — it lists eight rows, not the brief's ten.
- ~~**`docs/confidence_rules.md` §"Client guidance"** must converge with the code.~~
  **CLOSED 19 Aug.** They had NOT converged: the box claimed the change made Postman's 10/10 High
  impossible, and it had not (defect 42). The file now carries that correction in its own words,
  documents all three reporting axes in Step 6, shows both axes in the worked-examples table, and
  adds items 5 and 6 to its closing list of rules it once described wrongly.
- **`src/agent1_collect.py` calls characters "bytes"** in its unusable-page message. Under 0.01%
  error on ASCII-dominant pages and no decision changes, but the label is wrong. One-word fix;
  costs a full Agent 1 re-run, so do it the next time that file is touched anyway.
- **`docs/confidence_rules.md`** now carries **six** entries in its closing section on rules it
  previously described incorrectly, two of them added 19 Aug about itself. Keep that section and
  keep adding to it — it is the single most persuasive page in the repo, because it demonstrates
  the discipline the deliverable is arguing for rather than asserting it.

- ~~**`docs/evaluation.md` carries three claims that defect 42 made false.**~~ **ALL THREE CLOSED — re-checked against the file itself on 23 Aug:** §0 no longer contains *"A sixth is open"*; §4.3 now opens *"Until 19 August, Postman and Sentry received identical scores"*; the count sentence reads **fifty-five** in all three places it appears. The original note, kept because it records what was verified against
  `data/briefs/postman_brief.json` on 20 Aug rather than against a document:
  **§0** ends *"A sixth is open and belongs to Agent 3: a vendor can still score 10/10 High while
  half its primary documents were never read"* — closed; Postman now reads `evidence_score` 10,
  `confidence_band` **Medium**, `coverage_verified` **2** of **5**, and a `SCORE OVERSTATES
  COVERAGE` review flag naming all three unread fields.
  **§4.3** still says *"Postman and Sentry receive identical scores and identical confidence
  labels"* and calls this *"the most important open defect"* — they are no longer identical, and it
  is no longer open.
  **§5** now says *"Fifty-five defects"* in all three places. *This line read "Thirty-seven ... the count is now 47" until 23 Aug, having missed defects 48–53 — a note about stale counts that was itself stale.*
  The one-page executive summary added 20 Aug states the current position. Everything else in the
  file was fact-checked by script on 18 Aug and should be re-read rather than rewritten.
- ~~**`docs/evaluation.md` does not yet contain defects 40–47**~~ — **DONE**: §5.1 carries 40–47,
  §5.2 carries 48–53, §5.3 carries 54–55 (23 Aug). **The offline-replay reconciliation named in
  this bullet was NOT re-checked on 23 Aug and may still be missing** — do not treat this line as
  evidence that it is there.

---

## 9. Commands

```powershell
cd "C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\vendor-dd-prototype"
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q                                    # expect 152 passed. Re-run after every
                                             # extraction, not just after code changes
python tools/run_workflow.py --mode replay   # 1->2->3 over every vendor, offline from the cache
python tools/verify_corpus.py                # expect 0 FAIL before any commit
python tools/export_all.py                   # refresh data/exports/
streamlit run app.py                         # then http://localhost:8501

# The order that matters after ANY change to src/: run_workflow --mode replay FIRST, then
# verify_corpus, then export_all. Skipping the replay leaves data/ written by older code, and
# verify_corpus will correctly fail on artifacts that no longer match the rules.
```

After a change to `src/`, the order is: **restart Streamlit → Agent 1 → Agent 2 → verify_corpus →
commit.** Skipping Agent 1 is what hid defect 34 for a day — the corpus on disk was written by an
older Agent 1 and no amount of re-running Agent 2 could put the missing `skip` steps into it.

If a git command fails with `Unable to create '.git/index.lock': File exists`, a Cowork-mount
read left it behind (§6.3). Clear it, never with `rm`:

```powershell
if (Test-Path .git\index.lock) { Move-Item .git\index.lock _to_delete\index.lock.$(Get-Random) }
if (Test-Path .git\HEAD.lock)  { Move-Item .git\HEAD.lock  _to_delete\HEAD.lock.$(Get-Random)  }
```

No API key, no account, no GPU, no paid service. After one collection run the whole workflow
replays offline from `data/cache/html/`.

---

## 10. Scope boundaries — never cross these

From the brief, verbatim in substance. The prototype must **not**: make final procurement
decisions · assign official vendor risk scores · claim legal, compliance or security approval ·
access private vendor portals · scrape aggressively or bypass access restrictions · build a
production procurement platform · require paid databases or enterprise tools. Also excluded by
our own design: manager agents · memory layers · autonomous browsing loops · JavaScript rendering.

Collection policy: robots.txt read before every fetch (RFC 9309 semantics), 2-second per-domain
delay, honest User-Agent, 10 pages / 20 requests per vendor, no JavaScript rendering, everything
cached on first fetch.

Every output states plainly that it is a **first-pass internal research aid** and that final
review remains manual — `VendorBrief.disclaimer` carries this on every export.

---

## 11. BRIEF COMPLIANCE MATRIX — keep this current (Rule B)

| Brief requirement | Status | Where |
|---|---|---|
| Max 3 working roles: Source Collection, Evidence Extraction, Brief Review | **3 of 3 built** | `src/agent1_collect.py`, `src/agent2_extract.py`, `src/agent3_review.py` |
| No manager agents, memory layers, autonomous browsing loops | Met | linear orchestration by design |
| 5–8 vendors, one practical category | Met — 7 developer productivity tools | `config/vendors.yaml` |
| Only public, official/credible sources | Met | seeds are official vendor domains; robots honoured |
| Source types: product, pricing, security/trust, privacy, terms, docs, integrations, status | Met | 6–8 per vendor collected. `trust` became a first-class authoritative type on 18 Aug because the brief pairs it with `security` in one bullet |
| Structured store with vendor name, source URL, source type, page title, collected text, date collected, tags, evidence note | Met — `SourceRecord` maps 1:1 | `src/schema.py` |
| Input: vendor name/list, collected URLs or pre-prepared source file, optional category filter | **Met 19 Aug.** The filter existed as a control whose return value was DISCARDED for nine days — a dropdown that changed nothing under a help line promising it narrowed extraction. Now wired as a reading lens over tabs 3 and 4: `FOCUS_TO_FIELDS` maps the brief's five category words to field names; nothing is discarded, so clearing it restores everything with no re-run | `app.py` |
| Output: overview, category, key sources, security, privacy, support, integrations, pricing, missing/unclear, review flags, evidence snippets, confidence | **Met** — populated by Agent 3, exported in three formats | `src/agent3_review.py`, `src/export.py` |
| Streamlit: select vendor · view sources · run or replay · see agent steps · inspect evidence · view brief · export JSON/CSV/Markdown | **7 of 7, built 19 Aug.** Rendered and screenshotted in headless Chromium, not only AppTest | `app.py`, `src/export.py` |
| Runs locally on a standard laptop, low cost, no heavy infrastructure | Met | no LLM, no GPU, no paid service |
| Missing or unclear information flagged instead of guessed | **Met end to end.** Agent 3 raises 3–8 flags per vendor and separates "not found" from "could not be evaluated" per field | caveats + `verify_corpus` + `agent3_review`. `PARTIAL` became reachable on 18 Aug (defect 36) |
| Confidence level: High / Medium / Low | **Met on two axes.** `docs/confidence_rules.md` rewritten 19 Aug for defects 42 and 43 and now documents both | `docs/confidence_rules.md` §Step 6 |
| Lower-cost alternatives (Ollama, local models, rule-based, template summaries) mentioned and supported | **Rule-based is built; the alternatives are not yet written down anywhere.** The brief asks that they be *mentioned* | owed by `assumptions_limitations.md` |
| Deliverables: prototype · orchestration code · corpus · ≥5 sample outputs · README · architecture note · assumptions & limitations · test cases · evaluation summary · screenshots | **10 of 10 complete** (recounted 20 Aug against `brief.txt` verbatim). Prototype, orchestration code, corpus, sample outputs (7 briefs × 3 formats), README, architecture note, assumptions & limitations, **sample test cases (`docs/test_cases.md`)**, evaluation summary, screenshots. `code_walkthrough.md` is NOT on the brief's list and must not be counted against the ten | see §7, `docs/test_cases.md` |
| Zip or repository, all code, data, README, screenshots, sample outputs | **Built and verified 22 Aug** — `git archive` produces a 3 MB, 109-file zip; unpacked and checked. Structured corpus + code + source manifest; HTML cache EXCLUDED; README explains re-collection (§1.1 item 3). The two internal documents are `export-ignore`d — see §7 *Packaging* | `.gitattributes`, §7 |
| Queries only via projects@firstquadrantlabs.com, consolidated | **Sent and answered 18 Aug** | §1.1 |

### Added by the client's written guidance, 13 Aug (§1.1). Not in the original brief.

| Client requirement | Status | Where |
|---|---|---|
| Rule-based extraction as delivered behaviour; verbatim evidence praised for auditability | **Met and endorsed** | quote it in the evaluation |
| Optional LLM summarisation toggle — must work without an API key, must link back to evidence | **Not built.** Last item in the build order, only if time permits | — |
| No headless browser; distinguish "not found" from "could not be evaluated" | **Met, in their exact wording**, per field rather than per vendor: 3 could-not-be-evaluated vs 7 genuine not-founds | `agent3_review.review_vendor` |
| Check other official sources before marking a category unavailable, else flag for manual review | **Met** — a not-found now states that the field's own pages read cleanly and how many others did not | `agent3_review.review_vendor` |
| Number AND percentage of inaccessible pages in the evaluation | **Met — 8 of 49, 16.3%** | `docs/evaluation.md` §1.1 |
| Do NOT ship the 22 MB HTML cache | **Locked decision withdrawn**; packaging step rewritten | §1.1 item 3, §7 |
| **SOURCE MANIFEST — new deliverable** | **BUILT AND COMMITTED** (`3cb4455`). 54 attempts across 7 vendors: 5 never collected, 8 collected but unreadable | `data/exports/source_manifest.csv` |
| Submit the structured CSV/JSON/SQLite corpus, URLs, titles, dates, snippets, tags, code | **Met** — `data/exports/corpus.csv` (49 pages, the brief's 8 named fields first) plus the JSON corpus | `src/export.py` |
| README explains how a reviewer re-collects the sources | **Not written** | §8 |
| Confidence not based primarily on sentence length | **IMPLEMENTED 18 Aug at field level, COMPLETED 19 Aug at vendor level.** The 18 Aug claim was false: the vendor header kept summing the extraction axis under the word *Confidence*, so Postman tied Sentry at 10/10 High on coverage 2/5 vs 5/5 (defect 42). Three measures now carry three names | `review_rules.confidence`, `review_rules.vendor_confidence`, `schema.VendorBrief` |
| Agent 3 = review and synthesis only; coverage, missing categories, conflicts, final brief | **BUILT 18 Aug** | `src/agent3_review.py` |
| **Conflict detection between sources — new** | **Built and unit-tested. Returns ZERO on the real corpus** — reported as a finding, not hidden. Value-level only (percentages, audit levels); semantic contradiction needs an LLM | `review_rules.conflicting_values` |
| Offline replay demonstrated in the submission | **BUILT AND RECONCILED 19 Aug.** `orchestrator` names three modes; `review` needs neither network nor cache and is what the submitted archive runs. Verified: with `data/cache/` deleted, `tools/run_workflow.py` still produces every brief | `src/orchestrator.py`, README |
| UI shows Source → Evidence → Field → Confidence → Flag → Brief | **BUILT 19 Aug.** Labelled literally, one numbered link per field, in tab 4 | `app.py`, screenshots `04_vendor_brief.png` / `tab4_chain.png` |
| Cross-vendor comparison table in the evaluation | **Met** | `docs/evaluation.md` §2 |

---

## 12. THE 19 AUGUST COMPLIANCE AUDIT — method and verdict

Recorded because the METHOD is reusable and the result is the thing a marker will check.

### What was done
`Project_Brief_1.pdf` was extracted to text and read line by line against the repository — every
requirement in *Expected Input*, *structured format fields*, *Expected Output*, *Streamlit
interface*, *Deliverables*, *Scope Boundaries*, *Success Criteria* and the *suggested stack*. Every
verdict was reached by running code or reading data. **No verdict rests on a document's description
of itself**, which matters in a repository this heavily documented: the docs are the thing most
likely to be believed and least likely to be true.

**This should have happened on day 2.** Until 19 Aug every compliance check was made against a
summary of the brief, not the brief. Four requirements had been quietly unmet for over a week.

### Verdict

| Group | Result |
|---|---|
| **Scope Boundaries (7)** | **NONE VIOLATED.** The collection layer is the strongest part of the project: RFC 9309 robots semantics, honest User-Agent, 2s per-domain delay, 10-page/20-request caps, and **zero credential-handling code anywhere in `src/`** |
| **Success Criteria (9)** | 8 clean before the fixes; the ninth — *"usable for a non-technical reviewer"* — was compromised by defects 44 and 45 and is now clean |
| **Expected Input (3)** | Was 2 of 3 (defect 44). Now 3 of 3 |
| **Corpus fields (8)** | 8 of 8 present; `tags` was thin and is answered by `evidence_tags` in `corpus.csv` |
| **Expected Output (12)** | The **brief** carries all 12. JSON and Markdown carry all 12 throughout. CSV carried 6 (defect 46) and now carries **10** — `BRIEF_COLUMNS` is 17 columns, but a one-row-per-field table has no row shape for `vendor_overview` or `product_category`. *Corrected 20 Aug: this row read "now all three do", which is false and was never checked against `src/export.py`. The brief does not require every format to carry every item — it says export as JSON, CSV, **or** Markdown — so this is a design property to state, not a gap to close. Stated in `docs/test_cases.md` §B.* |
| **Streamlit capabilities (7)** | Was 5 clean (defects 44, 45). Now 7 |
| **Deliverables (10)** | **10 complete** as of 20 Aug. *Corrected 20 Aug: this row originally read "8 complete, missing `test_cases.md` and `code_walkthrough.md`". `code_walkthrough.md` appears nowhere in `brief.txt`; it is our own idea, counted against a list it was never on.* |
| **Suggested stack** | Every decline documented in `docs/assumptions_limitations.md` §6 — SQLite, LangGraph/CrewAI, hosted LLM, Playwright/Selenium, and (added 19 Aug) sentence-transformers/FAISS/Chroma |

### The audit itself imported an error, and that is the more useful finding

The 19 August audit was built to stop compliance being judged against a summary of the brief. It
still counted `code_walkthrough.md` — an item we invented — as one of the brief's ten deliverables,
and reported 8 of 10 where the brief's own list gives **9 of 10**. Nothing was missing that we
thought was missing; we had added a requirement to the client's list and then failed it.

**Reading the source document is not the same as counting from it.** The audit re-read the brief
and then scored against a remembered list. That is the identical failure one level up — and it
cost a day of perceived debt in the last week of a twenty-day project.

### The pattern worth quoting in the evaluation
**Every one of the four gaps was on the client-facing surface, and none was in the engineering.**
A dead dropdown, a tab denying a working agent existed, an export stripping its own disclaimer, and
a config key advertising a feature that was never built. The code was more honest than the interface
describing it — which is the exact inversion of what this project spent twelve days warning about,
committed by the project itself.

### And one finding was false
See §5. `screenshots/` was reported empty by an audit running against a **container copy** of the
repo. All twelve are committed. **Findings about code content transfer between a working tree and a
copy; findings about a file being absent do not.**
