# Vendor Due-Diligence Research Workflow Prototype

A bounded internal experiment: a three-step workflow that collects, structures
and summarises **public** vendor due-diligence information into consistent
first-pass research briefs, with every statement traceable to the page it came
from.

> **First-pass internal research aid.** Built from public web pages only. It does
> not assign vendor risk scores, grant security or compliance approval, or make
> procurement decisions. Every field requires human review.

---

## Current status

| Stage | State |
|---|---|
| Day 1–3 — vendor register, schema, confidence rules, extraction core, UI shell | **Complete** |
| Day 4–8 — Source Collection Agent (fetching, caching, robots checks) | Not started |
| Day 9–13 — Evidence Extraction Agent | Core parser complete and tested; agent wrapper not started |
| Day 14–16 — Brief Review Agent, exports, UI polish | Not started |
| Day 17–19 — documentation, evaluation, submission | Not started |

`pytest` currently passes 9/9 tests covering five real page shapes.

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py     # the review interface
pytest -v                # the test suite
```

No API key, no account, no GPU and no paid service is required. After one
collection run, every page is cached to `data/cache/html/`, so the workflow
replays **fully offline**.

## The three agents

The project brief allows a maximum of three working roles. There is no manager
agent, no memory layer and no autonomous browsing loop — the flow is strictly
linear so that it stays explainable and debuggable.

| Agent | File | Job |
|---|---|---|
| **1 · Source Collection** | `src/agent1_collect.py` | Builds candidate URLs from patterns, keeps the ones that return HTTP 200, classifies each page type, falls back to the curated seed list in `config/vendors.yaml` when discovery fails. |
| **2 · Evidence Extraction** | `src/agent2_extract.py` | Cuts each page into heading-anchored blocks and matches them against `config/field_dictionary.yaml`, keeping the heading, snippet and matched terms as evidence. |
| **3 · Brief Review** | `src/agent3_review.py` | Applies the confidence rules, flags missing or unclear fields, and assembles the vendor brief. |

## How extraction works, in one paragraph

A page is split into **blocks** — one heading plus the paragraphs beneath it.
Each block is tested against a plain list of phrases held in a YAML file
(`config/field_dictionary.yaml`), not against regular expressions. When a block
matches, the whole block is kept: heading, snippet, matched terms and source URL.
That produces evidence a human can check, and it means adding coverage for a new
vendor is a matter of adding a phrase to a data file rather than editing code.
Vendors write the same fact very differently — `SOC 2 Type II` (Linear),
`SOC 2 Type 2` (GitLab), `SOC 2 and 3` (Postman), `Service Organization Controls`
(Linear), or as a logo with alt-text `AICPA SOC logo` (Atlassian) — which is
exactly why a phrase list beats a pattern.

## Layout

```
config/     vendors.yaml · field_dictionary.yaml · settings.yaml   <- all policy lives here
src/        agent1..3, orchestrator, fetch, parse, schema, export  <- all behaviour lives here
data/       cache/html · corpus · briefs
docs/       architecture · confidence_rules · assumptions_limitations · evaluation · code_walkthrough
tests/      test_parse.py + five HTML fixtures modelled on real vendor pages
```

## Vendor set

Seven developer-productivity vendors, chosen at three difficulty tiers so the
evaluation has real failure modes to report rather than only successes:

- **Rich** — GitLab, Linear, Sentry
- **Awkward** — Postman (bare certification lists), Atlassian (certifications as images)
- **Hard** — GitHub (certifications not on public pages), JetBrains (legal-document style)

Reserve: Docker, CircleCI, Vercel.

## Scope boundaries

Deliberately **not** built: procurement decisions, official risk scores,
legal/compliance/security approval, access to private vendor portals, aggressive
scraping or restriction bypassing, a production procurement platform, or any
dependency on paid databases or enterprise tooling.

Collection policy: `robots.txt` checked before every fetch, 2-second delay per
domain, honest User-Agent, hard cap of 10 pages per vendor, no JavaScript
rendering. See `config/settings.yaml` and `docs/assumptions_limitations.md`.
