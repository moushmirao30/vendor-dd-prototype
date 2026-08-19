# Client guidance — First Quadrant Labs, 18 August 2026

**AUTHORITATIVE. This is the client speaking in writing about their own brief.
Where it conflicts with anything else in this repository — including the locked
decisions in `HANDOFF.md` §2 — it wins.**

**Written into the repository on 19 August 2026, in full.** It had been held only
in the assistant's project memory, which was lost. `HANDOFF.md` §1.1 carries a
condensed version; this file is the complete record. **A client instruction that
exists in one place, and that place is not version-controlled, is one session away
from being gone** — and a design decision whose justification has disappeared is
indistinguishable from a decision nobody thought about.

Quote it in `docs/assumptions_limitations.md` and `docs/evaluation.md`. A
documented client instruction is the strongest justification a design choice can
have.

**Their closing position:**

> *"You do not need to redesign Agents 1 and 2 based on the points raised above.
> Please proceed with Agent 3, the review interface, exports, testing,
> documentation, and evaluation."*

So this is guidance, not a rework order — **except item 3, which changes a
deliverable.**

---

## 1 · LLM — CONFIRMED. Rule-based is the delivered behaviour.

- Fully rule-based extraction is **acceptable as the primary behaviour**. LLM
  integration is **not mandatory**.
- They praised the design in their own words:
  > *"retaining verbatim evidence from the source is valuable for auditability and
  > reduces hallucination risk."*

  **The `value`-is-a-quote decision is therefore client-endorsed — say so in the
  evaluation.**
- **Optional extra if time permits:** an LLM summarisation toggle as a *secondary*
  feature. Hard constraints: the system must still work completely **without an API
  key**, and any LLM-generated summary **must retain links or references to the
  underlying evidence**.
- Priority: this is the LAST thing to build, after Agent 3, exports, docs and
  evaluation.

## 2 · JavaScript-rendered pages — CONFIRMED. No headless browser.

> *"You are not required to introduce Playwright, Selenium, or another
> headless-browser layer."*

**Two obligations follow, and the wording is theirs:**

- The output must clearly distinguish:
  - information **not found** on the vendor's public sources, from
  - information that **could not be evaluated** because the page could not be
    reliably extracted.
- **Before marking a category unavailable, check whether the same information
  exists on another official source** — trust centre, documentation, security page,
  help centre — and otherwise flag for manual review. Agent 2 already searches
  every collected page; what was missing was making that check **visible in the
  brief** ("searched N other official pages, found nothing") rather than implicit.
- **They asked for the number AND percentage of affected pages in the evaluation
  summary.** Current: **8 of 49 pages, 16.3%**, across 4 of 7 vendors.

## 3 · SUBMISSION FORMAT CHANGED — this reverses a locked decision

> *"We recommend not including the complete 22 MB cache of verbatim third-party
> HTML pages in the final submission archive."*

The previous locked decision — ship a zip including `.git/` so a reviewer could
replay offline — **is withdrawn.**

**Submit instead:**

- the structured **CSV/JSON/SQLite corpus**
- **source URLs and page titles**
- **date collected**
- **relevant extracted sections / evidence snippets**
- **source type and tags**
- **the collection / retrieval code**
- **a SOURCE MANIFEST showing which pages were successfully or unsuccessfully
  collected** ← **NEW DELIVERABLE, not in the original brief.**

Keep the full HTML cache **locally** for development and reproducibility.
**The README must explain how a reviewer can re-collect the public sources.**

Their rationale: it keeps the submitted corpus focused on research evidence rather
than redistributing full copies of third-party webpages.

**Consequence, to state plainly in the README and the limitations note:** a fresh
clone of the submitted archive **cannot replay the full pipeline offline until the
reviewer re-collects.** That is a consequence of a client instruction, not an
oversight, and naming it that way is the difference between a limitation and a
defect.

## 4 · CONFIDENCE — they pushed back on the core of the rule

> *"We recommend not basing confidence primarily on sentence length. A long
> sentence is not necessarily stronger evidence than a short statement or
> structured table."*

**They supplied a model:**

| Level | Their definition |
|---|---|
| **High** | Direct, explicit evidence from an authoritative official source, with the requested field **clearly answered**. |
| **Medium** | Relevant official evidence exists, but it is **incomplete, indirect, spread across multiple sections, or requires limited interpretation**. |
| **Low** | Evidence is **weak, ambiguous, outdated, inaccessible**, or the field cannot be confidently established from the collected public material. |

**And the sentence that makes it implementable:**

> *"You can additionally track extraction quality separately if you want to measure
> whether the evidence was obtained from a complete sentence, bullet list, table,
> etc."*

Their High/Medium/Low is **semantic** — "clearly answered", "requires limited
interpretation". A rule-based system with no LLM cannot judge whether a field is
clearly answered, so their wording cannot be implemented literally inside the
no-LLM decision they endorsed in the same email. Their last sentence is the
resolution: **two axes, then three measures.** See `docs/confidence_rules.md`
§Step 6 for how it was built and what went wrong on the way (defects 42 and 43).

## 5 · Four additional requirements — all NEW

- **Agent 3 scope, confirmed narrow:**
  > *"focus on review and synthesis rather than introducing another complex
  > intelligence layer. It should verify evidence coverage, identify missing
  > categories, highlight conflicts or weak evidence, and prepare the final brief."*

  Note **"highlight conflicts"** — contradiction detection between sources was not
  in the original brief.
- **Offline replay is a strong feature and must be DEMONSTRATED in the final
  submission** — via the demo, screenshots and the audit trail. **This and item 3
  must be reconciled explicitly**, not left to coexist.
- **The Streamlit view must show the chain explicitly:**
  `Source → Extracted Evidence → Structured Field → Confidence → Review Flag → Final Brief`
- **The evaluation must include a cross-vendor comparison table** covering: source
  coverage, extraction success rate, inaccessible pages, populated due-diligence
  fields, and fields requiring manual review. They said this demonstrates
  effectiveness and limitations **better than screenshots alone**.

**Their figures for that table, verified against the frozen 13 August corpus:**

| Vendor | Pages | Usable | Extraction success | Fields populated | Fields needing manual review | Coverage |
|---|---|---|---|---|---|---|
| GitHub | 8 | 8 | 100% | 7/8 | 1 | 5/5 |
| GitLab | 7 | 7 | 100% | 7/8 | 1 | 5/5 |
| Sentry | 7 | 7 | 100% | 8/8 | 1 | 5/5 |
| Linear | 7 | 6 | 86% | 6/8 | 6 | 3/5 |
| Atlassian | 7 | 5 | 71% | 6/8 | 5 | 2/5 |
| Postman | 7 | 5 | 71% | 8/8 | 4 | 2/5 |
| JetBrains | 6 | 3 | 50% | 4/8 | 5 | 2/5 |
| **TOTAL** | **49** | **41** | **84%** | **46/56 (82%)** | **23/56 (41%)** | — |

---

## The tone of their reply, and what it does and does not mean

They opened with *"Your approach is well aligned with the intended scope"* and
closed with *"We appreciate that you raised these questions before making
unnecessary architectural changes."*

The email was worth sending and the restraint decisions were correct. **Do not
over-read the praise.** Items 3 and 4 are real changes, and item 5 adds four
requirements that did not exist before.
