# Assumptions and limitations

**Written 19 August 2026. Every figure re-derived against the frozen corpus on that
date rather than quoted from an earlier document** — four worked examples in this
repository have already gone stale, and two real defects were found by re-deriving
them.

## What this document is, and what `evaluation.md` is

They answer different questions and neither repeats the other.

| Document | Question |
|---|---|
| `docs/evaluation.md` | **Did it work?** Measured results, per vendor, and where manual review is still needed. |
| **This document** | **What did we take for granted, and what can the system structurally not do?** |

A limitation here is a property of the design. A finding there is a property of the
seven vendors. Confusing the two is the central failure this whole prototype exists
to report, so the split is deliberate.

---

## 1. Assumptions — things taken as true without proof

Each of these would change a conclusion if it turned out to be false. They are
listed so a reviewer can attack the premise rather than only the output.

| # | Assumption | If it is false |
|---|---|---|
| 1 | **A page on the vendor's own domain is an authoritative statement by that vendor.** | A stale or unmaintained page would be read as a current commitment. We record `date_collected` on every row so the reader can judge freshness, but we cannot tell when the vendor last reviewed the page. |
| 2 | **A vendor that publishes a fact publishes it in text a browser-less fetch can read.** | Disproved for 8 of 49 pages (16.3%), across 4 of 7 vendors. This is the largest known limitation and §3 is about it. |
| 3 | **A heading plus the paragraphs under it is a coherent unit of meaning.** | Holds well on trust, security and legal pages; holds badly on marketing pages built from independent layout cards, where a heading and the text beneath it can be unrelated. Linear's `data_residency` is the live example — heading *"Multi-region hosting"*, body about customer counts. |
| 4 | **A curated seed URL is more trustworthy than a discovered one.** | Adopted after discovery preferred a Zendesk help *article* over GitLab's docs index because it returned HTTP 200 first. If a seed decays, the vendor's real page is missed and reported as never located — which is why a never-located page type is always reported and never silently omitted. |
| 5 | **The five core fields are the ones a first-pass procurement review needs.** | Chosen from the brief's own output list. Data residency, encryption and uptime are extracted but not scored, because most vendors omit them by convention rather than by policy and penalising that would make the number meaningless. |
| 6 | **A term matched as a whole word is a term used in its intended sense.** | False in a measurable minority. `SLA` inside a CVSS remediation clause once scored High for uptime. Whole-word matching removed the worst class of error — `sla` matched "Slack" 11 times of 13 before it — but a string match is not a meaning, and no rule-based system reads sense. |
| 7 | **The reviewer reads the brief, not the audit trail.** | This drove every design decision about where a caveat is written. It has been wrong-way-round twice: defect 24 and defect 40 both put an honest record in the trail and a misleading sentence in the brief. |
| 8 | **A frozen corpus is a fair basis for evaluation.** | See §5. The corpus is dated 13 August 2026 and vendor pages demonstrably move. Every figure in this project describes what those pages said on that date. |

---

## 2. Limitations by deliberate design

These follow from decisions the brief asked for, or that we made and documented.
None is a bug.

### 2.1 No language model, so `value` is always a quote

The brief permits *"OpenAI API lightly… keep it optional and cost-conscious"*. We
built none, and the client confirmed in writing on 18 August 2026 that
**"fully rule-based extraction is acceptable as the primary behaviour"**, adding:
*"retaining verbatim evidence from the source is valuable for auditability and
reduces hallucination risk."*

The consequence is that a field's `value` is a **verbatim sentence from the page**,
never a synthesis. It reads less smoothly than a generated summary and it is
traceable, which is the trade we chose. **We produce more NOT_FOUND results than an
LLM approach would**, and that is the intended direction: a flagged gap is cheaper
to fix than a fluent guess.

### 2.2 No JavaScript rendering — the largest measured limitation

The client confirmed on 18 August: *"You are not required to introduce Playwright,
Selenium, or another headless-browser layer."*

**Cost, measured: 8 of 49 pages (16.3%), across 4 of 7 vendors.** Atlassian's Jira
product page returns 898 KB of HTML and yields **52 readable characters and zero
heading blocks**; its pricing page yields **66 characters from 1.21 MB**. Postman's
privacy policy yields **0 characters from 4.7 KB**.

**No-JavaScript costs nothing on trust, legal and status pages, and costs
everything on modern marketing pages.** That is a favourable trade for this
project, whose fields come mostly from the former — but it is a trade, not a free
choice, and the cost is reported per page rather than argued away.

Two guarantees follow, in the client's own vocabulary:

- Information **not found** on the vendor's public sources, and information that
  **could not be evaluated** because the page could not be reliably extracted, are
  distinguished per field — tested against *that field's own* home page, not the
  vendor's worst page. Currently 3 could-not-be-evaluated against 7 genuine
  not-founds.
