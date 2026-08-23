# Evaluation Summary

**Vendor Due-Diligence Research Workflow Prototype — First Quadrant Labs**
Moushmi Rao · corpus collected 13 August 2026, **GitLab re-collected 19 August, JetBrains
22 August** · analysis and revision 18–22 August 2026
**Status: complete. Three agents, orchestrator, export layer and interface all built and running.
Figures below cover the full pipeline, Agent 3 included.**

This document answers the four questions the project brief asks of the evaluation summary:
whether sources were collected correctly, whether the extracted fields are useful, whether the
summaries are source-grounded, and where manual review is still required.

Every number below was produced by running the workflow over seven real vendors and reading the
artifacts it wrote. Nothing here is estimated. Where a claim could not be verified, it says so.

---

## Executive summary — read this page, then stop if you have five minutes

**Seven developer-productivity vendors. 49 public pages from official domains. 8 fields per
vendor. No LLM, no browser automation, no paid service — every claim in every brief is a verbatim
quote with the URL it came from.**

### The finding

> **The dangerous failure is not a missing answer. It is a confident answer about a company that
> nobody checked.**

A missing field is visible: a reviewer sees the gap and fills it. A **wrong** field that arrives
labelled *High confidence*, with a real quote and a working URL beneath it, is invisible — it
recruits the reviewer's trust and then spends it. **Five distinct mechanisms produced exactly that
on real vendor pages** (§0): JavaScript-rendered pages that return 898 KB of HTML and 52 readable
characters; a privacy policy that is a redirect shell with zero readable characters, silently
answered from a different page; a security page whose URL could not be guessed in six attempts
while the vendor did publish one; a technically-correct quote from a terms-of-service liability
clause standing in for a security posture; and a safeguard that had never once executed since the
day it was written. All five are closed, each by a named defect, each measured on the corpus.

### The three numbers, and why one was never enough

The system reports **three axes side by side and never one alone**. Reporting only the first was
itself a defect (42) — it made a vendor whose documents were largely unreadable indistinguishable
from one that was fully read.

| Vendor | Evidence found | Confidence | Coverage checked | Flags |
|---|---|---|---|---|
| GitLab | 10/10 | Medium — 2 of 5 core fields High | **5/5** | 6 |
| Sentry | 10/10 | Medium — 2 of 5 core fields High | **5/5** | 5 |
| GitHub | 10/10 | Medium — 2 of 5 core fields High | **5/5** | 4 |
| Postman | 10/10 | Medium — **0** of 5 core fields High | **2/5** | 6 |
| Atlassian | 10/10 | Medium — **0** of 5 core fields High | **2/5** | 8 |
| Linear | 6/10 | Low — 1 High, 3 Medium, 1 Low | 3/5 | 3 |
| JetBrains | 5/10 | Low — 1 High, 2 Medium, 2 Low | 2/5 | 5 |

- **Evidence found** — how much quotable material the extractor located. It counts what was found.
- **Confidence** — how good that material is, on the client's definition rather than sentence
  length. Reported as counts per level, not a score, because averaging three levels hides the
  weakest link.
- **Coverage checked** — how many core fields rest on pages we could actually read. **This is the
  column that stops the dangerous failure.** Postman and Sentry both score 10/10; one of them was
  read and the other largely was not, and only this column says so. A brief whose coverage is
  short also carries a `SCORE OVERSTATES COVERAGE` flag naming every unread field.

**The score is not a comparative measure and the system says so in the brief itself, not only in
the audit trail.**

### What the tool could not read, stated as a number

**8 of 49 pages — 16.3%, across four of seven vendors — returned a URL and no document.** They
returned HTTP 200 and either JavaScript shells or empty bodies. Extraction succeeded on **84%** of
pages and populated **46 of 56 fields (82%)**.

**23 of those 56 results — 41% — need a human before anyone relies on them.** That is not a
failure figure. It is the figure that makes a first-pass research aid safe to use, and it is
printed on the vendor's own brief rather than buried here.

### Where manual review remains necessary — the brief's fourth question

1. **Any vendor with an unreadable primary page.** Where a field's home page could not be read and
   the answer came from elsewhere, a caveat is written into the brief a human reads, not just the
   log. **13 such caveats across four vendors — each one a page somebody must open by hand.**
2. **Any field evidenced only from outside its expected home.** The match is real; the finding is
   weak. On GitLab three of five core fields draw their best evidence from the privacy policy —
   which is authoritative and also the longest, best-punctuated document any vendor publishes. The
   rule as written rewards a good writer.
3. **Any vendor that scores well because nothing contradicted it.** Conflict detection returns
   **zero** on this corpus, and that is reported as a finding rather than presented as agreement.
   Absence of contradiction is not corroboration.
4. **Every vendor, on every export.** Each brief states in its own text that it is a first-pass
   internal research aid and that final review remains manual.

### How the defects were found — the method, not the tooling

**Fifty-five defects have been found in this project. The automated test suite caught one of
them.** The rest came from reading the output against the source page, from re-running the
workflow end to end, and — for the last four — from reading the client's brief line by line
instead of a summary of it. Every one of those four was on the client-facing surface and none was
in the engineering: a dropdown that changed nothing, a tab denying a working agent existed, an
export stripping its own disclaimer, and a config key advertising a feature never built.

**The code was more honest than the interface describing it.** For a tool whose entire purpose is
to stop unchecked claims reaching a reader, that inversion is the most useful thing this
evaluation has to report — and it is why the interface, not the documents, is where the honesty
guarantees are now enforced.

### Where to look next

§1 collection · §2 extraction and the cross-vendor table · §3 source-grounding · §4 manual review
in detail · §5 what actually found the defects · §6 the limits of this evaluation itself.

---

## 0. The finding this project exists to report

> **The dangerous failure is not a missing answer. It is a confident answer about a company that
> nobody checked.**

