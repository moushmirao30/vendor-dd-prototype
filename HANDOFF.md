# HANDOFF — Vendor Due-Diligence Research Workflow Prototype

**Purpose of this file:** everything a fresh chat session needs to pick this project up cold.
Read it top to bottom before touching anything. Last updated: **10 August 2026**.

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
- **Verify before presenting.** Triple-check, find faults in your own answer, correct it, then show me.
- **I know Python basics only.** Write the code, then explain it line by line so I can defend it
  in a review. Never hand over unexplained code — "an AI wrote it" ends an interview.
- Be token-efficient without losing correctness.

---

## 1. The project in one paragraph

Internship project for **First Quadrant Labs**. Build a bounded 3-agent workflow that collects,
structures and summarises **public** vendor due-diligence information into consistent first-pass
research briefs, where every statement traces back to the page it came from. It is a **restraint
test**, not an ML test: the brief bans manager agents, memory layers, autonomous browsing loops,
paid tools and risk scoring. Roughly half the marks live in the five prose deliverables.

- **Deadline: Saturday 29 August 2026.**
- Submit to **projects@firstquadrantlabs.com** AND upload to the LMS. Zip or repo format.
- All clarifications go through that one project email, consolidated into a single message.
- Brief PDF: `C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\Project_Brief_1.pdf`
- Repo: `C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\vendor-dd-prototype`

### The company, and how to score with them
First Quadrant Labs is a **consulting firm** (finance, technology, AI, cybersecurity, digital
marketing); testimonials are from CFOs and analytics heads at banks and investment firms. Their AI
page sells **explainability** as the product — *"We ensure your team understands how models work,
what they predict, and how decisions are made"* — and a four-stage method:
**Discovery & Assessment → Strategy & Solution Design → Development & Deployment → Monitoring &
Optimization**. Mirror that vocabulary in the README and architecture note. In consulting the
deliverable *is* the product, so document polish counts as much as code.

---

## 2. Locked decisions (do not relitigate without a reason)

| # | Decision | Why |
|---|---|---|
| Category | **Developer productivity tools** | richest public trust/security/status pages |
| Vendors | GitLab, Linear, Sentry (rich) · Postman, Atlassian (awkward) · GitHub, JetBrains (hard). Reserve: Docker, CircleCI, Vercel | deliberately mixed so the evaluation has real failure modes, not just successes |
| LLM | **None by default.** Rule-based + template extraction; any model backend stays behind an off-by-default flag | keeps "runs on a standard laptop, low cost" literally true |
| Orchestration | **Plain Python**, strictly linear 1→2→3. No LangGraph/CrewAI | a 3-step linear flow does not need a framework; brief rewards simplicity |
| Storage | **JSON canonical + CSV export** | page text contains commas/quotes/newlines; CSV as primary store corrupts silently |
| Agent 1 design | **Curated seed first, discovery fills gaps** | a human-checked URL outranks a guessed one — see defect #10 |
| Code delivery | Written into the repo with full explanation + `docs/code_walkthrough.md` | I must be able to defend every line |

---

## 3. What exists right now

**7 commits, latest `9dae9cc`. 51/51 pytest passing.**

```
vendor-dd-prototype/
├─ app.py                     Streamlit UI — Agent 1 live, Agents 2/3 stubbed
├─ README.md · requirements.txt · .gitignore · HANDOFF.md
├─ config/
│   ├─ vendors.yaml           7 vendors, 43 seed URLs, per-vendor observation notes
│   ├─ field_dictionary.yaml  8 fields, 112 terms (every term marked "# observed" is real)
│   └─ settings.yaml          all policy: UA, delays, caps, confidence thresholds
├─ src/
│   ├─ fetch.py               PageFetcher + RobotsPolicy + versioned disk cache
│   ├─ parse.py               page_to_blocks · find_evidence · score_field_confidence
│   │                         · main_text · visible_text · page_title
│   ├─ agent1_collect.py      AGENT 1 — collector, audit trail, save/load run
│   └─ schema.py              SourceRecord · ExtractedField · VendorBrief
├─ data/corpus/               gitlab.json (7 records) + gitlab_run.json (audit trail)
├─ data/cache/html/           v2_*.html — offline replay
├─ docs/confidence_rules.md   the written confidence rule + worked examples
└─ tests/                     51 tests, all offline
    ├─ test_parse.py (9) · test_agent1.py (13) · test_fetch_robots.py (6)
    ├─ test_app_smoke.py (11) · test_text_quality.py (7)
    └─ fixtures/  5 HTML files modelled on real vendor page shapes
```