- Before a category is marked unavailable, every other collected page is searched,
  and the brief states how many were searched rather than implying it.

### 2.3 Three agents, strictly linear, no loops

Brief-mandated. Agent 2 cannot ask Agent 1 for another page; Agent 3 cannot ask
Agent 2 to re-extract. A missing page is a recorded fact that travels forward, not
a retry. This costs recall — a better URL guess after seeing the extraction results
would find more — and buys explainability, which is what the brief is testing.

### 2.4 Public sources only, and access rules are respected

`robots.txt` is read before every fetch using RFC 9309 semantics, with a 2-second
per-domain delay, an honest User-Agent, and a cap of 10 kept pages and 20 requests
per vendor. **No browser-impersonating headers and no restriction bypassing.**
A vendor's refusal is data; a tool whose findings depend on ignoring it cannot be
shown to a client.

### 2.5 The confidence rule is mechanical, and cannot be otherwise

The client's definition of High — *"direct, explicit evidence… with the requested
field clearly answered"* — is a semantic judgement. A rule-based system cannot
decide whether a field is *clearly answered*. Their own next sentence supplied the
resolution: track extraction quality separately. So the system reports **three
numbers instead of one**: how much evidence was found, how good it is by mechanical
proxies for their definition, and how much could actually be checked.

**The confidence axis is reported as counts, not a score, deliberately.**
Compressing three levels into 0–10 needs two thresholds, and we would be choosing
them while looking at our own seven vendors — fitting the rule to the answer. A
count needs no threshold and cannot be tuned. Derivation in
`docs/confidence_rules.md` §Step 6.

---

## 3. Limitations of the method that remain open

Recorded rather than fixed. In each case the obvious fix was measured against the
corpus and found to cost more than it bought — which is itself the finding.

### 3.1 A section title inside body text is indistinguishable from a sentence

Atlassian's `security_trust` value is **"Sensitive Health Information and HIPAA."**
— a numbered terms-of-service section title sitting inside prose. No rule we have
separates it from a real sentence. Raising the claim floor to exclude it would
over-fit to one vendor, which the locked decisions forbid. **Agent 3 flags it; the
threshold stays.**

### 3.2 A heading can match while its body is unrelated

Linear's `data_residency` quotes *"Trusted by more than 40,000 product teams around
the globe"* under the heading *"Multi-region hosting"*. The heading matched; the
body is marketing copy. The card prints the heading separately so a reviewer can
see the match, but the quote alone misleads. This is assumption 3 failing.

### 3.3 Cited terms can sit outside the printed quote

**21 of 122 evidence cards cite 43 terms that are not visible in the 600-character
snippet.** Every one is genuinely on the page — this is not fabrication — but a
reviewer cannot verify it from the card. Agent 3 marks those cards
(`terms_not_shown`) and the interface prints a warning on them.

### 3.4 A confidence label can be earned by a sentence that does not carry the term

**9 of 122 cards.** `evidence_level` measures the longest sentence anywhere in the
matched block. **Deliberately not fixed:** scoring only the term-carrying sentence
also demotes Sentry's *"High Availability"* heading with a full paragraph beneath
it, and GitLab's *"Trust Center Documents"*. Vendors do not repeat a heading inside
its own paragraph, so the strict rule trades a cosmetic over-score for a false
negative — the same mistake defect 23 exists to prevent. `verify_corpus.py` raises
`claim-not-in-matched-sentence` on all nine so a human sees them.

### 3.5 Conflict detection returns zero, and that is reported

`conflicting_values` compares numeric and categorical values for the same field
across sources. It is unit-tested and finds **nothing** on the real corpus.
Reported as a finding rather than omitted: **semantic** contradiction between two
prose statements needs a language model this prototype does not have.

An earlier negation-based detector fired on 3 of 7 vendors and **every hit was
false** — it compared three blocks of the *same* privacy policy against each other,
because a privacy policy contains both "we do not sell your data" and ordinary
positive statements. It was **deleted, not tuned.** A detector that produces false
positives is worse than one that produces nothing, because it teaches the reviewer
to skim past flags — and the flags are the product.

### 3.6 The system rewards whichever page a vendor writes in full sentences

**21 of 56 fields draw all their evidence from outside the page where the fact
belongs.** Counted by the page it actually came from:

| Source of off-home evidence | Fields |
|---|---|
| pricing | 11 |
| privacy | 8 |
| security | 7 |
| terms | 4 |
| status | 2 |

**Pricing pages lead, and that is a structural bias, not a coincidence.** A pricing
page lists security and support features tier by tier in prose, so it matches
security, support and integration terms while being the *marketing* description of
those things rather than the commitment. Privacy policies come second for the
opposite reason: they are legally drafted, so they are unusually full of complete
sentences that clear the claim floor.

