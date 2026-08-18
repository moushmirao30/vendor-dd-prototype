# Confidence rules

Confidence in this prototype is a **rule**, not a judgement call. Anyone can
apply it by hand to any page and get the same answer the code gets. That is the
point: a reviewer who disagrees with a rating can see exactly which clause
produced it.

**Last corrected 13 August 2026** for defects 27, 28 and 36. The corrections are
listed in full at the end of this file rather than folded silently into the text.

> ## ⚠ CLIENT GUIDANCE, 13 AUGUST 2026 — this rule is scheduled to change
>
> First Quadrant Labs reviewed this approach in writing and asked for one change:
>
> > *"We recommend not basing confidence primarily on sentence length. A long sentence is not
> > necessarily stronger evidence than a short statement or structured table."*
>
> They are right, and the corpus agrees with them: GitHub's most precise security statement is 52
> characters (`"GitHub's API stays secure with ISO, SOC 2, and GDPR."`) while the sentence that
> nearly became Atlassian's security headline is 322 characters of terms-of-service prose about
> something else. Length is a proxy for "is this a claim or a label", and it is a **good** proxy
> for that narrow question — but it is the wrong thing to put at the top of a confidence rule.
>
> **The model they gave:**
>
> | Level | Client definition |
> |---|---|
> | High | Direct, explicit evidence from an authoritative official source, with the requested field **clearly answered**. |
> | Medium | Relevant official evidence exists, but it is **incomplete, indirect, spread across multiple sections, or requires limited interpretation**. |
> | Low | Evidence is **weak, ambiguous, outdated, inaccessible**, or the field cannot be confidently established. |
>
> **Why it cannot be implemented literally.** "Clearly answered" and "requires limited
> interpretation" are semantic judgements. This prototype has no language model by design, so it
> cannot decide whether a field is clearly answered. Taking their wording at face value would
> require breaking a locked decision they themselves endorsed in the same email.
>
> **How it will be implemented.** Their own next sentence supplies the resolution —
> *"You can additionally track extraction quality separately … complete sentence, bullet list,
> table, etc."* So the single axis below becomes two:
>
> | Axis | What it measures | Source |
> |---|---|---|
> | **Extraction quality** | sentence · bullet list · table · bare heading · image alt-text | **everything documented below**, renamed. The logic is sound; the name was wrong |
> | **Confidence** | the client's definition, via mechanical proxies | **High** = on the field's own preferred authoritative page, matched term present in the quoted text, **no tool-limitation caveat**. **Medium** = official but off-home, spread across pages, home page unreadable so the answer came from elsewhere, or a list/table/heading+body pair. **Low** = bare label, alt-text only, inaccessible, or conflicting |
>
> **This closes the worst open defect in the project as a side effect.** The new rule mechanically
> forbids a caveated field from scoring High, so Postman's *10/10 → High on coverage 2/5* becomes
> impossible. See "The score does not measure coverage" below.
>
> **Status: designed, not yet implemented.** It lands with Agent 3 (14–16 Aug) as an additive
> change of roughly 40 lines, not a rewrite of Agent 2 — the client explicitly said Agents 1 and 2
> do not need redesigning. **Everything below this box describes the rule as the code applies it
> today.** When the change lands, this box is replaced by the new rule and moved into the
> corrections list at the end. Leaving it as a description of unbuilt behaviour would make this the
> third document in the project to describe code that does not exist.

## Why confidence is needed at all

Two vendors can both "have SOC 2" while the evidence for one is a full sentence
on their trust page and the evidence for the other is a logo image. Reporting
both as "yes" would hide the difference that actually matters to a reviewer.

## Step 1 — classify each page as authoritative or secondary

| Class | Page types | Reasoning |
|---|---|---|
| **Authoritative** | security, **trust**, privacy, pricing, status, terms | The vendor is making a formal statement it can be held to. |
| **Secondary** | product, docs, integrations, blog | Marketing or explanatory content; true, but not a commitment. |

`trust` was added on 13 August 2026 with defect 27. The project brief names the
source category as *"security or trust center pages"* — one category, two URLs —
so a vendor's trust centre is exactly as authoritative as its security page.
GitHub is the only vendor in this corpus that publishes both.

Both classes must be on the vendor's **own domain**. Third-party pages are not
collected at all.

## Step 2 — classify where the term was matched

| Location | Meaning |
|---|---|
| `body` | The vendor states it in prose beneath a heading. |
| `heading_only` | A heading names the topic; the explanation, if any, is separate. |
| `alt_text_only` | The only match is an image's `alt` attribute. |

