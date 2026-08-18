# HANDOFF — Vendor Due-Diligence Research Workflow Prototype

**Purpose:** everything a fresh chat session needs to pick this project up cold.
Read it top to bottom before touching anything.
**Last updated: 13 August 2026, day 6 — defect 27–37 pass, and the client's written guidance.**

> ### ⚠ READ §1.1 BEFORE ANY DESIGN DECISION
> First Quadrant Labs replied to the clarification email in writing on 13 August. **That reply
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
machine has no `pytest` and no network. The fix pass of 13 Aug was therefore run by copying the
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

- **Deadline: Saturday 29 August 2026.** 16 days left as of this update.
- The brief describes a **20-day cycle**. Day 1 = 8 Aug 2026, so **day N = 7 Aug + N**.
  Today, 13 Aug, is **day 6**. Day 20 = 27 Aug, two days before the deadline.
- Submit to **projects@firstquadrantlabs.com** AND upload to the LMS.
- All queries go through that one project email, consolidated into one message where possible.
- Brief PDF: `C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\Project_Brief_1.pdf`
- Repo: `...\Research Project_1\vendor-dd-prototype` · remote:
  `https://github.com/moushmirao30/vendor-dd-prototype.git` (**private**, branch `master`)

---

## 1.1 CLIENT GUIDANCE — received in writing 13 August 2026. AUTHORITATIVE.

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

**Recommendation: implement it, additively, alongside Agent 3 — not as an Agent 2 redesign.** Keep
`evidence_level` intact and rename it; add a second function for confidence. Roughly 40 lines.
Declining is defensible only in writing, and reads badly: a consulting client gave explicit written
guidance and the deliverable ignored it.

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
| Agent 2 confidence | measured on the **longest sentence**, not the whole block | a bullet list is a label, not a claim (defect 15). **QUESTIONED BY THE CLIENT 13 Aug — §1.1 item 4. Keep this logic but rename it EXTRACTION QUALITY, and add a second confidence axis on their definition** | "Confidence level: High / Medium / Low" |
| Agent 2 ranking | sorts by **confidence level first** | the quote printed under a label must be the evidence that earned it | "outputs are structured and easy to review" |
| `preferred_source_types` | **orders** evidence, never filters it | GitLab really does state FedRAMP on its pricing page | — |
| Generic-term noise | **Agent 3 raises a flag**, dictionary left alone | avoids over-fitting the dictionary to one vendor | "review flags for manual follow-up" |
| ~~Submission format~~ | ~~zip including `.git/`, excluding `.venv/`~~ **WITHDRAWN 13 Aug — see §1.1 item 3.** Ship the structured corpus, the code, and a NEW **source manifest**; keep the 22 MB HTML cache local; README explains re-collection | the client asked us not to redistribute verbatim third-party pages | "a structured zip folder or repository format" |
| Repo visibility | **private** | the corpus stores ~70,000 chars of verbatim vendor text per vendor | — |
| Code delivery | written into the repo with full explanation + `docs/code_walkthrough.md` | I must be able to defend every line | "the agent structure is simple, controlled, and understandable" |

---

## 3. What exists right now

**13 commits (`b7068bb`). 101 pytest passing (was 97; +4 written with defects 34–36).
7 vendors, 49 pages, 55 cached files. `verify_corpus.py`: 0 FAIL across all seven.**
**Everything from 12–13 Aug is UNCOMMITTED, including the defect 27–36 fixes and the defect 37 report — see §7.**

