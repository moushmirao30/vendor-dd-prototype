# Evaluation Summary

**Vendor Due-Diligence Research Workflow Prototype — First Quadrant Labs**
Moushmi Rao · draft of 13 August 2026 · **status: Agents 1 and 2 complete, Agent 3 not built**

This document answers the four questions the project brief asks of the evaluation summary:
whether sources were collected correctly, whether the extracted fields are useful, whether the
summaries are source-grounded, and where manual review is still required.

Every number below was produced by running the workflow over seven real vendors and reading the
artifacts it wrote. Nothing here is estimated. Where a claim could not be verified, it says so.

---

## 0. The finding this project exists to report

> **The dangerous failure is not a missing answer. It is a confident answer about a company that
> nobody checked.**

A missing field is visible. A reviewer sees the gap, opens the vendor's site, and fills it in.
A wrong field that arrives labelled *High confidence*, with a real quote and a working URL under
it, is invisible — it recruits the reviewer's trust and then spends it. Everything this prototype
does that is more complicated than "match a phrase and print it" exists to make that second
failure visible.

Four distinct mechanisms produced it on real pages, all measured:

| Mechanism | Vendor | Measurement | What a naive tool would have reported |
|---|---|---|---|
| JavaScript rendering | Atlassian | product page: **52 readable characters and 0 heading blocks from 898,035 bytes** of HTML; pricing: 66 characters from 1,213,336 bytes | "No security information published" |
| A JavaScript shell behind a redirect | Postman | privacy policy: **0 readable characters from 4,727 bytes** | Privacy field FOUND / High, quoted from the *security* page, while the privacy policy itself was never read |
| An unguessable URL | JetBrains | the security page returned 404 six times — the curated seed plus all five URL patterns | "JetBrains publishes no security page", while JetBrains states *"SOC 2 Type II and GDPR compliance"* at `/legal/docs/privacy/trust-center/` |
| A quote that is technically correct and says nothing | GitHub | `security_trust` resolves to *"…the content of your Account and its security are up to you."* — a liability clause in the terms of service | A confident, sourced, entirely useless answer about GitHub's security posture |

**A 200 means the URL exists. It does not mean it is the right page, and it does not mean the page
contains words. A 404 means our URL guess was wrong, not that the vendor is silent. And a quote
that survives every automated check can still be the wrong sentence.**

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

| Vendor | Page | Readable chars | HTML bytes | chars/KB | Caught by |
|---|---|---|---|---|---|
| Atlassian | product | 52 | 898,035 | 0.1 | floor + density |
| Atlassian | pricing | 66 | 1,213,336 | 0.1 | floor + density |
| JetBrains | pricing | 40 | 54,569 | 0.8 | floor + density |
| JetBrains | docs | 45 | 4,434 | **10.4** | **floor only** |
| JetBrains | status | 333 | 227,437 | 1.5 | floor + density |
| Linear | docs | 1,034 | 540,090 | **1.96** | **density only** |
| Postman | privacy | 0 | 4,727 | 0.0 | floor + density |
| Postman | docs | 2,370 | 1,234,954 | **1.96** | **density only** |

This table is the empirical argument for using **two orthogonal cheap tests instead of one clever
one**. The thresholds are a 600-character floor and a 2.0-readable-chars-per-kilobyte density
rule, and neither is sufficient alone:

- **JetBrains' `docs` page has a high density — 10.4 chars/KB — and would pass a density test
  comfortably. It contains 45 characters. Only the floor catches it.**
- **Postman's and Linear's `docs` pages clear the 600-character floor by 1.7× and 4×. At 1.96
  chars/KB they are 98% JavaScript. Only the density rule catches them.**

Each rule catches a failure the other misses. A single test would have passed roughly half of
these pages as readable and then reported their missing fields as vendor silence.

### 1.2 Three defects in collection, and what each cost

- **A false `robots.txt` refusal dropped four of six sources and blamed the vendor.** Python's
  standard-library parser is stricter than RFC 9309. The refusal was returned as a bare boolean,
  so the reason was unavailable at the point of failure. Returning `(allowed, reason)` instead of
  `allowed` exposed it in one run. *A refusal must always carry its reason.*