A term must appear as a **whole word or phrase**, not as a fragment inside a
longer word. `SLA` matches "a 99.9% SLA" and not "Slack"; `CLI` matches "run the
CLI" and not "click". This is `parse.term_in`, and it exists because the first
version did not do it — see the notes at the end of this file.

**Interface furniture is removed before anything is quoted or measured.**
`parse.strip_noise` deletes phrases listed in `extraction.noise_phrases` — today,
the placeholders GitHub's pricing page renders when a panel fails to load. This
is deliberately *not* a `negative_term`: a negative term suppresses the whole
block, and that block also contained GitHub's SOC 2 statement. It matters for
scoring as well as for readability, because *"There was an error while loading."*
is a 41-character sentence and 40 is the threshold for High.

## Step 3 — how long is the claim?

The block that matched is not the claim. A block is a heading plus everything
under it, so a bullet list of certifications easily runs to hundreds of
characters while saying nothing a vendor could be held to.

So the measurement is **the longest complete sentence inside the matched
block** (`parse.longest_sentence_length`), against `min_body_chars_for_high` in
`config/settings.yaml`, currently 40.

| Matched text | Longest sentence | Reading |
|---|---|---|
| "GitLab maintains a SOC 2 Type 2 report for the Security, Confidentiality and Availability Trust Services Criteria for GitLab.com." | 129 | a claim |
| "GitHub's API stays secure with ISO, SOC 2, and GDPR." | 52 | a claim — **and it is an `<h2>` with no paragraph under it** |
| "Advanced CI/CD Team Project Management SLA Management Priority Support" | 0 — no sentence-ending punctuation at all | a feature list |
| "Includes $12 in GitLab Credits per user per month*" | 0 | a label, despite being 49 characters |
| "SOC 2 and 3. PCI DSS. HIPAA." | 12 | a list of labels |
| "Pricing" | 0 | a section label — the vendor wrote no claim here |

Text with no sentence-ending punctuation scores 0 by definition. A commitment a
vendor can be held to is written as a sentence.

**The test is the sentence, not the HTML tag** (defect 28). A heading that is a
complete sentence is prose a designer set in larger type, and it is scored as
prose. A heading that is a label — "SOC Certification", "Pricing", "Data
Residency" — scores 0 and cannot reach High no matter which page it is on.

## Step 3b — is this the page where the fact belongs?

Each field names its natural home in `config/field_dictionary.yaml`
(`preferred_source_types`): security & trust belongs on the security page or the
trust centre, pricing on the pricing page, uptime on the status page.

This **orders** evidence; it never filters it. GitLab genuinely states its
FedRAMP position on its *pricing* page, and suppressing that because it was
"the wrong page" would be the extractor overruling the vendor. What it does is
decide which piece of evidence gets quoted when several are equally strong.

**Because it orders before term count, this list is a policy statement and a
wrong entry is a wrong answer** (defect 27). `security_trust` used to list
`terms` as a preferred home. The result was that GitHub's security field quoted
its terms of service — *"…the content of your Account and its security are up to
you."*, one matched term — above *"GitHub offers AICPA System and Organization
Controls (SOC) 1 Type 2 and SOC 2 Type 2 reports…"*, four matched terms. A
terms-of-service page is where a vendor **limits** its security obligations; a
security page or trust centre is where it **states** its posture. The ranking
code was never wrong; this list was.

## Step 4 — field confidence

| | Authoritative page | Secondary page |
|---|---|---|
| longest sentence ≥ 40 characters — in prose **or in a heading that is a whole sentence** | **High** | **Medium** |
| `body`, longest sentence < 40 characters (a bullet list, a fragment) | **Medium** | **Low** |
| `heading_only`, no sentence — a bare label with nothing under it | **Low** | **Low** |
| `alt_text_only` | **Low** | **Low** |
| no match at all | **NOT_FOUND** | **NOT_FOUND** |

The bare-heading row **changed on 13 August 2026** (defect 36) — it used to read
Medium on an authoritative page. See the corrections section.

If several pieces of evidence exist for one field, the **best** one sets the
level — and the brief quotes that same piece. `parse.evidence_level` scores one
item; the field takes the maximum, and Agent 2's ranking sorts by it first, so
the quote a reviewer reads is always the evidence that earned the label printed
above it.

**Which sentence is quoted:** within the winning block, the value is the sentence
carrying the **most** matched terms, ties going to the earliest (defect 30).
It used to be the first sentence carrying *any* term, which made JetBrains'
security field read *"Please visit our Trust Center to learn more…"* — a signpost
matched on the navigational term `trust center` — while *"You can also find
details on our SOC 2 Type II and GDPR compliance…"* sat 340 characters later in
the same quoted block.