```
vendor-dd-prototype/
├─ app.py                     Streamlit UI — Agents 1 and 2 live, Agent 3 stubbed
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
│   └─ schema.py              SourceRecord · ExtractedField · VendorBrief
├─ tools/
│   └─ verify_corpus.py       CORPUS HEALTH CHECKER — run before every commit
├─ data/corpus/               7 vendors × {json, _run.json, _fields.json}
├─ data/cache/html/           55 × v2_*.html — offline replay (gitignored)
├─ docs/
│   ├─ confidence_rules.md    the written confidence rule + worked examples
│   ├─ architecture.md        DRAFT — see §8
│   └─ evaluation.md          DRAFT — written 13 Aug from the corpus
└─ tests/                     101 tests, all offline
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
| **A confident quote that says nothing** *(found and FIXED 13 Aug)* | GitHub | `security_trust` = *"…the content of your Account and its security are up to you."* — the **terms of service**, one matched term | The AICPA SOC 1/SOC 2 Type 2 statement, matching four terms, ranked **second** and never became the value. Now fixed: see defects 27, 28, 30 |

**A 200 means the URL exists, not that it is the right page, and not that it contains words.
A 404 means our URL guess was wrong, not that the vendor is silent.
And a quote that passes every check can still be the wrong sentence.**

The machinery that enforces the first three:
- `SourceRecord.block_count` and `content_usable` (Agent 1 measures readability at collection)
- `unusable-page`, `unread-home-page`, `home-page-never-found`, `skip` audit steps
- caveat entries injected into a field's **evidence list**, because a reviewer reads the brief, not the trail
- `tools/verify_corpus.py`, which FAILs on an uncaveated confident answer

What now guards the fourth (all added 13 Aug):
- `preferred_source_types` no longer treats a terms-of-service page as a home for security claims
- ranking and scoring both ask "is this a complete sentence?" rather than "which HTML tag was it in"
- the field's headline is the sentence carrying the MOST matched terms, not the first one found
- interface furniture is stripped out of quotes before they are shown or measured
- `verify_corpus` prints coverage beside every score and WARNs when a High rests on unread pages

**The fifth mechanism has no guard yet and is Agent 3's job: a vendor can still score 10/10 High
while half its primary documents were never read. See defect 31.**

---

## 5. Thirty-seven defects, and the headline they add up to

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

### 27–37 — FOUND 13 Aug 2026. All verified against the real corpus; 36 fixed, 37 recorded.

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
- **Defect 31's scoring change** — Agent 3 owes a coverage-aware score.

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
- **Measure a fix against real data before believing it.** On 13 Aug three of four candidate
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
   the argument for shipping a zip including `.git/`. **The client withdrew that on 13 Aug (§1.1
   item 3): the cache is NOT submitted.** The consequence stands and must be stated in the README —
   a reviewer re-collects the public sources before they can replay. The cache stays local for
   development.
8. **Vendor pages change between runs.** Linear's `docs` page went from 24,444 bytes / 15 readable
   chars to 540,090 bytes / 1,034 readable chars between 12 and 13 Aug. The cache, not the live
   web, is the record of what was collected. Say so in `assumptions_limitations.md`.

---

## 7. Where things stand and what happens next

### State at 13 Aug, after the fix pass — every number below was produced by running it
- **101 pytest passing** (97 before; +2 for defect 34's wiring, +1 for 35, +1 for 28).
- `python tools/verify_corpus.py` → **0 FAIL across all seven vendors.**
- Field totals moved **46 FOUND / 10 NOT_FOUND / 0 PARTIAL → 43 / 10 / 3**. PARTIAL is reachable
  for the first time (defect 36).
- Independent checks run OUTSIDE `verify_corpus`, against the cached HTML: **0 empty quotes ·
  0 loader-noise quotes · 0 real orphan citations** across 122 evidence blocks and 18 caveats.
- Coverage now printed beside every score: GitHub, GitLab, Sentry **5/5**; Linear **3/5**;
  Atlassian, JetBrains, Postman **2/5**.
- JetBrains' corrected security seed works: `/legal/docs/privacy/trust-center/` returns 200 and
  carries the SOC 2 Type II sentence, which is now the field's value. `terms` still 404s three
  times — and, since defect 34, is finally *reported* as never collected.

### IMMEDIATELY OUTSTANDING — verified against the repo, evening of 13 Aug

**Done today, confirmed by inspection, not by memory:**
- ✅ Commit `07127e8` landed — the 12 Aug work plus the first round of docs. **It does NOT contain
      the defect 27–37 code fixes**; those are still in the working tree.
- ✅ Agent 1 AND Agent 2 re-run for all seven vendors (`ran_on` 21:28–21:34 IST), using the fixed
      code. **Defect 34 verified in production: `jetbrains_run.json` now carries `skip: terms`** —
      the step that had never once been emitted since the day it was written.
- ✅ Clarification email sent and answered. See §1.1.

**Still outstanding, in this order:**
- [ ] **Confirm `pytest -q` = 101 passed on Windows.** Not yet verified there; the fix pass ran in
      a Linux container.
- [ ] **Commit the CODE — 12 files — BEFORE the corpus.** The corpus on disk was generated by code
      that is not yet committed. Committing the corpus first would produce a repo where the
      evidence cannot be reproduced from the code beside it.
      `HANDOFF.md · config/field_dictionary.yaml · config/settings.yaml · docs/confidence_rules.md ·
      docs/evaluation.md · src/agent1_collect.py · src/agent2_extract.py · src/parse.py ·
      tests/test_agent1.py · tests/test_agent2.py · tests/test_parse.py · tools/verify_corpus.py`
- [ ] **Then commit the corpus** — 6 untracked vendors + gitlab. `verify_corpus` must show 0 FAIL
      first.
- [ ] Delete `_to_delete/`.
- [ ] Correct `docs/architecture.md` §3, §6, §10, §11 (§8 lists what is wrong in each).
- [ ] Rewrite the `README.md` submission section — the client withdrew the cache-in-zip plan
      (§1.1 item 3) and the README still describes it.

**A note on how today went, for the next session.** Day 6 produced no new capability: no Agent 3,
no orchestrator, no export. What it produced was eleven defects found and ten fixed, three
documents rewritten against verified data, and a client reply that fixed the scope in writing.
That was the right trade on day 6 and it is the wrong trade on day 8. **From 14 Aug the measure is
shipped capability, not documents.**

### The per-vendor loop
```
# in the app: pick vendor -> Agent 1 -> Agent 2
python tools/verify_corpus.py <slug>      # FAIL = our bug, WARN = a vendor finding
git add data/corpus/<slug>*.json
git commit -m "<what this vendor taught>"   # the finding, not "add <slug>.json"
```

### Remaining build — dated, not day-numbered

| Dates | Work |
|---|---|
| **13 Aug** (day 6) | ✅ Defects 27–37. ✅ Clarification email sent AND answered — §1.1. Docs rewritten. Still to do today: pytest on Windows, re-run Agent 1+2 for all seven, commit code then corpus. |
| **14–16 Aug** | **Agent 3.** Extract the shared predicates out of `tools/verify_corpus.py` into `src/`, then build `src/agent3_review.py` on top of them — **`verify_corpus.py` is already a working prototype of Agent 3** (`vendor-score`, coverage, `field-status`, `off-home-evidence`, `unread-home-page`, `unusable-page`, `thin-density`, `claim-not-in-matched-sentence`). Import them; do not reimplement, or the tool and the product drift and that is defect 15 again. **The client fixed Agent 3's scope in writing (§1.1 item 5): verify evidence coverage, identify missing categories, highlight conflicts or weak evidence, prepare the final brief — and nothing else.** Required flags from real data: (a) evidence only from outside `preferred_source_types` — on GitLab three of five core fields draw their strongest evidence from the *privacy policy*; (b) gated evidence — Sentry's SOC 2 reports are "available to customers … upon request"; (c) coverage vs score (defect 31); (d) **conflicts between sources — NEW, client-requested, not built today**; (e) cite only terms visible in the printed quote. Populate `VendorBrief.vendor_overview` and `.product_category` (category from `vendors.yaml`, overview quoted from the product page). **Do the two-axis confidence change here (§1.1 item 4) — additive, ~40 lines, and it closes defect 31.** |
| **17–18 Aug** | `src/export.py` (JSON/CSV/Markdown) **plus the SOURCE MANIFEST export — new client-required deliverable, §1.1 item 3**; `src/orchestrator.py` (1→2→3). Wire the Vendor brief and Export tabs. **The UI must show the chain end to end: Source → Extracted Evidence → Structured Field → Confidence → Review Flag → Final Brief (§1.1 item 5).** |
| **19 Aug** | **FEATURE FREEZE.** Anything unfinished becomes a limitations entry — that scores better than a half-working feature. |
| **14 Aug onward, in parallel** | `docs/evaluation.md`. It is already ~90% writable from the corpus and the defect log and does **not** depend on Agent 3. Writing it early hedges the worst case. |
| **20–25 Aug** | `assumptions_limitations.md`, `test_cases.md`, `code_walkthrough.md`. Correct `architecture.md` (§8). Screenshots. |
| **26 Aug** | Fresh-clone test: delete the venv, follow the README exactly, confirm it runs first try. Remove `_to_delete/`. **Package per §1.1 item 3 — structured corpus + code + source manifest, HTML cache EXCLUDED, README explaining re-collection.** Verify by unpacking the archive somewhere clean and checking that nothing in it is a verbatim third-party page. |
| **27 Aug** (day 20) | **Submit.** Email + LMS. Never submit on the deadline day; 28–29 Aug is buffer, not schedule. |

---

## 8. Known-wrong things in the current documents — fix before submission

Recorded honestly rather than quietly patched, because a document that describes behaviour the
code does not have is worse than no document.

- **`docs/architecture.md` §10 claims "JavaScript rendering is unnecessary, not merely excluded".**
  **False.** True for Statuspage-hosted status pages; false for Atlassian's marketing pages,
  Postman's privacy policy and docs, JetBrains' pricing and docs, and Linear's docs. Rewrite as:
  *rendering is excluded by scope, and the cost of that exclusion is measured and reported.*
- **`docs/architecture.md` §6** documents Agent 3, which does not exist. Keep the "NOT BUILT YET"
  marker until it does.
- **`docs/architecture.md` §11** asserts GitHub's *"GitHub's API stays secure with ISO, SOC 2, and
  GDPR"* scores **High**. It was false when written and is true now, for a reason worth telling:
  the sentence is a bare `<h2>` with no paragraph under it, so it scored `heading_only` → Medium,
  ranked 9th of 9 and never reached the brief at all — until defect 28 made scoring and ranking
  ask "is this a sentence?" instead of "which tag was it in". **Rewrite the paragraph around what
  actually happened.** A claim that was accidentally right is worth less than a defect explained.
- **`docs/architecture.md` §3** says "94 offline tests" and "43 seed URLs". It is now **101 tests**;
  recount the seeds.
- **`config/settings.yaml`** — worked examples CORRECTED 13 Aug (defect 33). Nothing owed.
- **`docs/confidence_rules.md` — CORRECTED 13 Aug** for defects 27, 28 and 36, and its worked
  examples re-derived from the corpus. Three of its six rows had gone stale exactly as
  `settings.yaml` had: the Linear row quoted *"Linear undergoes regular Service Organization
  Controls audits (SOC 2 Type II)."*, a sentence that **appears nowhere in the current corpus** —
  Linear's security page now yields `<h2>SOC 2 compliance</h2>` with an empty body. The Atlassian
  row described the field as Low/PARTIAL from alt-text; it is FOUND/High from the terms page.
  Nothing owed.
- **`docs/evaluation.md` — REWRITTEN 13 Aug** against the corrected corpus. Every figure in it was
  fact-checked against `data/corpus/` by script, not by eye.
- **`README.md` is now wrong about the submission** — it describes shipping the cache for offline
  replay. §1.1 item 3 withdrew that. It must instead explain **how a reviewer re-collects the
  public sources**, and state that a fresh clone cannot replay until they do.
- **`docs/confidence_rules.md` §"Client guidance"** records what the client asked for and what the
  code does today. Those must converge when the two-axis change lands, or the file becomes the
  third document in this project to describe behaviour the code does not have.
- **`src/agent1_collect.py` calls characters "bytes"** in its unusable-page message. Under 0.01%
  error on ASCII-dominant pages and no decision changes, but the label is wrong. One-word fix;
  costs a full Agent 1 re-run, so do it the next time that file is touched anyway.
- **`docs/confidence_rules.md`** is current as of 12 Aug and contains a closing section naming two
  rules it previously described incorrectly. Keep that section — it reads as rigour.

---

## 9. Commands

```powershell
cd "C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\vendor-dd-prototype"
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q                       # expect 101 passed. Re-run after every extraction, not just
                                # after code changes