- **URL patterns are guesses and must be recorded as such.** JetBrains' `terms` page still 404s on
  all three attempted patterns. That is written into the audit trail as three failed guesses, not
  as "JetBrains publishes no terms of service".
- **Vendor pages change between runs.** Linear's `docs` page moved from 24,444 bytes and 15
  readable characters to 540,090 bytes and 1,034 readable characters between 12 and 13 August. The
  local cache, not the live web, is the record of what was actually collected and evaluated.

---

## 2. Are the extracted fields useful?

**Useful, with two limitations that are structural rather than incidental.**

Eight fields per vendor: security and trust, privacy and data handling, support and documentation,
integrations and API, pricing and availability, data residency, encryption, uptime and reliability.
Across seven vendors that is 56 field results, carrying **122 evidence blocks and 18 caveats**.

| Vendor | Score (core fields) | Confidence | FOUND | NOT_FOUND | Evidence | Caveats |
|---|---|---|---|---|---|---|
| Atlassian | 10/10 | High | 6 | 2 | 17 | 5 |
| GitHub | 10/10 | High | 7 | 1 | 20 | 0 |
| GitLab | 10/10 | High | 7 | 1 | 19 | 0 |
| Postman | 10/10 | High | 8 | 0 | 21 | 4 |
| Sentry | 10/10 | High | 8 | 0 | 21 | 0 |
| Linear | 7/10 | Medium | 6 | 2 | 16 | 4 |
| JetBrains | 5/10 | Medium | 4 | 4 | 8 | 5 |

### 2.1 The evidence comes from the pricing page more than anywhere else

Counting where the 122 evidence blocks were actually found:

| Source page | Evidence blocks | Share |
|---|---|---|
| pricing | 38 | 31% |
| security | 33 | 27% |
| privacy | 29 | 24% |
| terms | 13 | 11% |
| status | 8 | 7% |
| product | 1 | 1% |
| **docs** | **0** | **0%** |
| **integrations** | **0** | **0%** |
| **trust** | **0** | **0%** |

Two uncomfortable results sit in that table.

**The pricing page is the single largest source of vendor due-diligence evidence.** Not the
security page, not the trust centre. Enterprise pricing tiers are feature-comparison tables, and
compliance certifications are sold as features — so "SOC 2 Type 2", "SAML single sign-on",
"FedRAMP", "SCIM", "data residency" all appear there, in prose, in quantity. It is real evidence
and it belongs in the brief. It is also marketing copy, and a reviewer should know that is where
the answer came from. This is why `preferred_source_types` **orders** evidence rather than
filtering it, and why Agent 3 must flag a field whose evidence came only from outside its
expected home.

**The documentation pages contributed nothing at all.** Not one of 122 blocks. Partly because
four of seven `docs` pages are JavaScript shells, and partly because documentation is written in
task-oriented fragments rather than the declarative sentences the confidence rule rewards.
For due-diligence purposes, `docs` is currently a page type that costs a fetch and returns
nothing — a finding worth acting on rather than hiding.

### 2.2 The status vocabulary has three values and only ever emits two

All 56 field results are either `FOUND` (46) or `NOT_FOUND` (10). **`PARTIAL` was produced zero
times.** Either the middle case does not occur in practice, or the condition that would produce it
is unreachable. This has not yet been traced, and it should be before submission — an unused
branch in a status vocabulary is a defect until proven otherwise. *(Unverified; recorded rather
than explained.)*

### 2.3 Ranking is a policy statement, and one policy is currently wrong

The strongest single defect open in the system: **GitHub's security field quotes a disclaimer
instead of a certification.**

```
GitHub · security_trust · FOUND · High
value: "We offer tools such as two-factor authentication to help you maintain
        your Account's security, but the content of your Account and its
        security are up to you."
source: https://github.com/terms
```

The evidence ranked second was:

```
"GitHub offers AICPA System and Organization Controls (SOC) 1 Type 2 and
 SOC 2 Type 2 reports with IAASB International Standards on Assurance
 Engagements, ISAE 3000, and ISAE 3402."
```