**NOT_FOUND is a real answer, not a failure.** It means: this vendor does not
publish this on the pages we are permitted to read. That is useful information
for a procurement team and it is the honest output.

## Step 5 — status

| Confidence | Status | Meaning |
|---|---|---|
| High, Medium | `FOUND` | the vendor states it, and we can quote it |
| Low | `PARTIAL` | a hint only — a heading, a logo, a fragment. Open the page. |
| NOT_FOUND | `NOT_FOUND` | nothing matched on any page we could read |

`PARTIAL` exists so that "we saw a hint" is never printed with the same weight
as "the vendor said so". **Until 13 August 2026 it was unreachable** — see the
corrections section. It now occurs three times across the corpus: Linear's
pricing and data-residency fields, and Sentry's data-residency field, each of
which matched a section heading with no statement written under it.

## Step 6 — vendor confidence

Score the **five core fields** — security & trust, privacy & data handling,
support & documentation, integrations & API, pricing availability:

```
High = 2    Medium = 1    Low = 0    NOT_FOUND = 0
```

Maximum 10.

| Total | Vendor confidence |
|---|---|
| 8 – 10 | **High** |
| 4 – 7 | **Medium** |
| 0 – 3 | **Low** |

Supplementary fields (data residency, encryption, uptime) are reported but **not
scored**, because they are absent from most vendors' pages by convention rather
than by omission — penalising a vendor for that would make the score meaningless.

### The score does not measure coverage, and must never be read alone

This score counts what was found. It does not count what was never looked at.
Postman scores **10/10 → High** with four core fields resting on pages that
returned no readable text; Sentry scores **10/10 → High** with every page read.
`tools/verify_corpus.py` therefore prints a coverage figure beside every score —
*"coverage 2/5 core fields verified without a caveat"* — and raises
`score-without-coverage` when a High rests on unread pages.

**Agent 3 owes a coverage-aware score, and must import that calculation rather
than write its own.** A build-time tool and a shipped brief computing the same
thing two different ways is how the two start disagreeing.

## Worked examples from the current corpus (re-derived 2026-08-13)

Every row below was re-checked against `data/corpus/*_fields.json` on 13 August.
The previous version of this table was written on 10 August and **three of its
six rows had gone stale** — see the corrections section. A worked example decays
the moment the data moves.

| Vendor | `security_trust` result | Quoted value | Why |
|---|---|---|---|
| GitLab | **FOUND / High** | "GitLab maintains a SOC 2 Type 2 report for the Security, Confidentiality and Availability Trust Services Criteria for GitLab.com." | prose, security page, 129-character sentence |
| Sentry | **FOUND / High** | "Sentry has obtained the following compliance certifications: SOC2 Type I SOC2 Type II HIPAA Attestation ISO 27001…" | prose, security page. Reports are "available to customers … upon request" — **gated evidence, Agent 3 must flag it** |
| Postman | **FOUND / High** | "All compliance documents SOC 2 Type II reports, penetration test summaries, audit reports and security questionnaire responses are available via the…" | prose, security page, seven matched terms in one block |
| GitHub | **FOUND / High** | "GitHub's API stays secure with ISO, SOC 2, and GDPR." | an `<h2>` with **no paragraph under it**. Before defect 28 this produced an EMPTY quote, scored Medium, ranked 9th of 9 and never reached the brief |
| JetBrains | **FOUND / High** | "You can also find details on our SOC 2 Type II and GDPR compliance, access security resources, and view our controls across various security domains." | prose on the corrected trust-centre seed. Before defect 30 the value was the signpost sentence two sentences earlier |
| Linear | **FOUND / Medium** | a pricing-tier feature list naming SAML and SCIM | **Linear's security page carries `<h2>SOC 2 compliance</h2>` with an empty body** — the detail is JavaScript-rendered. The field falls back to the pricing page |
| Atlassian | **FOUND / High** | "Sensitive Health Information and HIPAA." | a numbered **terms-of-service section title**. The High was earned by a 322-character sentence elsewhere in the same block. **See the last limitation below** |

The Atlassian regression guard still holds and is separate from that row:
`tests/test_parse.py::test_atlassian_shape_never_scores_high_on_alt_text_alone`
asserts that evidence whose only match is an image's alt-text can never score
High. If it ever does, the extractor is presenting a picture as a written claim,
and that is the failure mode this whole project exists to avoid.

## Known limitations of this rule

