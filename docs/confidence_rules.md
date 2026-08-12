# Confidence rules

Confidence in this prototype is a **rule**, not a judgement call. Anyone can
apply it by hand to any page and get the same answer the code gets. That is the
point: a reviewer who disagrees with a rating can see exactly which clause
produced it.

## Why confidence is needed at all

Two vendors can both "have SOC 2" while the evidence for one is a full sentence
on their trust page and the evidence for the other is a logo image. Reporting
both as "yes" would hide the difference that actually matters to a reviewer.

## Step 1 — classify each page as authoritative or secondary

| Class | Page types | Reasoning |
|---|---|---|
| **Authoritative** | security, privacy, pricing, status, terms | The vendor is making a formal statement it can be held to. |
| **Secondary** | product, docs, integrations, blog | Marketing or explanatory content; true, but not a commitment. |

Both classes must be on the vendor's **own domain**. Third-party pages are not
collected at all.

## Step 2 — classify where the term was matched

| Location | Meaning |
|---|---|
| `body` | The vendor states it in prose beneath a heading. |
| `heading_only` | A heading names the topic; no explanatory text follows. |
| `alt_text_only` | The only match is an image's `alt` attribute. |

A term must appear as a **whole word or phrase**, not as a fragment inside a
longer word. `SLA` matches "a 99.9% SLA" and not "Slack"; `CLI` matches "run the
CLI" and not "click". This is `parse.term_in`, and it exists because the first
version did not do it — see the note at the end of this file.

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
| "Advanced CI/CD Team Project Management SLA Management Priority Support" | 0 — no sentence-ending punctuation at all | a feature list |
| "Includes $12 in GitLab Credits per user per month*" | 0 | a label, despite being 49 characters |
| "SOC 2 and 3. PCI DSS. HIPAA." | 12 | a list of labels |

Text with no sentence-ending punctuation scores 0 by definition. A commitment a
vendor can be held to is written as a sentence.

## Step 3b — is this the page where the fact belongs?

Each field names its natural home in `config/field_dictionary.yaml`
(`preferred_source_types`): security & trust belongs on the security page,
pricing on the pricing page, uptime on the status page.

This **orders** evidence; it never filters it. GitLab genuinely states its
FedRAMP position on its *pricing* page, and suppressing that because it was
"the wrong page" would be the extractor overruling the vendor. What it does is
decide which piece of evidence gets quoted when several are equally strong.

## Step 4 — field confidence

| | Authoritative page | Secondary page |
|---|---|---|
| `body`, longest sentence ≥ 40 characters | **High** | **Medium** |
| `body`, longest sentence < 40 characters | **Medium** | **Low** |
| `heading_only` | **Medium** | **Low** |
| `alt_text_only` | **Low** | **Low** |
| no match at all | **NOT_FOUND** | **NOT_FOUND** |

If several pieces of evidence exist for one field, the **best** one sets the
level — and the brief quotes that same piece. `parse.evidence_level` scores one
item; the field takes the maximum, and Agent 2's ranking sorts by it first, so
the quote a reviewer reads is always the evidence that earned the label printed
above it.

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
as "the vendor said so".

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

## Worked examples from real pages (collected 2026-08-10)

| Vendor | Evidence for security & trust | Location | Page class | Result |
|---|---|---|---|---|
| Linear | "Linear undergoes regular Service Organization Controls audits (SOC 2 Type II)." | body | authoritative | **High** |
| GitLab | "GitLab maintains a SOC 2 Type 2 report for the Security, Confidentiality and Availability Trust Services Criteria for GitLab.com." | body | authoritative | **High** |
| Postman | "We comply with industry standards and regulations…" + list incl. "SOC 2 and 3" | body | authoritative | **High** from the sentence; the bare list alone would be Medium |
| Sentry | "SOC 2 Type I / Type II"; report "available to customers … upon request" | body | authoritative | **High** + flag: evidence gated behind customer account |
| Atlassian | Heading "Our compliance certifications"; certifications are images, alt-text "AICPA SOC logo" | alt_text_only | authoritative | **Low** / `PARTIAL` + flag: logos only, verify manually |
| GitHub | "GitHub's API stays secure with ISO, SOC 2, and GDPR" — an API claim, not a platform claim | body | authoritative | **High** by the rule, and the rule is wrong here — see "Known limitations" |

The Atlassian row is the regression guard. `tests/test_parse.py` and
`tests/test_agent2.py` both assert it can never score High — if it ever does,
the extractor is presenting a picture as a written claim, and that is the
failure mode this whole project exists to avoid.

## Known limitations of this rule

- It measures **how well-evidenced a statement is**, not whether the statement is
  true, and not whether it is about the thing you asked. GitHub's sentence
  "GitHub's API stays secure with ISO, SOC 2, and GDPR" is a full sentence on an
  authoritative page, so the rule returns **High** — but it is a claim about the
  API, not about the platform. No rule-based system reads scope. **This is a
  human-review case by design**, and it is why the brief prints the quote and
  its source URL beside every confidence label rather than the label alone.
- It rewards a vendor with a long, well-written privacy policy. On the real
  GitLab corpus, three of the five core fields drew their strongest evidence
  from the privacy policy, because that page is both authoritative and full of
  complete sentences. Agent 3 raises a review flag whenever a field's evidence
  comes only from a page outside its `preferred_source_types`.
- It cannot read PDFs, images, or content behind a login. Atlassian and GitHub
  both lose points for publishing in formats we deliberately do not parse — that
  is a limitation of the method, not a judgement about those vendors.
- The 40-character floor is a chosen number, not a derived one. It is set in
  `config/settings.yaml` (`min_body_chars_for_high`) so a reviewer can change it
  and re-run.

## Two rules this document used to describe incorrectly

Recorded here rather than quietly corrected, because how a rule was wrong is
worth more to a reader than the rule alone.

1. **Matching was a bare substring test.** This document said a term is "a plain
   phrase", which was true, and implied it matched as a phrase, which was not.
   Across GitLab's seven pages the term `sla` matched 13 times and only 2 were
   the acronym — the rest were "Slack". `cli` matched 9 times and never once
   meant the command line. GitLab's uptime field was reported **FOUND / High**
   quoting its privacy policy on third-party vendors.

2. **The 40-character floor measured the whole block.** This document has always
   justified the floor with "a fragment such as 'SOC 2 and 3' is a label, not a
   claim" — but the code measured the length of the entire matched block, which
   a bullet list clears easily. The floor now measures the longest sentence, so
   the document and the code finally say the same thing.

Both were found on 2026-08-12 by reading Agent 2's first real output field by
field against the pages it came from. Neither was caught by 82 passing tests.
