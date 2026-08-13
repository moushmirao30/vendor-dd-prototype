# HANDOFF — Vendor Due-Diligence Research Workflow Prototype

**Purpose:** everything a fresh chat session needs to pick this project up cold.
Read it top to bottom before touching anything. **Last updated: 13 August 2026, day 6.**

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
| Agent 2 confidence | measured on the **longest sentence**, not the whole block | a bullet list is a label, not a claim (defect 15) | "Confidence level: High / Medium / Low" |
| Agent 2 ranking | sorts by **confidence level first** | the quote printed under a label must be the evidence that earned it | "outputs are structured and easy to review" |
| `preferred_source_types` | **orders** evidence, never filters it | GitLab really does state FedRAMP on its pricing page | — |
| Generic-term noise | **Agent 3 raises a flag**, dictionary left alone | avoids over-fitting the dictionary to one vendor | "review flags for manual follow-up" |
| Submission format | **zip including `.git/`, excluding `.venv/`** | reviewer gets code + cache + history without cloning | "a structured zip folder or repository format" |
| Repo visibility | **private** | the corpus stores ~70,000 chars of verbatim vendor text per vendor | — |
| Code delivery | written into the repo with full explanation + `docs/code_walkthrough.md` | I must be able to defend every line | "the agent structure is simple, controlled, and understandable" |

---

## 3. What exists right now

**13 commits (`b7068bb`). 97 pytest passing as of 12 Aug — NOT re-run since the 13 Aug
re-extraction; re-run before committing. 7 vendors collected, 55 cached pages.**
**A large amount of work from 12–13 Aug is UNCOMMITTED — see §7.**

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
└─ tests/                     97 tests, all offline
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
| **A confident quote that says nothing** *(NEW, 13 Aug)* | GitHub | `security_trust` = *"…the content of your Account and its security are up to you."* — the **terms of service**, one matched term | The AICPA SOC 1/SOC 2 Type 2 statement, matching four terms, ranked **second** and never became the value |

**A 200 means the URL exists, not that it is the right page, and not that it contains words.
A 404 means our URL guess was wrong, not that the vendor is silent.
And a quote that passes every check can still be the wrong sentence.**

The machinery that enforces the first three:
- `SourceRecord.block_count` and `content_usable` (Agent 1 measures readability at collection)
- `unusable-page`, `unread-home-page`, `home-page-never-found` audit steps
- caveat entries injected into a field's **evidence list**, because a reviewer reads the brief, not the trail
- `tools/verify_corpus.py`, which FAILs on an uncaveated confident answer

**Nothing yet enforces the fourth. That is defect 27 and it is open.**

---

## 5. Thirty defects, and the headline they add up to

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

### OPEN — found 13 Aug, none fixed yet