The first matched one dictionary term (`two-factor`). The second matched four. The first won
because `terms` is listed among `security_trust`'s preferred source types and the preferred-source
tie-break is evaluated before the term-count tie-break. The ranking function did exactly what the
configuration told it to; **the wrong thing was in the dictionary, not the code.** A terms-of-
service page is where a vendor *limits* its security obligations. It is not where a vendor
*states* its security posture, and it should not be a preferred home for that field.

Two related defects sit alongside it:

- **A claim published as a bare heading becomes evidence with an empty quote.** GitHub's
  `/security` page carries `<h2>GitHub's API stays secure with ISO, SOC 2, and GDPR.</h2>` with no
  paragraph beneath it. The block model pairs a heading with its body; with an empty body the
  match is classified `heading_only`, scores Medium instead of High, ranks ninth of nine
  candidates, and is discarded by the three-evidence cap. **The field's own highest-priority
  source page contributed nothing, and the most precise sentence GitHub publishes about its
  security never reaches the brief.**
- **The field's headline quote is the first matching sentence, not the strongest one.** JetBrains'
  security field displays *"Please visit our Trust Center to learn more about JetBrains' security
  practices, compliance certifications, and data protection measures."* That sentence matched on
  the navigational term `trust center` and asserts nothing. The sentence *"You can also find
  details on our SOC 2 Type II and GDPR compliance…"* is 340 characters further into the same
  quoted block and is never promoted to the headline.

All three are fixable and none required new machinery to find. They required opening the output
and reading it.

---

## 3. Are the summaries source-grounded?

**Yes, and this is the strongest property of the system — but "grounded" is a weaker guarantee
than it sounds, and the difference matters.**

There is no language model anywhere in this workflow. Every field's `value` is a sentence copied
character-for-character from a vendor page, selected rather than written. Nothing is paraphrased,
so nothing can drift from its source; the failure mode of a generated summary — fluent text with
no traceable origin — cannot occur here by construction.

Grounding was verified independently of the project's own checker, because a checker that passes
its own output proves nothing:

- **122 evidence blocks carry matched terms. 0 cite a term that appears nowhere on the source
  page.** There are no fabricated citations. This was checked by re-extracting the readable text
  from each cached HTML file and searching it for every cited term, rather than by trusting the
  extraction's own record.
- **20 evidence cards display at least one cited term that a reader cannot find in the quoted
  text.** All 42 such terms are genuinely on the page, but outside the 600-character snippet
  window. This is not a fabrication; it is a presentation defect. A reviewer shown "matched:
  SOC 2, ISO 27001, PCI DSS, HIPAA" above a quote containing only "SOC 2" cannot verify the other
  three without leaving the brief. **Agent 3 should cite only the terms visible in the quote it
  prints, and count the rest separately.**
- **Loader error text is currently quoted as vendor evidence.** *"There was an error while loading.
  Please reload this page ."* appears inside four of GitHub's evidence snippets, captured from the
  pricing page. It is real page text, faithfully quoted — and it is noise presented to a reviewer
  as due-diligence material.

The honest summary: **the system cannot invent a claim, but it can quote the wrong one, quote it
with unverifiable annotations, or quote page furniture.** Source-grounding removes an entire class
of failure. It does not remove judgement.

---

## 4. Where does manual review remain necessary?

Everywhere, by design — this is a first-pass research aid and every export says so. But three
places need it specifically and predictably.

### 4.1 Any vendor with an unreadable primary page

Eight pages across four vendors returned a URL and no document. Where a field's own home page was
unreadable and the answer came from somewhere else, a caveat is injected into that field's
evidence list — into the brief itself, not just the audit trail, because a reviewer reads the
brief. Eighteen such caveats exist across the seven vendors. **Every one of them is a page a human
must open by hand.**

### 4.2 Any field whose evidence came only from outside its expected home

The match is real; the finding is weak. On GitLab, three of five core fields draw their strongest
evidence from the **privacy policy** — which is authoritative, and also happens to be the longest,
best-punctuated document any vendor publishes. This is the sharpest limitation of the confidence
rule as written: **it rewards a vendor with a well-written privacy policy.** A short, precise,
factual sentence loses to a long, vague, well-formed one. GitHub's `<h2>` above is the clearest
case — 52 characters naming three standards, outranked by 164 characters of liability language.