### The core idea, in case it needs restating
Split each page into **blocks** (one heading + the paragraphs under it), then match each block
against a plain phrase list in `config/field_dictionary.yaml` — a substring test, **not** a regex.
Keep the whole matching block as evidence: heading, snippet, matched terms, source URL. Vendors
write the same fact differently — `SOC 2 Type II` (Linear), `SOC 2 Type 2` (GitLab),
`SOC 2 and 3` (Postman), `Service Organization Controls` (Linear), or an image with alt-text
`AICPA SOC logo` (Atlassian) — which is exactly why a phrase list beats a pattern.

**Critical architectural point:** evidence extraction reads **raw HTML**, never `collected_text`.
This is not a detail — see defect #7. Say so in the architecture note.

---

## 4. Verified facts collected from real vendor pages (10 Aug 2026)

- **GitLab security page** — `<h3>SOC Certification</h3>` → *"GitLab maintains a SOC 2 Type 2 report
  for the Security, Confidentiality and Availability Trust Services Criteria for GitLab.com."*
  Also ISO/IEC 27001:2022. No uptime, residency or encryption text.
- **Linear** — cleanest of the seven. Heading + real sentence per topic; explicit residency
  ("European Union or the United States"); TLS 1.2 and AES 256-bit.
- **Sentry** — SOC 2 Type I/II and ISO 27001, but reports are *"available to customers … upon
  request"* — gated evidence, a genuine flag. Its **status page** yields per-component uptime
  ("99.99% uptime", "All Systems Operational") plus separate US and EU components.
- **Postman** — prose sentence + bare list including "SOC 2 and 3"; only vendor of the seven to
  state an uptime figure on its security page ("99.9% SLA on our Enterprise plan"); residency
  ("AWS servers in the EU and the U.S.").
- **Atlassian** — **certifications are images.** Only text is alt-text "AICPA SOC logo". Must score
  Low with a "logos only, verify manually" flag. `tests/test_parse.py` asserts it can never be High.
- **GitHub** — `/trust-center` and `/security` both lack certifications, residency, SLA, encryption.
  `/security` has only an API marketing line. Correct output: NOT_FOUND + review flag.
  This is the project's strongest human-in-the-loop argument.
- **JetBrains — NOT VERIFIED.** All its URLs are candidates.
- **Uptime is not a security-page fact.** It lives on status pages. Statuspage-hosted pages are
  server-rendered, so plain `requests` + BeautifulSoup reads them — **no JavaScript rendering needed.**
- **GitLab robots.txt** disallows only `/search/` and `/api/`.

### First clean live run — GitLab, 10 Aug 2026
11 URLs tried · 7 pages collected · 0 flagged. security 4,156 chars · privacy 35,888 ·
pricing 16,388 · docs 11,863 · terms 5,061 · product 2,885 · status 489.

---

## 5. Twelve defects found so far — and the headline they add up to

**The automated test suite caught almost none of these. Every one was found by opening the
artifact and reading what it actually said — the screen, then the JSON, then the raw HTML.**
That sentence, with this table behind it, is the spine of the evaluation summary deliverable.

| # | Defect | Fix |
|---|---|---|
| 1 | Source table rendered as an empty grey box in Chrome while the data was correct server-side | `st.dataframe` canvas collapses to zero height inside `st.tabs` → explicit `height=` |
| 2 | `use_container_width` is removed API (removal date 2025-12-31) | `width="stretch"`; streamlit pinned `>=1.49,<2.0`; a test greps app.py |
| 3 | LinkColumn `display_text` regex made four different GitLab URLs render identically | show full URLs |
| 4 | **False "disallowed by robots.txt"** — 4 of 6 sources dropped, blaming the vendor | `RobotFileParser.read()` uses urllib's UA; GitLab's CDN 403'd it; stdlib treats 403 as disallow-all. Now fetch robots.txt with our own UA and apply RFC 9309 |
| 5 | Request cap counted successes not requests — 25 requests to keep 2 pages | `max_requests_per_vendor` |
| 6 | `@st.cache_data` keyed on filename; editing settings.yaml did nothing | mtime in the cache key |
| 7 | **Content cleaner discarded the evidence** — trafilatura kept 7.6% of GitLab's security page, dropping every certification sentence | ratio guard + `text_extractor` field. Agent 2 was safe only because it reads raw HTML |
| 8 | Mojibake — UTF-8 decoded as ISO-8859-1 corrupted quotes in evidence snippets | `apparent_encoding`; cache key versioned to `v2_` |
| 9 | No replay — a browser refresh erased the audit trail; the brief requires "run **or replay**" | `save_run` / `load_previous_run` |
| 10 | A guessed URL beat a human-verified one: `/support` returned 200, redirected to one Zendesk article, and won over docs.gitlab.com | curated seed first; redirects reported in the trail |
| 11 | Request budget silently dropped page types probed last | `budget-stop` step recorded — no silent caps |
| 12 | Status page: 489 chars from a 2,858-char page passed the 15% ratio guard | absolute floor `MIN_ABSOLUTE_CHARS = 800` |