| # | Defect | Evidence | Fix |
|---|---|---|---|
| **27** | **`terms` is a `preferred_source_type` for `security_trust`, so a liability disclaimer outranks a certification statement.** Ranking key position 3 (preferred source) is evaluated *before* position 5 (number of matched terms). | GitHub rank 1 = ToS, 1 term (`two-factor`), value *"…its security are up to you."* Rank 2 = *"GitHub offers AICPA System and Organization Controls (SOC) 1 Type 2 and SOC 2 Type 2 reports…"*, 4 terms. Reproduced by re-running `rank_evidence`. | Remove `terms` from `security_trust.preferred_source_types`. A ToS is where a vendor *disclaims* security, not where it *states* it. Then re-run Agent 2 for all seven. |
| **28** | **A claim published as a bare heading with no paragraph under it becomes evidence with an EMPTY snippet.** | GitHub `/security` carries `<h2>GitHub's API stays secure with ISO, SOC 2, and GDPR.</h2>` with `body=''`. It matched (`soc 2`), scored `heading_only` → Medium, ranked **9th of 9**, and was dropped by `max_evidence_per_field: 3`. The field's own #1 preferred source contributed nothing. | When `body` is empty and the heading is a full sentence, promote the heading text into the snippet. **This also corrects `docs/architecture.md` §11**, which claims this sentence scores High — it scores Medium and never reaches the brief. |
| **29** | **Loader error text is quoted to the reviewer as vendor evidence.** | *"There was an error while loading. Please reload this page ."* appears inside 4 of GitHub's evidence snippets, from the pricing page. | Add loader/placeholder phrases to a shared `noise_terms` list stripped from snippets — not to `negative_terms`, which would suppress the whole block including the real SOC 2 sentence. |
| **30** | **`best_sentence` returns the FIRST sentence containing ANY matched term, not the sentence carrying the strongest claim.** | JetBrains `security_trust` value = *"Please visit our Trust Center to learn more about JetBrains' security practices, compliance certifications, and data protection measures."* — matched on the weak navigational term `trust center`. The sentence *"You can also find details on our SOC 2 Type II and GDPR compliance…"* sits 340 characters later in the same snippet and is never the headline. | Score candidate sentences by how many terms they contain (and prefer specific terms over navigational ones); tie-break by position. |
| **31** | **The vendor score ignores caveats, so the least-verified vendor ties the best-verified one.** | Postman scores **10/10 → High** with 4 of 8 fields carrying `tool_limitation` caveats, its privacy policy at 0 readable chars and its docs at 2,370 chars from 1.2 MB. Sentry scores **10/10 → High** with 0 caveats and every page readable. Identical score. | Agent 3 must either discount caveated fields in the score or print a separate coverage figure beside it. This is the single most important thing Agent 3 does. |
| **32** | **`verify_corpus` prints `thin-density: "Passed the usability threshold"` for pages it has already declared unusable**, and rounds density to 1 dp so a page rejected at 1.96 ch/KB prints as "2.0 readable chars per KB" — a number that appears to contradict the decision. | Atlassian product/pricing, Postman docs. Postman docs: 2,370 chars ÷ 1,206 KB = **1.965**; threshold 2.0. | Skip `thin-density` for already-unusable pages; print 2 decimals and the threshold. |
| **33** | **Documentation defect — the worked examples for the two-test usability rule are falsified by the current corpus.** `config/settings.yaml` lines 33–37 and HANDOFF §5 claimed Postman's privacy page has "high density (27 ch/KB), caught only by the floor" and JetBrains' status page "clears any sane floor, caught only by density". Current data: Postman privacy = **0 chars, 0.0 ch/KB** (both tests) and JetBrains status = **333 chars, 1.5 ch/KB** (both tests). | Replace with the pages that actually demonstrate it: **floor-only = JetBrains `docs`, 45 chars at 10.4 ch/KB** (density is high; only the floor catches it). **Density-only = Postman `docs`, 2,370 chars at 1.96 ch/KB**, and Linear `docs`, 1,034 chars at 1.96 ch/KB (both clear the 600 floor comfortably). The rule is still right; the examples were stale. |

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
7. `data/cache/html/*` is gitignored. A bare `git clone` cannot replay offline. This is why the
   submission is a **zip including `.git/`**, not a repo link.
8. **Vendor pages change between runs.** Linear's `docs` page went from 24,444 bytes / 15 readable
   chars to 540,090 bytes / 1,034 readable chars between 12 and 13 Aug. The cache, not the live
   web, is the record of what was collected. Say so in `assumptions_limitations.md`.

---

## 7. Where things stand and what happens next

### State at 13 Aug, verified by re-running the checker
- `python tools/verify_corpus.py` → **0 FAIL across all seven vendors.** Linear's two
  `unread-home-page` FAILs are resolved; they are now WARNs with caveats attached.
- Re-extracted 13 Aug: **linear, postman, github, jetbrains**. Not re-extracted (already newer
  than the code): atlassian, gitlab, sentry.
- Independent check outside `verify_corpus`: **0 real orphan citations** across 122 evidence
  blocks. 20 cards show at least one cited term that falls outside the 600-char snippet window —
  a presentation issue, not a data-integrity one. Agent 3 should cite only visible terms.
- JetBrains' corrected security seed **works**: `/legal/docs/privacy/trust-center/` returns 200
  and carries the SOC 2 Type II sentence. `terms` still 404s three times and stays unresolved.

### IMMEDIATELY OUTSTANDING
- [ ] **Commit the CODE now, separately from the corpus.** 13 modified files and `tools/`,
      `docs/` are uncommitted. The corpus commit waits on defects 27–30.
- [ ] Re-run `pytest -q` on Windows. The 97-test figure predates the 13 Aug re-extraction.
- [ ] Fix defects **27, 28, 29, 30**, then re-run Agent 2 for **all seven** vendors, then
      `verify_corpus` must show 0 FAIL again, then commit the corpus.