A missing field is visible. A reviewer sees the gap, opens the vendor's site, and fills it in.
A wrong field that arrives labelled *High confidence*, with a real quote and a working URL under
it, is invisible — it recruits the reviewer's trust and then spends it. Everything this prototype
does that is more complicated than "match a phrase and print it" exists to make that second
failure visible.

Five distinct mechanisms produced it on real pages, all measured against the frozen corpus —
**collected 13 August 2026 for five vendors, 19 August for GitLab and 22 August for JetBrains** —
the two whose seed URLs were corrected. Every figure in this document was re-verified by running
the workflow on 20 August, and JetBrains' 22 August re-collection reproduced every one of its
numbers unchanged, which is itself a result: the pipeline is deterministic, and the pages that
drift are not the ones this vendor publishes:

| Mechanism | Vendor | Measurement | What a naive tool would have reported |
|---|---|---|---|
| JavaScript rendering | Atlassian | product page: **52 readable characters and 0 heading blocks from 898,035 bytes** of HTML; pricing: 66 characters from 1,213,336 bytes | "No security information published" |
| A JavaScript shell behind a redirect | Postman | privacy policy: **0 readable characters from 4,727 bytes** | Privacy field FOUND / High, quoted from the *security* page, while the privacy policy itself was never read |
| An unguessable URL | JetBrains | the security page returned 404 six times — the curated seed plus all five URL patterns | "JetBrains publishes no security page", while JetBrains states *"SOC 2 Type II and GDPR compliance"* at `/legal/docs/privacy/trust-center/` |
| A quote that is technically correct and says nothing | GitHub | `security_trust` resolved to *"…the content of your Account and its security are up to you."* — a liability clause in the terms of service | A confident, sourced, entirely useless answer about GitHub's security posture |
| **A safeguard that was never wired up** | JetBrains | the caveat for "we never found this page at all" had **never fired once** since the day it was written; `skip` occurred zero times in seven audit trails | The workflow reporting a clean negative with a guard in place that could not run |

**A 200 means the URL exists. It does not mean it is the right page, and it does not mean the page
contains words. A 404 means our URL guess was wrong, not that the vendor is silent. A quote that
survives every automated check can still be the wrong sentence. And a safeguard nobody exercised
is a safeguard nobody has.**

All five are now closed. **A sixth was open until 19 August and belongs to Agent 3: a vendor
could still score 10/10 High while half its primary documents were never read.** It is closed by
defect 42. Verified on the shipped artifact rather than asserted: `data/briefs/postman_brief.json`
now reads `evidence_score` 10, `confidence_band` **Medium**, `coverage_verified` **2** of **5**,
and a `SCORE OVERSTATES COVERAGE` review flag naming all three unread fields by name — see §4.3.

---

## 1. Were sources collected correctly?

**Mostly yes, and the failures are the useful part.**

Seven vendors, one category (developer productivity tools), **49 public pages collected**, all
from official vendor domains. Collection policy: `robots.txt` read before every fetch using
RFC 9309 semantics, a 2-second delay per domain, an honest User-Agent, a hard cap of 10 pages and
20 requests per vendor, and every page cached on first fetch so nothing is fetched twice.

| Vendor | Pages | Page types resolved |
|---|---|---|
| GitHub | 8 | product, pricing, security, trust, privacy, docs, status, terms |
| Atlassian | 7 | product, pricing, security, privacy, docs, status, terms |
| GitLab | 7 | product, pricing, security, privacy, docs, status, terms |
| Linear | 7 | product, pricing, security, privacy, docs, status, terms |
| Postman | 7 | product, pricing, security, privacy, docs, status, terms |
| Sentry | 7 | product, pricing, security, privacy, docs, status, terms |
| JetBrains | 6 | product, pricing, security, privacy, docs, status — **`terms` never resolved** |

### 1.1 Eight of 49 pages returned a URL but not a document

An HTTP 200 with a valid cache entry is not evidence that anything was read. Agent 1 therefore
measures readability at collection time and records the verdict in the audit trail:

| Vendor | Page | Readable chars | HTML size | chars/KB | Caught by |
|---|---|---|---|---|---|
| Atlassian | product | 52 | 898,035 | 0.06 | floor + density |
| Atlassian | pricing | 66 | 1,213,336 | 0.06 | floor + density |
| JetBrains | pricing | 40 | 54,569 | 0.75 | floor + density |
| JetBrains | docs | 45 | 4,434 | **10.39** | **floor only** |
| JetBrains | status | 333 | 227,437 | 1.50 | floor + density |
| Linear | docs | 1,034 | 540,090 | **1.96** | **density only** |
| Postman | privacy | 0 | 4,727 | 0.00 | floor + density |
| Postman | docs | 2,370 | 1,234,954 | **1.97** | **density only** |

This table is the empirical argument for using **two orthogonal cheap tests instead of one clever
one**. The thresholds are a 600-character floor and a 2.0-readable-chars-per-kilobyte density
rule, and neither is sufficient alone:

- **JetBrains' `docs` page has a high density — 10.39 chars/KB — and would pass a density test
  comfortably. It contains 45 characters. Only the floor catches it.**
- **Postman's and Linear's `docs` pages clear the 600-character floor by 4× and 1.7×. At 1.97 and
  1.96 chars/KB they are ~98% JavaScript. Only the density rule catches them.**

Each rule catches a failure the other misses. A single test would have passed roughly half of
these pages as readable and then reported their missing fields as vendor silence.

*Note on the HTML size column: Agent 1 measures the length of the decoded HTML string — characters,
not bytes — and its audit trail calls them "bytes". On ASCII-dominant pages the difference is under
0.01% and none of the pass/fail decisions above change, but the label is wrong and is listed for
correction.*

The examples above replaced an earlier pair that had gone stale, which is a finding in its own
right and is picked up in §5.

### 1.2 Four defects in collection, and what each cost

- **A false `robots.txt` refusal dropped four of six sources and blamed the vendor.** Python's
  standard-library parser is stricter than RFC 9309. The refusal was returned as a bare boolean,
  so the reason was unavailable at the point of failure. Returning `(allowed, reason)` instead of
  `allowed` exposed it in one run. *A refusal must always carry its reason.*