*(An earlier draft of this section said privacy led. It does not, corpus-wide — that
was a GitLab-specific observation generalised without re-counting, which is the same
mistake as the four stale worked examples. Re-derived 19 August: pricing 11,
privacy 8.)*

Every one is flagged as weak evidence; **none is suppressed**, because GitLab
genuinely does state its FedRAMP position on its pricing page, and an extractor that
overruled that would be overruling the vendor. `preferred_source_types` orders
evidence; it never filters it.

### 3.7 `tags` in the corpus restates the page type

The brief names `key tags` as a corpus field — *"security, privacy, pricing,
support, integrations, uptime, documentation"*. `SourceRecord.tags` carries the
page **type** plus a `human-verified` marker: **39 of 49 rows have
`tags == [source_type]` exactly**, and four of the brief's seven example words
never appear as a tag at all.

That is honest but thin, and the reason is structural: tags are written by Agent 1,
which knows what kind of page it fetched and not what was later found on it. The
information the brief wants belongs to Agent 2, and having Agent 1 compute it would
mean doing Agent 2's job inside Agent 1 — breaking the linear flow the brief
requires.

**Resolved at export time instead.** `corpus.csv` carries an `evidence_tags`
column, derived from Agent 2's results: the due-diligence topics that actually
found quotable evidence on that page. It is populated on **26 of 49 pages**; an
empty value means the page was collected, searched, and contributed nothing — which
is itself worth seeing. This needed no re-collection, which mattered because the
corpus is frozen (§5).

### 3.8 Thresholds are chosen, not derived

The 40-character claim floor, the 600-character usable-text floor, the 2.0
readable-chars-per-KB density floor, the 15% cleaner ratio and the three-evidence
cap are **judgements**. They live in `config/settings.yaml` with worked examples, so
a reviewer who disagrees changes one line and re-runs. They were tuned against
seven vendors and would need re-checking against a different category.

---

## 4. The submitted archive cannot replay the full pipeline. This is an instruction.

First Quadrant Labs, 18 August 2026:

> *"We recommend not including the complete 22 MB cache of verbatim third-party HTML
> pages in the final submission archive."*

The cache is therefore excluded, and the consequence is stated rather than
discovered: **a fresh clone can review, but cannot re-extract, until the reviewer
re-collects the public sources.** The README explains how.

| In a fresh clone | Works? |
|---|---|
| Read the corpus, briefs, source manifest, exports | yes |
| Re-run Agent 3 (`--mode review`, the default) | yes — verified by deleting `data/cache/` and running it: 7 of 7 briefs |
| Re-run Agent 2 (`--mode replay`) | **no** — refuses, names the missing pages, names the mode that works |
| Re-fetch from vendors (`--mode collect`) | yes, with a network connection |

**This is a limitation, not a defect, because it was requested.** Naming the
difference is the point: an unexplained inability to reproduce results would be a
defect.

The guard exists because of what happened without it. With the cache absent, Agent
2 returned every field as NOT_FOUND under the printed sentence *"nothing matched on
any page we could read"* — about pages nobody had opened — while coverage reported
5/5 verified. **All seven vendors would have been reported as publishing nothing,
in the exact configuration the client asked us to submit.**

The **source manifest** (`data/exports/source_manifest.csv`) is what replaces the
cache: one row per page *attempted*, not per page kept — 54 attempts across seven
vendors, of which 5 were never collected and 8 were collected but unreadable. It is
the only artifact that lets a reader distinguish *"the vendor is silent"* from
*"we could not look"*.

---

## 5. The corpus is frozen, and pages have moved since

**It is not uniformly 13 August, and saying so was an error this document repeated
for three days.** `data/exports/source_manifest.csv` records `date_collected`
**2026-08-13** for Atlassian, GitHub, Linear, Postman and Sentry, **2026-08-19** for
**GitLab**, and **2026-08-22** for **JetBrains** — the two vendors whose seed URLs
were corrected, JetBrains re-collected once more from the interface on the 22nd with
every figure reproducing unchanged. The right sentence is *"13 August, with GitLab
re-collected on the 19th and JetBrains on the 22nd"*, and the manifest is where a
reader should check it rather than trusting this paragraph — including the sentence
you are reading, which has now been wrong twice.

Collection has **not** been re-run since, deliberately: every measured figure in
`evaluation.md` and `confidence_rules.md` was fact-checked by script
against that corpus, and re-collecting would invalidate all of them for no
analytical gain. The figures were re-verified by running the full workflow on
20 August and every one reproduced.

Drift is real and is reported as a finding:

- Linear's `docs` page went from **24,444 bytes to 540,090** between 12 and 13 August.
- Linear's security page now publishes `<h2>SOC 2 compliance</h2>` with an **empty
  body**, where a complete SOC 2 sentence was recorded on 10 August.

**The cache, not the live web, is the record of what was evaluated.** A reviewer who
re-collects should expect different numbers, and that difference is itself a result:
a first-pass research brief has a shelf life, and this one states its date.

---

## 6. Lower-cost alternatives — the brief asks that these be mentioned

The brief asks that lower-cost options *"be mentioned and supported where
practical"*. **The delivered system is already the lowest-cost option available**:
no API key, no account, no GPU, no paid service, no model of any kind. It runs on a
standard laptop and replays offline. The alternatives below are recorded for
completeness and because the client's guidance keeps an LLM summarisation toggle on
the table as an optional extra.

| Option | Cost | Where it would fit | Assessment |
|---|---|---|---|
| **Rule-based extraction + verbatim quotes** (delivered) | zero | the whole pipeline | Chosen. Client-endorsed for auditability. Produces more NOT_FOUND results, which the brief rewards. |
| **Template summaries** — assembling brief prose from extracted fields with fixed sentence frames | zero | the vendor overview and the missing-or-unclear list | **Partially used already**: the missing-or-unclear lines and confidence reasons are template-assembled from mechanical facts. Deliberately not extended to the field `value`, because a machine-assembled sentence is no longer traceable to a page — the locked decision `value` is a quote. |
| **Ollama with a small local model** (e.g. Llama 3.x 8B, Mistral 7B) | zero marginal, ~8 GB RAM | an optional summarisation pass over already-extracted evidence | The realistic upgrade if summarisation is wanted. Keeps "no paid service" true and sends no vendor text to a third party — which matters when the input is another company's legal pages. Costs a multi-GB download and rules out the "standard laptop, instant" claim. |
| **A hosted LLM API used lightly** (the brief's own suggestion) | per-token | the same optional pass | Deferred. The client's hard constraints — must work **completely without an API key**, and any summary **must retain links to the underlying evidence** — mean the rule-based path has to exist and be complete first. It now is, so this is additive rather than architectural. |
| **A headless browser** (Playwright/Selenium) | zero marginal, high complexity | the 8 unreadable pages | **Explicitly excluded by the client.** It would recover the 16.3%, at the cost of a browser dependency, much slower collection, and a heavier machine — against a brief that asks for "a standard laptop, low cost". |
| **SQLite instead of JSON** (the brief lists it as an option) | zero | the corpus store | Not used. JSON is canonical because page text contains commas, quotes and newlines, and a reviewer can open a JSON file in any editor and check a quote by eye. CSV is produced as an **export**, never as the store; a round-trip test proves a comma, a quote and a newline survive in one cell. |
| **LangGraph / CrewAI** (mentioned in the brief) | zero | orchestration | Not used. A three-step linear flow does not need a framework, and the brief itself says "simple custom Python orchestration". `src/orchestrator.py` is 364 lines of which roughly 90 are executable — the rest is the reasoning, kept in the file rather than in a wiki — and every handoff is visible in one place. |

**`sentence-transformers`, FAISS and Chroma — declined.** The brief offers them
*"if retrieval is used"* and *"if you decide to add lightweight retrieval"*. No
retrieval layer was built. With 49 pages across seven vendors, exhaustive matching
over every block on every page is fast, exact and explainable; an embedding index
would add a model download, a similarity threshold nobody could justify, and a
layer of approximation between the vendor's sentence and the reviewer's screen.
The whole argument of this project is that a reviewer can check every step by hand,
and a nearest-neighbour score is the first step that breaks that.

**Departures from the brief's suggested stack, stated because a silent omission
would be a compliance failure even where the engineering choice is right:**
LangGraph and CrewAI declined (above); SQLite declined in favour of JSON (above);
the optional LLM not built (above); **trafilatura kept and used on 42 of 49 pages**,
with a visible-text fallback on the other 7 when it retained too little — GitLab's
security page is one, where trafilatura kept 12% of the text and discarded every
certification sentence.

---

## 7. What this prototype must never be used for

From the brief, and repeated on every export:

> **First-pass internal research aid.** Generated from public web pages only. This is
> not a vendor risk score, a security approval, or a procurement decision. Every
> field must be confirmed by a human reviewer before use.

It does not make procurement decisions, assign official vendor risk scores, claim
legal, compliance or security approval, access private vendor portals, or replace
a security questionnaire. **13 of 56 fields (23%) currently carry a collection
caveat**, and no vendor reaches an overall High confidence. Those are the honest
outputs of a rule-based tool reading public marketing pages, and they are reported
rather than tuned away.