python tools/verify_corpus.py   # expect 0 FAIL before any commit
streamlit run app.py            # then http://localhost:8501
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
| Max 3 working roles: Source Collection, Evidence Extraction, Brief Review | 2 of 3 built | `src/agent1_collect.py`, `src/agent2_extract.py`; **Agent 3 missing** |
| No manager agents, memory layers, autonomous browsing loops | Met | linear orchestration by design |
| 5–8 vendors, one practical category | Met — 7 developer productivity tools | `config/vendors.yaml` |
| Only public, official/credible sources | Met | seeds are official vendor domains; robots honoured |
| Source types: product, pricing, security/trust, privacy, terms, docs, integrations, status | Met | 6–8 per vendor collected. `trust` became a first-class authoritative type on 13 Aug because the brief pairs it with `security` in one bullet |
| Structured store with vendor name, source URL, source type, page title, collected text, date collected, tags, evidence note | Met — `SourceRecord` maps 1:1 | `src/schema.py` |
| Input: vendor name/list, collected URLs or pre-prepared source file, optional category filter | Partial — **optional research-category filter not implemented** | `app.py` |
| Output: overview, category, key sources, security, privacy, support, integrations, pricing, missing/unclear, review flags, evidence snippets, confidence | Schema complete, **unpopulated until Agent 3** | `VendorBrief` in `src/schema.py` |
| Streamlit: select vendor · view sources · run or replay · see agent steps · inspect evidence · view brief · export JSON/CSV/Markdown | 5 of 7 — **brief and export tabs are stubs** | `app.py` tabs 4 and 5 |
| Runs locally on a standard laptop, low cost, no heavy infrastructure | Met | no LLM, no GPU, no paid service |
| Missing or unclear information flagged instead of guessed | Met for collection, **pending for the brief** | caveats + `verify_corpus`; Agent 3 owes the flag list. `PARTIAL` became reachable on 13 Aug (defect 36), so "we saw a hint" is no longer reported as "the vendor said so" |
| Confidence level: High / Medium / Low | Met, rule corrected 13 Aug | `docs/confidence_rules.md` **still describes the pre-defect-36 rule** — update it |
| Lower-cost alternatives (Ollama, local models, rule-based, template summaries) mentioned and supported | **Rule-based is built; the alternatives are not yet written down anywhere.** The brief asks that they be *mentioned* | owed by `assumptions_limitations.md` |
| Deliverables: prototype · orchestration code · corpus · ≥5 sample outputs · README · architecture note · assumptions & limitations · test cases · evaluation summary · screenshots | 4 of 10 complete | see §7 |
| Zip or repository, all code, data, README, screenshots, sample outputs | Planned — **packaging rewritten by client instruction** | structured corpus + code + source manifest; HTML cache EXCLUDED; README explains re-collection (§1.1 item 3) |
| Queries only via projects@firstquadrantlabs.com, consolidated | **Sent and answered 13 Aug** | §1.1 |