### 4.3 Vendors that score well because nothing contradicted them

The most important open defect in the system, and the thing Agent 3 exists to fix:

| | Postman | Sentry |
|---|---|---|
| Core score | **10/10** | **10/10** |
| Confidence | **High** | **High** |
| Fields FOUND | 8 of 8 | 8 of 8 |
| Fields carrying caveats | **4** | **0** |
| Privacy policy | **0 readable characters** | fully readable |
| Docs page | **2,370 chars from 1.2 MB (98% JavaScript)** | fully readable |

**Postman and Sentry receive identical scores and identical confidence labels. One of them was
read. The other largely was not.** The score counts what was found; it does not count what was
never looked at. Presented to an operations lead without the caveats visible, these two vendors
are indistinguishable — which is precisely the failure named at the top of this document,
reproduced by the system's own scoring.

Agent 3 must therefore either discount caveated fields when scoring, or print a coverage figure
beside the score so that "10/10 from 4 of 8 fields we could actually verify" cannot be read as
"10/10". Until it does, **the vendor score must not be presented as a comparative measure.**

And the case for keeping JetBrains: it fails worst — 5/10, four fields NOT_FOUND, three pages
unreadable, one page type never resolved after three attempts. It is also the single best piece of
evidence this evaluation has for the brief's own question, *where does manual review remain
necessary?* Swapping it for a tidier reserve vendor would have improved every number in this
document and destroyed its point.

---

## 5. What found the defects

**Thirty-three defects have been found in this project. The automated test suite caught one.**

The other thirty-two were found by opening the artifact and reading what it actually said — the
screen first, then the JSON, then the raw HTML. Ninety-seven offline tests are worth having: they
hold the fixed behaviour still while it is changed. But they test what was already understood.
Every defect that mattered was a gap between what the code was believed to do and what the vendor
pages actually contained, and no test written from the first belief can find that.

Three that illustrate the pattern:

- `sla` matched **"Slack" eleven times out of thirteen**, and `cli` matched *click*, *client* and
  *decline* nine times out of nine. A substring is not a word. Whole-token matching fixed it.
- `SLA` inside *"a deadline based on an internal Service Level Agreement (SLA) for fixing
  vulnerabilities"* — a vulnerability-remediation commitment — scored High confidence for **uptime
  reliability**. A string match is not a meaning. Negative terms fixed it.
- The confidence rule documented in `docs/confidence_rules.md` described behaviour the code did
  not implement. Checking code against its own documentation found it; checking the documentation
  against the current *data* later found that its worked examples had gone stale too. Both
  directions need checking.

The same discipline applied to this document. Four candidate findings were investigated while
writing it; **three were wrong** — a set of apparent orphan citations that turned out to be
snippet truncation, two pages that appeared misclassified until the recomputation itself was found
to be at fault, and a JetBrains extraction that appeared to have missed SOC 2 entirely when the
truncation was in the diagnostic, not the code. Only the fourth survived. Reporting any of the
first three would have sent a day of work at a defect that did not exist.

---

## 6. Honest limitations of this evaluation

- **Agent 3 does not exist yet.** Every statement here about brief assembly, review flags and
  scoring describes Agent 2's output and `tools/verify_corpus.py`, not the finished workflow.
- **Seven vendors in one category is not a sample.** These findings describe developer-productivity
  vendors' public pages in August 2026 and should not be generalised further.
- **The corpus is a snapshot.** Vendor pages changed measurably between two consecutive days of
  this project. Re-running collection on a later date will produce different numbers.
- **No JavaScript rendering.** This is a scope decision, not a claim that rendering is unnecessary.
  Its cost is measured in §1.1 and reported rather than hidden — eight pages, four vendors.
- **The `PARTIAL` status has never been produced** and the reason has not been established.
- **Defects 27 through 33 are open at the time of writing.** The GitHub and JetBrains quotes shown
  in §2.3 are current output, not historical examples.