- **URL patterns are guesses and must be recorded as such.** JetBrains' `terms` page still 404s on
  all three attempted patterns. That is written into the audit trail as three failed guesses, not
  as "JetBrains publishes no terms of service".
- **The mechanism that records those guesses only worked for pages that had a seed URL.** Agent 1
  emitted its "wanted but never found" step only for page types listed in `vendors.yaml` seeds.
  JetBrains' `terms` is reachable only through URL patterns, so it 404'd three times and was never
  reported missing at all. Because Agent 2's caveat is built from those steps, **the safeguard
  written for exactly this case had never executed on any vendor** — the step appears zero times
  across all seven audit trails. Found on 18 August by noticing an empty list where there should
  have been an entry. **A fix nobody exercised is a fix nobody verified.**
- **Vendor pages change between runs.** Linear's `docs` page moved from 24,444 bytes and 15
  readable characters to 540,090 bytes and 1,034 readable characters between 12 and 13 August (Linear's pages are dated 13 August and were deliberately frozen there — see the limitations). The
  local cache, not the live web, is the record of what was actually collected and evaluated.

---

## 2. Are the extracted fields useful?

**Useful, with limitations that are structural rather than incidental.**

Eight fields per vendor: security and trust, privacy and data handling, support and documentation,
integrations and API, pricing and availability, data residency, encryption, uptime and reliability.
Across seven vendors that is 56 field results, carrying **122 evidence blocks and 18 caveats**.

| Vendor | Score (core) | Confidence | **Coverage** | FOUND | PARTIAL | NOT_FOUND | Evidence | Caveats |
|---|---|---|---|---|---|---|---|---|
| GitHub | 10/10 | High | **5/5** | 7 | 0 | 1 | 20 | 0 |
| GitLab | 10/10 | High | **5/5** | 7 | 0 | 1 | 19 | 0 |
| Sentry | 10/10 | High | **5/5** | 7 | 1 | 0 | 21 | 0 |
| Postman | 10/10 | High | **2/5** | 8 | 0 | 0 | 21 | 4 |
| Atlassian | 10/10 | High | **2/5** | 6 | 0 | 2 | 17 | 5 |
| Linear | 6/10 | Medium | **3/5** | 4 | 2 | 2 | 16 | 4 |
| JetBrains | 5/10 | Medium | **2/5** | 4 | 0 | 4 | 8 | 5 |

*Coverage* = core fields whose evidence carries no tool-limitation caveat. It is printed beside
every score because the score alone cannot be compared between vendors — see §4.3.

### 2.0 Cross-vendor comparison

Requested by First Quadrant Labs in their written guidance of 13 August, on the grounds that it
*"demonstrates the effectiveness and limitations of the prototype more clearly than relying only on
screenshots"*. They are right: the table below says more about what this tool can and cannot do
than any single vendor's brief.

| Vendor | Source coverage | Extraction success | Inaccessible pages | Fields populated | Fields needing manual review | Core coverage |
|---|---|---|---|---|---|---|
| GitHub | 8 page types | **100%** | 0 | 7 of 8 | 1 | 5/5 |
| GitLab | 7 page types | **100%** | 0 | 7 of 8 | 1 | 5/5 |
| Sentry | 7 page types | **100%** | 0 | 8 of 8 | 1 | 5/5 |
| Linear | 7 page types | 86% | 1 | 6 of 8 | 6 | 3/5 |
| Atlassian | 7 page types | 71% | 2 | 6 of 8 | 5 | 2/5 |
| Postman | 7 page types | 71% | 2 | 8 of 8 | 4 | 2/5 |
| JetBrains | 6 page types (`terms` never resolved) | **50%** | 3 | 4 of 8 | 5 | 2/5 |
| **All seven** | **49 pages** | **84%** | **8 (16.3%)** | **46 of 56 (82%)** | **23 of 56 (41%)** | — |

Three things a reader should take from it:

- **Extraction success and field coverage are not the same measure.** Postman has the *worst* page
  accessibility tied with Atlassian at 71%, and yet populates all eight fields — because its
  security page is unusually rich and the extractor happily sourced answers from it while the
  privacy policy and documentation were unreadable. High field coverage on low page coverage is the
  signature of a vendor whose brief looks complete and is not.
- **41% of all field results need a human.** That is the honest headline for a first-pass research
  aid. It is not a failure figure; it is the figure that makes the tool safe to use.
- **JetBrains at 50% is the control case.** It is the vendor the tool handles worst and the one the
  evaluation needs most — see §4.4.

### 2.1 The evidence comes from the pricing page more than anywhere else

Counting where the 122 evidence blocks were actually found:

| Source page | Evidence blocks | Share |
|---|---|---|
| pricing | 38 | 31.1% |
| security | 34 | 27.9% |
| privacy | 29 | 23.8% |
| terms | 12 | 9.8% |
| status | 8 | 6.6% |
| product | 1 | 0.8% |
| **docs** | **0** | **0%** |
| **integrations** | **0** | **0%** |
| **trust** | **0** | **0%** |

Three uncomfortable results sit in that table.

**The pricing page is the single largest source of vendor due-diligence evidence.** Not the
security page, not the trust centre. Enterprise pricing tiers are feature-comparison tables, and
compliance certifications are sold as features — so "SOC 2 Type 2", "SAML single sign-on",
"FedRAMP", "SCIM" and "data residency" all appear there, in prose, in quantity. It is real evidence
and it belongs in the brief. It is also marketing copy, and a reviewer should know that is where
the answer came from. This is why `preferred_source_types` **orders** evidence rather than
filtering it, and why Agent 3 must flag a field whose evidence came only from outside its expected
home.

**The documentation pages contributed nothing at all.** Not one of 122 blocks. Partly because four
of seven `docs` pages are JavaScript shells, and partly because documentation is written in
task-oriented fragments rather than the declarative sentences the confidence rule rewards. For
due-diligence purposes, `docs` currently costs a fetch and returns nothing.

**GitHub's trust centre also contributed nothing**, despite being 7,684 readable characters and
the only trust-centre page in the corpus. Its compliance material is presented as linked resource
cards rather than sentences.

### 2.2 The status vocabulary had three values and only ever emitted two

Until 13 August, all 56 field results were either `FOUND` or `NOT_FOUND`. **`PARTIAL` had been
produced zero times.** The cause was not a rare condition — it was two docstrings that disagreed
about one rule. `agent2_extract.status_from_confidence` documented *"PARTIAL — Low, something
matched but only a heading, a logo, or a fragment"*; `parse.score_field_confidence` documented
*"Medium — named only in a heading … on an authoritative page"*, which then reports as FOUND.
The code implemented the second, so the state was unreachable.

Resolved in favour of PARTIAL: a heading with nothing written under it is a reason to go and look,
which is what PARTIAL means. Totals moved from **46 FOUND / 10 NOT_FOUND / 0 PARTIAL** to
**43 / 10 / 3**. The three are Linear's pricing field (`<h2>Pricing</h2>`, no paragraph), Linear's
data-residency field, and Sentry's data-residency field (`<h2>Data Residency</h2>`, no paragraph).

**Two docstrings describing one rule differently is how a codebase stops being auditable** — and
here the disagreement had quietly killed a whole status value while every test passed.

### 2.3 Ranking is a policy statement, and one policy was wrong

The strongest single defect found in the system, now fixed. GitHub's security field quoted a
disclaimer instead of a certification:

```
GitHub · security_trust · FOUND · High          [BEFORE]
value: "We offer tools such as two-factor authentication to help you maintain
        your Account's security, but the content of your Account and its
        security are up to you."
source: https://github.com/terms
```

The evidence ranked second was *"GitHub offers AICPA System and Organization Controls (SOC) 1
Type 2 and SOC 2 Type 2 reports with IAASB International Standards on Assurance Engagements,
ISAE 3000, and ISAE 3402."* The first matched one dictionary term (`two-factor`). The second
matched four. The first won because `terms` was listed among `security_trust`'s preferred source
types, and preferred-source is evaluated before term count.

**The ranking function was doing exactly what the configuration told it. The wrong thing was in
the dictionary.** A terms-of-service page is where a vendor *limits* its security obligations; it
is not where a vendor *states* its security posture.

Two related defects sat alongside it, both fixed:

- **A claim published as a bare heading became an evidence card with an empty quote.** GitHub's
  `/security` page carries `<h2>GitHub's API stays secure with ISO, SOC 2, and GDPR.</h2>` with no
  paragraph beneath it. The block model pairs a heading with its body; with an empty body the quote
  was empty, the match scored Medium rather than High, it ranked ninth of nine candidates and was
  discarded by the three-evidence cap. **The field's own highest-priority source page contributed
  nothing, and the most precise sentence GitHub publishes about its security never reached the
  brief.** The fix was to ask *"is this a complete sentence?"* rather than *"which HTML tag was it
  in?"* — in the quote, in the score, and in the ranking, because fixing only one of the three
  changed the number and not the output.
- **The headline quote was the first matching sentence, not the strongest.** JetBrains' security
  field displayed *"Please visit our Trust Center to learn more about JetBrains' security
  practices, compliance certifications, and data protection measures."* — matched on the
  navigational term `trust center`, asserting nothing. *"You can also find details on our SOC 2
  Type II and GDPR compliance…"* sat 340 characters further into the same quoted block. The value
  is now the sentence carrying the most matched terms.

After the fixes, all seven security fields quote a certification statement or an explicit
limitation, and five of seven quote it from the vendor's own security page.

### 2.4 A fix that looked right and was wrong

Worth recording because the reasoning was sound and the data still said no.

The first version of the bare-heading fix dropped any block whose heading was not a complete
sentence. Measured against the corpus, that turned **Linear's pricing** and **Sentry's data
residency** from a weak FOUND into a clean **NOT_FOUND** — a flat statement that Linear publishes
no pricing information, about a vendor whose pricing page we read successfully. Trading a poor
quote for a false negative is precisely the failure this project exists to prevent. The right
answer was neither FOUND nor NOT_FOUND but PARTIAL, which is how §2.2 came to be investigated.

**Measure a fix against real data before believing it. Reasoning is not verification.**

---

## 3. Are the summaries source-grounded?

**Yes, and this is the strongest property of the system — but "grounded" is a weaker guarantee
than it sounds, and the difference matters.**

There is no language model anywhere in this workflow. Every field's `value` is a sentence copied
character-for-character from a vendor page, selected rather than written. Nothing is paraphrased,
so nothing can drift from its source; the failure mode of a generated summary — fluent text with
no traceable origin — cannot occur here by construction.

Grounding was verified independently of the project's own checker, because a checker that passes
its own output proves nothing. Each figure below comes from re-extracting the readable text from
every cached HTML file and searching it directly:

- **122 evidence blocks carry matched terms. 0 cite a term that appears nowhere on the source
  page.** There are no fabricated citations.
- **0 evidence cards carry an empty quote.** Before the bare-heading fix, a card could be counted
  toward a field's confidence while displaying no text at all.
- **0 cards quote interface furniture.** *"There was an error while loading. Please reload this
  page."* — GitHub's placeholder for panels that fail to render — appeared inside four evidence
  cards. It is real page text, faithfully quoted, and it is not something the vendor is telling us.
  It also mattered for scoring: it is a 41-character complete sentence, and 40 characters is the
  threshold for High, so a page that failed to render could have earned High confidence on the
  strength of its own error message. Removing it needed a mechanism separate from the existing
  suppression list, because suppressing that block would also have discarded GitHub's SOC 2
  statement sitting inside it.
- **20 evidence cards still display at least one cited term that a reader cannot find in the
  quoted text.** All 42 such terms are genuinely on the page, but outside the 600-character snippet
  window. This is not fabrication; it is a presentation defect. A reviewer shown "matched: SOC 2,
  ISO 27001, PCI DSS, HIPAA" above a quote containing only "SOC 2" cannot verify the other three
  without leaving the brief. **Agent 3 should cite only the terms visible in the quote it prints
  and count the rest separately.**
- **9 of 122 blocks earn their confidence label from a sentence that does not contain the matched
  term.** Atlassian's security field is the clearest case: `hipaa` occurs only in the 39-character
  section title *"Sensitive Health Information and HIPAA."*, while the High was earned by a
  322-character sentence about something else in the same terms-of-service section. This is
  **deliberately not fixed**: the obvious tightening would also demote Sentry's *"High
  Availability"* heading with a full paragraph beneath it and GitLab's *"Trust Center Documents"*,
  because vendors do not repeat a heading inside its own paragraph. Whether a block coheres is a
  judgement, not a rule. All nine are flagged for human review by `verify_corpus`.

The honest summary: **the system cannot invent a claim, but it can quote the wrong one, annotate it
with terms the reader cannot see, or score it on a neighbouring sentence.** Source-grounding
removes an entire class of failure. It does not remove judgement.

### 3.1 The replay reconciles — every artifact in this archive is what the frozen cache produces

Grounding says where a sentence came from. Reproducibility says whether anyone can obtain the same
sentence again. They are separate claims, checked differently, and until 23 August only the first
had been demonstrated as a before-and-after.

On 23 August, after a change under `src/`, the whole offline chain was re-run against the frozen
cache — `run_workflow.py --mode replay`, then `verify_corpus.py`, then `export_all.py` — and the
output compared with the artifacts already committed:

- **7 of 7 vendors replayed with no network request made.** Agent 1 loaded every page from the
  cache; the preflight confirmed each readable page was present, so Agent 2 re-read all of them.
- **28 artifact files changed, and every changed byte was a timestamp** — `generated_on` and
  `ran_on`. Not one field value, confidence label, evidence quote, score, coverage figure or review
  flag moved.
- **`verify_corpus.py`: 0 FAIL across all seven vendors**, with the same 55 WARN rows ledgered in
  §4.5 — 11 Atlassian, 5 GitHub, 6 GitLab, 9 JetBrains, 5 Linear, 11 Postman, 8 Sentry.
- Every headline figure in this document survived unchanged: Postman 10/10 on evidence with
  coverage 2 of 5, JetBrains 5/10 with 4 NOT_FOUND, Atlassian 6 of 8 fields from 5 readable pages,
  GitHub, GitLab and Sentry at 5 of 5 coverage.

**A reviewer cannot repeat that comparison from this archive alone**, because the HTML cache is
excluded at the client's instruction of 18 August. What the archive does carry is
`data/exports/source_manifest.csv` — all 54 attempts, their outcomes, and a SHA-256 of each page's
content — so the pages behind these quotes can be identified and re-collected. The README's
*Re-collecting the public sources* section is the route back, and `docs/assumptions_limitations.md`
states plainly that the vendors' live pages have moved since the corpus was frozen.

---

## 4. Where does manual review remain necessary?

Everywhere, by design — this is a first-pass research aid and every export says so. But four
places need it specifically and predictably, and **§4.5 counts the resulting workload rather than
describing it**.

### 4.1 Any vendor with an unreadable primary page

Eight pages across four vendors returned a URL and no document. Where a field's own home page was
unreadable and the answer came from somewhere else, a caveat is injected into that field's
evidence list — into the brief itself, not just the audit trail, because a reviewer reads the
brief. **Thirteen such caveats exist, across four of the seven vendors — Postman 4, JetBrains 4,
Atlassian 3, Linear 2; GitHub, GitLab and Sentry carry none. Every one is a page a human must open
by hand.** Counted on 20 August from `data/briefs/*.json`, not from an earlier note: an earlier
draft of this section said eighteen, a figure that stopped being true when the seed corrections
changed what JetBrains and GitLab could read.

### 4.2 Any field whose evidence came only from outside its expected home

The match is real; the finding is weak. On GitLab, three of five core fields draw their strongest
evidence from the **privacy policy** — which is authoritative, and also happens to be the longest,
best-punctuated document any vendor publishes. This is the sharpest limitation of the confidence
rule as written: **it rewards a vendor with a well-written privacy policy.** A short, precise,
factual sentence competes badly against a long, vague, well-formed one.

Linear is the clearest case of the same effect from the other direction. Its security page
publishes `<h2>SOC 2 compliance</h2>` with an empty body — the detail is JavaScript-rendered — so
its security field falls back to a pricing-tier feature list naming SAML and SCIM, and scores
Medium. The sentence a reviewer would want is on the page; we cannot read it.

### 4.3 Vendors that score well because nothing contradicted them

This was the most important open defect in the system, and the thing Agent 3 was built to fix.
The table shows what the same two vendors looked like before and after that fix.

| | Postman | Sentry |
|---|---|---|
| Evidence found | **10/10** | **10/10** |
| Confidence — *as reported until 19 Aug* | ~~**High**~~ | ~~**High**~~ |
| Confidence — *as reported now* | **Medium** — 0 of 5 core fields High | **Medium** — 2 of 5 core fields High |
| **Coverage checked** | **2 of 5** | **5 of 5** |
| Fields carrying caveats | **4** | **0** |
| `SCORE OVERSTATES COVERAGE` flag | **raised** | not raised |
| Privacy policy | **0 readable characters** | fully readable |
| Docs page | **2,370 chars from 1.2 MB (98% JavaScript)** | fully readable |

The two rows that changed are the point. Coverage and the flag were always computable; until
19 August neither reached the reader.

**Until 19 August, Postman and Sentry received identical scores and identical confidence labels.
One of them was read. The other largely was not.** The score counts what was found; it cannot
count what was never looked at. Presented to an operations lead without the caveats visible, the
two vendors were indistinguishable — precisely the failure named at the top of this document,
reproduced by the system's own scoring. Atlassian is the same shape: 10/10 on 2 of 5.

**Closed 19 August by defect 42, and the fix is a reporting change rather than a scoring change.**
Three measures now carry three names and travel together: `evidence_score` (what was found),
`confidence_band` with per-level counts (how good it is, on the client's definition), and
`coverage_verified` / `coverage_total` (how much could be checked). No exporter, template or UI
panel can render the score without them. Postman's shipped brief now reads 10/10 evidence,
**Medium** confidence with **0** core fields High, coverage **2 of 5**, and a `SCORE OVERSTATES
COVERAGE` flag naming `integrations_api`, `privacy_data_handling` and `support_documentation`.
Sentry reads 10/10, Medium, **5 of 5**, no such flag. The two are now distinguishable at a glance.

The calculation lives in `src/review_rules.py` and is **imported** by both `agent3_review.py` and
`tools/verify_corpus.py`, because a build-time checker and a shipped brief computing coverage
separately is how the two begin to disagree — the mechanism behind four earlier defects.
**The vendor score is still not a comparative measure on its own, and the brief now says so in
its own text.**

### 4.4 The case for keeping JetBrains

It fails worst — 5/10, four fields NOT_FOUND, three pages unreadable, one page type never resolved
after three attempts. It is also the single best piece of evidence this evaluation has for the
brief's own question, *where does manual review remain necessary?* Swapping it for a tidier reserve
vendor would have improved every number in this document and destroyed its point.

### 4.5 The warning ledger — manual review, counted

`tools/verify_corpus.py` raises **0 FAIL and 55 WARN** across the seven vendors (run 20 August
2026). A FAIL is our bug. **A WARN is usually a real finding about the vendor, and the ledger below
is the manual-review workload this prototype hands to a human, stated as a number rather than as a
promise.**

| Warning | Count | What it means for a reviewer |
|---|---|---|
| `off-home-evidence` | 21 | The field was answered, but never from its own expected page. The match is real; the finding is weak |
| `unread-home-page` | 10 | The field's home page could not be read, so the answer came from elsewhere. A caveat is already in the brief |
| `claim-not-in-matched-sentence` | 9 | **The label was earned by a longer sentence than the one actually containing the matched term.** Worst case: JetBrains `privacy_data_handling`, where the longest sentence containing `gdpr`, `personal data` or `data subject` is **5 characters** |
| `unusable-page` | 8 | Collected, HTTP 200, and no readable document. The 16.3% |
| `thin-text` | 3 | The stored text is under half the readable text. Evidence is safe — Agent 2 reads raw HTML — but the corpus reads poorly for a human |
| `score-without-coverage` | 2 | Postman and Atlassian: 10/10 evidence on 2 of 5 core fields verified |
| `not-collected` | 1 | JetBrains `terms`, never located after six attempts |
| `gated-evidence` | 1 | Sentry's security evidence is *"available to customers"* — the claim cannot be closed from public sources at all |
| **Total** | **55** | Across 7 vendors: Atlassian 11, Postman 11, JetBrains 9, Sentry 8, GitLab 6, GitHub 5, Linear 5 |

**`claim-not-in-matched-sentence` is the one to read first.** It fires on **six of seven vendors**
and it is the residue of the confidence rule the client pushed back on: even after scoring moved
from sentence length to the client's definition, a block can still match on one term and be scored
on a different, longer sentence beside it. The checker reports it rather than silently correcting
it, because the correct action is a human reading the quote — which is printed next to the label
in every brief, for exactly this reason.

**A warning nobody reads is a defect nobody fixes.** Defect 42 sat in this output for days as
`score-without-coverage`, printed on every run, before anyone treated it as a finding.

---

## 5. What found the defects

**Fifty-five defects have been found in this project. The automated test suite caught one, and reported one more that was a defect in itself.**

The other fifty-three were found by opening the artifact and reading what it actually said — the
screen first, then the JSON, then the raw HTML. The 154 offline tests are worth having: they hold
fixed behaviour still while it is changed. But they test what was already understood, and every
defect that mattered was a gap between what the code was believed to do and what the vendor pages
actually contained.

Four that illustrate the pattern:

- `sla` matched **"Slack" eleven times out of thirteen**, and `cli` matched *click*, *client* and
  *decline* nine times out of nine. A substring is not a word.
- `SLA` inside *"a deadline based on an internal Service Level Agreement (SLA) for fixing
  vulnerabilities"* — a vulnerability-remediation commitment — scored High confidence for **uptime
  reliability**. A string match is not a meaning.
- **A test asserted the defect.** The test guarding "every missing page type must be reported"
  asserted `len(skipped) == len(seeds)` — a condition only the buggy seeds-only implementation
  satisfies. The correct fix made it fail. *A test that encodes a bug converts a defect into a
  guarantee and makes the next person's correct fix look like a regression.*
- **Documentation decays against data, not just against code.** The worked examples justifying the
  two-test readability rule claimed Postman's privacy page had "high density (27 chars/KB)" — it is
  0.00 — and that JetBrains' status page "clears any sane floor" — it is 333 characters. Both are
  caught by both tests, so neither example demonstrated anything. Separately, three of the six
  worked examples in `docs/confidence_rules.md` had gone stale the same way: the Linear row quoted
  a SOC 2 sentence that appears nowhere in the current corpus. **Check the code against its
  documentation, and the documentation against the current data.**

### 5.1 The last eight defects, and what each one was hiding behind

Defects 40–47 were found after the code was believed finished. **None came from the test suite; 134
tests were passing throughout defect 40.** They are grouped by what found them, because the method
is the transferable part.

**Found by running the deliverable in the shape it ships (defect 40).** With `data/cache/html/`
deleted — the exact configuration the client asked for on 18 August — every brief reported
*"NOT_FOUND — nothing matched on any page we could read"* under all eight fields of all seven
vendors, about pages nobody had opened. Coverage read **5/5 verified** while zero pages were read,
because "verified" means "not caveated" and an empty field has nothing to caveat. Agent 3 raised
zero flags. **The archive we were about to submit made the tool lie confidently, and every test
passed.** Fixed in three layers: `uncached` is now tracked separately from `unusable` (one is a
fact about the vendor's site, the other about our archive), a caveat is injected where the reviewer
reads rather than into the log, and the orchestrator refuses replay outright and names the mode
that works.

**Found by one rule living in three places (defect 41).** A single over-hedging rule had three
implementations and two were stale, so one brief said *"its own pages read cleanly, this is a
finding about the vendor"* **and** *"this may be our limit, not the vendor's silence"* about the
same field. Fired on eight fields across three vendors. All three now import
`review_rules.unread_home_page`.

**Found by reading a warning the tool had printed for days (defect 42).** The vendor header said
*Confidence* and measured sentence length. Postman and Sentry both read 10/10 High on coverage 2/5
and 5/5 — see §4.3. `verify_corpus` had been printing *"Agent 3 owes a coverage-aware score here"*
on every run. **A warning nobody reads is a defect nobody fixes.**

**Found by re-deriving a stale document against live data (defect 43).** A field could earn High on
evidence the reader never sees: Linear's `security_trust` ranked the *pricing* page first and its
reason read *"stated directly on the vendor's own pricing page"* — for a security field. High now
requires the printed quote to be on the field's own page. *Re-deriving a stale worked example is
not housekeeping; it is a defect-finding technique.*

**Found by reading the brief itself, line by line (defects 44–47).** Every compliance check before
19 August was made against a *summary* of the brief. Reading the PDF found four unmet requirements,
and **all four were on the client-facing surface while the engineering underneath audited clean**:

| # | What a reviewer would have seen |
|---|---|
| **44** | The research-category filter — one of the brief's three named inputs — was rendered and its return value discarded, for nine days, under help text promising the opposite. **A dead control is worse than a missing feature: a missing feature is visible.** |
| **45** | The agent-steps tab printed *"not built yet"* under Agent 3 while Agent 3's output was being rendered in two other tabs. Never hardcode a state you are also computing. |
| **46** | The CSV export was the one format carrying no disclaimer, no review flags and none of the three vendor numbers — a clean table of security claims about seven real companies with every caveat stripped, in the format most likely to be pasted into an email and read alone. |
| **47** | `config/settings.yaml` advertised an `llm` backend that no code reads. A dead config key in the file a reviewer opens to learn what the system does. |

**The pattern is the finding.** Four gaps, all on the surface a non-technical reviewer touches,
none in the collection or extraction layers. **The code was more honest than the interface
describing it** — the exact inversion of what this project spent twelve days warning about,
committed by the project itself.

### 5.2 The last six came from looking at the screen, and one from cloning the repository

Defects **48–53**, found on 22 August, after the code was finished, the documents were written and
the suite was green. **All six were on the surface a reviewer touches. None was in the engineering,
and all 152 tests passed throughout.**

| # | What a reviewer would have seen |
|---|---|
| **48** | Three JetBrains fields printed the heading *"Quoted from the vendor's page:"* above an **empty blockquote**, because the renderer treated a collection caveat as evidence. The table beside them read *Evidence: 1* on fields with none. **An empty quote presented as a vendor claim is the defect this whole document is about, produced by our own interface, on the vendor §4.4 calls the control case.** |
| **49** | The status sentinel `NOT_FOUND` was printed as a **confidence level** in four different renderers. The brief names three levels; this silently offered a fourth. |
| **50** | An internal sampling label — `Difficulty tier: hard` — sat unexplained beneath a vendor's name, where it reads as a judgement about the company. The brief's scope boundaries forbid assigning vendor risk scores. |
| **51** | *Key sources* listed 3 readable pages under a bare heading, with 6 collected and 10 attempted, so a short list read as *the vendor publishes little* rather than *we could read little*. |
| **52** | **Tab 3 and tab 4 disagreed about confidence on 26 field/vendor pairs, across all seven vendors** — Agent 2 saying High where Agent 3, applying defect 43's rule, had already downgraded to Medium. Every export used Agent 3's value, so the deliverable was correct and only the screen was wrong. A reviewer reading the earlier tab wrote down a rating the system had rejected. |
| **53** | In a **fresh clone of the submitted archive** — no HTML cache, exactly as instructed on 18 August — `verify_corpus.py` printed 49 FAIL rows and **"DO NOT COMMIT: 7 vendor(s) failed."** The checker told a reviewer following our own README that the deliverable was broken while it behaved exactly as specified. |

**Defect 53 is defect 40 wearing different clothes.** Both are the shape of the submitted archive
making a tool say something false; the orchestrator had already been taught to refuse gracefully
and explain itself, and the checker had not. **A fix applied to one of two tools that answer the
same question is half a fix**, and nothing in this project catches that except running the
deliverable in the shape it ships — which is what found both.

**Defect 52 is the one worth keeping.** The fix does not hide the disagreement; it prints both
numbers side by side and says the right-hand one is the reviewed value. The client asked on
18 August that Agent 3 identify weak evidence. That request is now visible on screen as it happens,
instead of being asserted in a document.

**Why the suite could not have caught any of them.** Every UI test asserts what the app hands to
Streamlit, and every export test writes to a temporary directory. Neither can see a heading above
an empty quote, a sentinel printed where a rating belongs, or a checker's verdict in a directory
that does not exist on the machine running the tests. **This is the strongest available evidence
for §5's opening sentence**: the tests hold behaviour still, and reading the output is what finds
defects.

### 5.3 Two more came from running the suite on a clone, and one of them was in the suite

Defects **54–55**, found on 23 August by doing what found defect 53: cloning the repository and
running it. `pytest -q` in the clone reported **1 failed, 151 passed**.

| # | What the clone showed |
|---|---|
| **54** | `test_gitlab_security_field_quotes_the_soc_2_sentence` failed with `assert 'NOT_FOUND' == 'High'`. Agent 2 was right and the test was wrong. It skipped itself on `data/corpus/gitlab.json.exists()` — but the corpus **index** is committed while the HTML pages it names deliberately are not, so on any clone the guard was true, the replay ran with nothing to replay, and the suite reported the archive's intended shape as a failure. **This is defect 53 in a third costume.** After `run_workflow --mode replay` and `verify_corpus.py`, the test suite was the third check we own that could not tell *excluded by instruction* from *broken*. |
| **55** | Found while fixing 54, and worse than it. `resolve_html_path` trusted `Path(raw_html_path).is_file()` before anything else. Since paths became repo-relative (defect 16), that branch resolves against the **process's working directory** rather than the repository it was handed — so a run whose working directory holds a cache can read that cache while reporting it as a different tree's. It surfaced because a simulated cacheless clone reported its pages as *present*: the simulation was running from inside the real repository. **A silent wrong answer, with no `missing-html` step and no caveat to show it happened** — the failure this project exists to report, committed by the tool's own path resolution. |

**Both fixes are pinned by tests that run without the cache.** The GitLab assertion was restated on
three committed fixtures, where a status board and a pricing tier compete with the security page
and lose; the path rule is pinned by a test that builds two trees, puts the same content-addressed
filename in both caches and runs from the wrong one. `pytest -q` now reports **154 passed** where
the cache exists and **153 passed, 1 skipped** on a clone — TC-34 and TC-35 in `docs/test_cases.md`.

**Defects 53, 54 and 55 are one pattern, not three.** Every check this project owns was written on
the machine that holds the HTML cache, and each behaved differently on the archive a reviewer
actually receives. The remedy is not more tests. It is running the ones that exist somewhere else
before believing them.

### 5.4 Checking is the job, and most candidate findings do not survive it

The same discipline was applied to this document. Seven candidate findings were investigated while
writing and revising it; **four were wrong** — a set of apparent orphan citations that turned out
to be snippet truncation, two pages that appeared misclassified until the recomputation itself was
found to be at fault, a JetBrains extraction that appeared to have missed SOC 2 entirely when the
truncation was in the diagnostic rather than the code, and a proposed scoring tightening that would
have demoted three well-evidenced fields. Reporting any of them would have sent a day of work at a
defect that did not exist.

**A final adversarial pass on 22 August took two briefs — JetBrains, the worst-served vendor, and
Sentry, the best — and re-checked every printed claim against the cached page it cites.** Four
things were tested mechanically: that a cache file exists for every cited URL, that the printed
quote appears verbatim on the page it names, that every cited term is present on that page, and
that the brief's `source_type` matches the source manifest.

**Every check passed.** Zero missing cache files, zero quotes that could not be located on the page
they cite, zero orphan citations, zero source-type mismatches. **Fourteen candidate findings were
raised during that pass and all fourteen were false** — twelve were terms sitting just outside a
truncated display excerpt but present on the page, and two were artifacts of the checker's own text
normalisation on a pricing table. That makes it the sixth time in this project that a plausible
finding has failed on checking, and the ratio is the point: **the discipline that produced the
fifty-five real defects is the same one that keeps the false ones out of the document.**

---

## 6. Honest limitations of this evaluation

- **Agent 3 was built on 18 August, after this document was written.** Every statement here about brief assembly, review flags and
  scoring describes Agent 2's output and `tools/verify_corpus.py`, not the finished workflow. Its
  scope was fixed in writing by First Quadrant Labs on 13 August — verify evidence coverage,
  identify missing categories, highlight conflicts or weak evidence, prepare the final brief.
- **No conflict detection.** Nothing in the workflow notices when two official pages disagree with
  each other; each field's evidence is ranked, not cross-checked. The client asked for this in
  Agent 3, and until it exists a contradiction between, say, a status page and a pricing-tier SLA
  would be reported as two independent pieces of supporting evidence.
- **Seven vendors in one category is not a sample.** These findings describe developer-productivity
  vendors' public pages in August 2026 and should not be generalised further.
- **The corpus is a snapshot.** Vendor pages changed measurably between two consecutive days of
  this project. Re-running collection on a later date will produce different numbers, and the
  cached HTML rather than the live web is the record of what was evaluated.
- **No JavaScript rendering.** This is a scope decision **confirmed in writing by First Quadrant
  Labs on 13 August** — *"You are not required to introduce Playwright, Selenium, or another
  headless-browser layer"* — not a claim that rendering is unnecessary. Its cost is measured in
  §1.1 and reported rather than hidden: **8 of 49 pages, 16.3%**, across four of seven vendors.
- **The confidence rule is scheduled to change.** The client asked that confidence not rest
  primarily on sentence length, and supplied a definition built on directness and source authority
  instead. Their definition is semantic and cannot be evaluated by a rule-based system without a
  language model, so it will be implemented as two axes — *extraction quality* (the current
  sentence-based measure, renamed to what it actually measures) and *confidence* (source authority,
  term present in the printed quote, no caveat). It lands with Agent 3. **Every confidence figure
  in this document describes the single-axis rule as it stands today**, and the two-axis change
  will close the coverage-blind scoring described in §4.3.
- **The submitted archive will not contain the HTML cache.** On the client's instruction, the
  22 MB of verbatim third-party pages stays local; the submission carries the structured corpus, the
  evidence snippets, the collection code and a source manifest. **A fresh clone therefore cannot
  replay offline until a reviewer re-collects the sources**, and the README explains how. That is a
  consequence of a client instruction, not an oversight — the offline replay capability itself is
  intact and demonstrated in the walkthrough.
- **Three defects are open and deliberately unfixed** — the terms cited outside the visible quote
  (§3), the label earned by a neighbouring sentence (§3), and the coverage-blind score (§4.3).
  Each is recorded with the reason it was not fixed. Fixing the first two by tuning thresholds
  would over-fit the rules to individual vendors; the third is Agent 3's by design.
- **The figures in this document were produced in a Linux container** with the repository, the
  corpus and all 55 cached pages copied into it, because the development machine's assistant bridge
  has neither `pytest` nor network access. They must be reproduced on the Windows development
  machine before submission.