- [ ] Fix defect **33** in `config/settings.yaml` (the comment) — one-line change, do it with 27.
- [ ] Delete `_to_delete/` (7 dead lock files).
- [ ] Send the consolidated clarification email. Day 16 is too late to ask.

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
| **13 Aug** (day 6) | Code commit. Clarification email. Defects 27–30 + 33. Re-extract all 7. Corpus commit. |
| **14–16 Aug** | Extract the shared flag predicates out of `tools/verify_corpus.py` into `src/`, then build `src/agent3_review.py` on top of them. **`verify_corpus.py` is already a working prototype of Agent 3** — it computes `vendor-score`, `field-status`, `off-home-evidence`, `unread-home-page`, `unusable-page`, `thin-density`. Do not reimplement those checks in Agent 3; import them, or the tool and the product will drift and that is defect 15 again. Flags known to be required from real data: (a) evidence drawn only from outside a field's `preferred_source_types` — on GitLab three of five core fields draw their strongest evidence from the *privacy policy*; (b) gated evidence — Sentry publishes that its SOC 2 reports are "available to customers … upon request"; (c) **coverage vs score, defect 31**. Populate `VendorBrief.vendor_overview` and `.product_category` — both are required by the brief's Expected Output and neither is one of the 8 extracted fields; take the category from `vendors.yaml` and the overview as a quote from the product page. |
| **17–18 Aug** | `src/export.py` (JSON/CSV/Markdown) and `src/orchestrator.py` (1→2→3). Wire the Vendor brief and Export tabs. |
| **19 Aug** | **FEATURE FREEZE.** Anything unfinished becomes a limitations entry — that scores better than a half-working feature. |
| **14 Aug onward, in parallel** | `docs/evaluation.md`. It is already ~90% writable from the corpus and the defect log and does **not** depend on Agent 3. Writing it early hedges the worst case. |
| **20–25 Aug** | `assumptions_limitations.md`, `test_cases.md`, `code_walkthrough.md`. Correct `architecture.md` (§8). Screenshots. |
| **26 Aug** | Fresh-clone test: delete the venv, follow the README exactly, confirm it runs first try. Remove `_to_delete/`. Zip including `.git/`, excluding `.venv/`. |
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
  GDPR"* scores **High**. **Verified false — see defect 28.** It is a bare `<h2>` with no body, so
  it scores `heading_only` → Medium, ranks 9th of 9, and never reaches the brief at all.
  Rewrite the paragraph around what actually happened; it is a better story than the original claim.
- **`docs/architecture.md` §3** says "94 offline tests" and "43 seed URLs". Recount both.
- **`config/settings.yaml` lines 33–37** — the two-test worked examples are stale. See defect 33.
- **`docs/confidence_rules.md`** is current as of 12 Aug and contains a closing section naming two
  rules it previously described incorrectly. Keep that section — it reads as rigour.

---

## 9. Commands

```powershell
cd "C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\vendor-dd-prototype"
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q                       # re-run after every extraction, not just after code changes
python tools/verify_corpus.py   # expect 0 FAIL before any commit
streamlit run app.py            # then http://localhost:8501
```

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
| Source types: product, pricing, security/trust, privacy, terms, docs, integrations, status | Met | 7–8 per vendor collected |
| Structured store with vendor name, source URL, source type, page title, collected text, date collected, tags, evidence note | Met — `SourceRecord` maps 1:1 | `src/schema.py` |
| Input: vendor name/list, collected URLs or pre-prepared source file, optional category filter | Partial — **optional research-category filter not implemented** | `app.py` |
| Output: overview, category, key sources, security, privacy, support, integrations, pricing, missing/unclear, review flags, evidence snippets, confidence | Schema complete, **unpopulated until Agent 3** | `VendorBrief` in `src/schema.py` |
| Streamlit: select vendor · view sources · run or replay · see agent steps · inspect evidence · view brief · export JSON/CSV/Markdown | 5 of 7 — **brief and export tabs are stubs** | `app.py` tabs 4 and 5 |
| Runs locally on a standard laptop, low cost, no heavy infrastructure | Met | no LLM, no GPU, no paid service |
| Missing or unclear information flagged instead of guessed | Met for collection, **pending for the brief** | caveats + `verify_corpus`; Agent 3 owes the flag list |
| Lower-cost alternatives (Ollama, local models, rule-based, template summaries) mentioned and supported | **Rule-based is built; the alternatives are not yet written down anywhere.** The brief asks that they be *mentioned* | owed by `assumptions_limitations.md` |
| Deliverables: prototype · orchestration code · corpus · ≥5 sample outputs · README · architecture note · assumptions & limitations · test cases · evaluation summary · screenshots | 4 of 10 complete | see §7 |
| Zip or repository, all code, data, README, screenshots, sample outputs | Planned | zip including `.git/`, excluding `.venv/` |
| Queries only via projects@firstquadrantlabs.com, consolidated | **Not yet sent** | §7 |
