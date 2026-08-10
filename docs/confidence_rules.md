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

## Step 3 — field confidence

| | Authoritative page | Secondary page |
|---|---|---|
| `body`, ≥ 40 characters | **High** | **Medium** |
| `body`, < 40 characters | **Medium** | **Low** |
| `heading_only` | **Medium** | **Low** |
| `alt_text_only` | **Low** | **Low** |
| no match at all | **NOT_FOUND** | **NOT_FOUND** |

If several pieces of evidence exist for one field, the **best** one sets the
level. The 40-character floor exists because a fragment such as "SOC 2 and 3"
is a label, not a claim.

**NOT_FOUND is a real answer, not a failure.** It means: this vendor does not
publish this on the pages we are permitted to read. That is useful information
for a procurement team and it is the honest output.

## Step 4 — vendor confidence

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
| Postman | "We comply with industry standards and regulations…" + list incl. "SOC 2 and 3" | body | authoritative | **High** |
| Sentry | "SOC 2 Type I / Type II"; report "available to customers … upon request" | body | authoritative | **High** + flag: evidence gated behind customer account |
| Atlassian | Heading "Our compliance certifications"; certifications are images, alt-text "AICPA SOC logo" | alt_text_only | authoritative | **Low** + flag: logos only, verify manually |
| GitHub | "GitHub's API stays secure with ISO, SOC 2, and GDPR" — an API claim, not a platform claim | body | authoritative | **Low** + flag: certifications not published publicly; request trust portal access |

The Atlassian row is the regression guard. `tests/test_parse.py` asserts it can
never score High — if it ever does, the extractor is presenting a picture as a
written claim, and that is the failure mode this whole project exists to avoid.

## Known limitations of this rule

- It measures **how well-evidenced a statement is**, not whether the statement is
  true. A vendor could publish a confident, well-written falsehood and score High.
- It cannot read PDFs, images, or content behind a login. Atlassian and GitHub
  both lose points for publishing in formats we deliberately do not parse — that
  is a limitation of the method, not a judgement about those vendors.
- The 40-character floor is a chosen number, not a derived one. It is set in
  `config/settings.yaml` (`min_body_chars_for_high`) so a reviewer can change it
  and re-run.