### Principles these produced (quote these in the docs)
- **AppTest verifies data, not rendering.** Screenshot the browser before calling any UI done.
- **A 200 means the URL exists, not that it is the right page.**
- **Never let a refusal be a bare boolean.** "disallowed by robots.txt" hid a bug for a whole run;
  `(allowed, reason)` would have exposed it instantly.
- **Re-read the brief's verbs.** "Run or replay" is two features.
- **Python's stdlib robots parser is stricter than RFC 9309.** We follow the RFC and record which
  branch fired.
- **We never bypass access controls.** No browser-impersonating headers. A vendor refusing our
  honest User-Agent is recorded as a finding for manual review — the brief bans bypassing.

---

## 6. Environment gotchas that will waste your time

1. **Streamlit hot-reloads `app.py` but NOT modules under `src/`.** After any `src/` change,
   restart the server (`Ctrl+C`, then `streamlit run app.py`). A browser refresh is not enough.
   This cost one full debugging cycle (`TypeError: unexpected keyword argument`).
2. **Run everything from the repo root** — `app.py` does `from src.agent1_collect import …`.
3. **Git inside the Cowork-mounted folder** leaves stale `.git/index.lock` and `.git/HEAD.lock`
   that cannot be unlinked. Workaround: `mv` them into `_to_delete/`, then re-run git.
   **Better: run git from a normal Windows terminal**, where it just works.
4. **`_to_delete/` must be deleted before submission.** It holds lock files and the mojibake-era
   cache. It is now gitignored but the folder is still on disk.
5. **The cache is versioned** (`v2_` prefix). Bump `PageFetcher.CACHE_VERSION` whenever a
   fetch-layer change makes existing cached pages wrong.

---

## 7. Where things stand and what happens next

### Immediately outstanding
- [ ] **Re-run GitLab after the seed-first change** and confirm the `docs` row reads
      `https://docs.gitlab.com/`, not a `support.gitlab.com/hc/...` article.
- [ ] **Refresh the browser without pressing anything** — the collected table must persist,
      labelled *loaded from a previous run*. That is replay working.
- [ ] **Collect the other six vendors** (Linear, Sentry, Postman, Atlassian, GitHub, JetBrains).
      Expect GitHub and Atlassian to produce genuine NOT_FOUNDs — that is the point of including them.
- [ ] **Verify JetBrains URLs.** All seven are unconfirmed candidates.

### Remaining build
| Days | Work |
|---|---|
| 9–13 | **Agent 2 — Evidence Extraction.** `src/agent2_extract.py`: run `page_to_blocks` + `find_evidence` over each corpus page per field dictionary, apply `score_field_confidence`, emit `ExtractedField` objects with snippet-level provenance. The core is written and tested in `parse.py` — this is the wrapper. |
| 14–16 | **Agent 3 — Brief Review.** `src/agent3_review.py`: apply the vendor-level score in `docs/confidence_rules.md`, list missing/unclear fields, raise review flags, assemble `VendorBrief`. Then `src/export.py` (JSON/CSV/Markdown) and `src/orchestrator.py` (runs 1→2→3). Wire the Evidence, Vendor brief and Export tabs. **Feature freeze at day 16.** |
| 17–18 | **All documents.** `docs/architecture.md` (use FQL's four stage names), `assumptions_limitations.md`, `evaluation.md` (use the defect table in §5 — with real numbers), `test_cases.md`, `code_walkthrough.md`. Screenshots. |
| 19 | **Fresh-clone test**: delete the venv, follow the README exactly, confirm it runs first try. Remove `_to_delete/`. Zip. Submit. Upload to LMS. |

Anything unfinished at day 16 goes into the limitations note as "not implemented, and here's why" —
that scores better than a half-working feature.

---

## 8. Commands

```bash
cd "C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\vendor-dd-prototype"
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
pytest -v                       # expect 51 passed
streamlit run app.py            # then http://localhost:8501
```

No API key, no account, no GPU, no paid service. After one collection run the whole workflow
replays offline from `data/cache/html/`.

---

## 9. Scope boundaries — never cross these

Deliberately **not** built: procurement decisions · official vendor risk scores ·
legal/compliance/security approval · access to private vendor portals · aggressive scraping or
restriction bypassing · a production procurement platform · any dependency on paid databases or
enterprise tooling · manager agents · memory layers · autonomous browsing loops.

Collection policy: robots.txt read before every fetch (RFC 9309 semantics), 2-second per-domain
delay, honest User-Agent, 10 pages / 20 requests per vendor, no JavaScript rendering, everything
cached on first fetch.

Every output states plainly that it is a **first-pass internal research aid** and that final
review remains manual.