- **It measures how well-evidenced a statement is, not whether the statement is
  true, and not whether it is about the thing you asked.** GitHub's sentence
  "GitHub's API stays secure with ISO, SOC 2, and GDPR" is a full sentence on an
  authoritative page, so the rule returns **High** — but it is a claim about the
  API, not about the platform. No rule-based system reads scope. **This is a
  human-review case by design**, and it is why the brief prints the quote and its
  source URL beside every confidence label rather than the label alone.
- **The label can be earned by a sentence that does not contain the matched
  term.** `evidence_level` measures the longest sentence anywhere in the block.
  In **9 of 122 evidence blocks** that sentence carries no matched term.
  Atlassian's security field is the clearest case: `hipaa` occurs only in the
  39-character section title *"Sensitive Health Information and HIPAA."*, while
  the High came from a 322-character sentence about something else in the same
  terms-of-service section. **Left unfixed on purpose.** The obvious tightening —
  score only the longest sentence carrying the term — would also demote Sentry's
  *"High Availability"* heading with a full paragraph beneath it, and GitLab's
  *"Trust Center Documents"*. Vendors do not repeat a heading inside its own
  paragraph, so the strict rule trades a cosmetic over-score for a false
  negative. `verify_corpus` raises `claim-not-in-matched-sentence` on all nine so
  a human sees them.
- **It rewards a vendor with a long, well-written privacy policy.** On the real
  GitLab corpus, three of the five core fields drew their strongest evidence from
  the privacy policy, because that page is both authoritative and full of
  complete sentences. Agent 3 raises a review flag whenever a field's evidence
  comes only from a page outside its `preferred_source_types`.
- **It cannot read PDFs, images, or JavaScript-rendered content.** Eight of 49
  collected pages carried no readable text. Atlassian, Postman, JetBrains and
  Linear all lose points for publishing in formats we deliberately do not
  render — that is a limitation of the method, not a judgement about those
  vendors, and the cost is measured in `docs/evaluation.md` §1.1 rather than
  hidden.
- **The 40-character floor is a chosen number, not a derived one.** It is set in
  `config/settings.yaml` (`min_body_chars_for_high`) so a reviewer can change it
  and re-run.

## Rules this document used to describe incorrectly

Recorded here rather than quietly corrected, because how a rule was wrong is
worth more to a reader than the rule alone.

1. **Matching was a bare substring test** (12 Aug). This document said a term is
   "a plain phrase", which was true, and implied it matched as a phrase, which
   was not. Across GitLab's seven pages the term `sla` matched 13 times and only
   2 were the acronym — the rest were "Slack". `cli` matched 9 times and never
   once meant the command line. GitLab's uptime field was reported **FOUND /
   High** quoting its privacy policy on third-party vendors.

2. **The 40-character floor measured the whole block** (12 Aug). This document
   has always justified the floor with "a fragment such as 'SOC 2 and 3' is a
   label, not a claim" — but the code measured the length of the entire matched
   block, which a bullet list clears easily. The floor now measures the longest
   sentence, so the document and the code finally say the same thing.

3. **This document and the code disagreed about a bare heading, and the
   disagreement had killed an entire status value** (13 Aug, defect 36). Step 4
   said a heading-only match on an authoritative page scores **Medium**, which
   Step 5 then reports as **FOUND**. `agent2_extract.status_from_confidence`
   said, in its own docstring, *"PARTIAL — Low, something matched but only a
   heading, a logo, or a fragment."* Both cannot be true. The code implemented
   the Medium reading, so **`PARTIAL` was produced zero times across seven
   vendors and 56 field results** — a three-state vocabulary with a dead state,
   which is a vocabulary overstating its own precision. Resolved in favour of
   PARTIAL, because a label is a reason to go and look, which is what PARTIAL
   means. A bullet list on an authoritative page still scores Medium; only a bare
   heading changed.

4. **Three of the six worked examples had gone stale** (13 Aug, the same failure
   as defect 33 in `settings.yaml`). The Linear row quoted *"Linear undergoes
   regular Service Organization Controls audits (SOC 2 Type II)."* — that
   sentence appears nowhere in the current corpus, and Linear's security page now
   yields `<h2>SOC 2 compliance</h2>` with an empty body. The Atlassian row
   described the field as **Low / PARTIAL** from alt-text; it is **FOUND / High**
   from the terms page. The GitHub row happened to be right about the score and
   wrong about the mechanism. **Check documentation against the current data, not
   only against the code.**

Items 1 and 2 were found on 2026-08-12 by reading Agent 2's first real output
field by field against the pages it came from; neither was caught by 82 passing
tests. Items 3 and 4 were found on 2026-08-13 while investigating why a fix had
produced a false NOT_FOUND, and while re-checking this table row by row against
the corpus. Of 101 tests now passing, **one** has ever caught a defect first.