### Added by the client's written guidance, 13 Aug (§1.1). Not in the original brief.

| Client requirement | Status | Where |
|---|---|---|
| Rule-based extraction as delivered behaviour; verbatim evidence praised for auditability | **Met and endorsed** | quote it in the evaluation |
| Optional LLM summarisation toggle — must work without an API key, must link back to evidence | **Not built.** Last item in the build order, only if time permits | — |
| No headless browser; distinguish "not found" from "could not be evaluated" | **Met** via caveats; **match their wording** in the brief | Agent 2 caveats |
| Check other official sources before marking a category unavailable, else flag for manual review | Behaviour exists (all pages searched); **not visible in the brief** | Agent 3 owes the wording |
| Number AND percentage of inaccessible pages in the evaluation | **Met — 8 of 49, 16.3%** | `docs/evaluation.md` §1.1 |
| Do NOT ship the 22 MB HTML cache | **Locked decision withdrawn**; packaging step rewritten | §1.1 item 3, §7 |
| **SOURCE MANIFEST — new deliverable** | **Not built.** Data exists in Agent 1's trail | `src/export.py`, 17–18 Aug |
| README explains how a reviewer re-collects the sources | **Not written** | §8 |
| Confidence not based primarily on sentence length | **Not implemented.** Two-axis model designed | §1.1 item 4, Agent 3 |
| Agent 3 = review and synthesis only; coverage, missing categories, conflicts, final brief | **Not built.** Scope now fixed in writing | 14–16 Aug |
| **Conflict detection between sources — new** | **Not built.** No contradiction detection today | Agent 3 |
| Offline replay demonstrated in the submission | **Not demonstrated.** Reconcile with the cache exclusion | screenshots + demo notes |
| UI shows Source → Evidence → Field → Confidence → Flag → Brief | **Partially** — tabs 4 and 5 are stubs | `app.py` |
| Cross-vendor comparison table in the evaluation | **Met** | `docs/evaluation.md` §2 |
