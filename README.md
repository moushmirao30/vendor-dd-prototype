# Vendor Due-Diligence Research Workflow Prototype

A bounded internal experiment: a three-step workflow that collects, structures
and summarises **public** vendor due-diligence information into consistent
first-pass research briefs, with every statement traceable to the page it came
from.

> **First-pass internal research aid.** Built from public web pages only. It does
> not assign vendor risk scores, grant security or compliance approval, or make
> procurement decisions. Every field requires human review.

> **This README is the entry point**, and it is written for a reviewer: everything
> needed to run, read and check this prototype is here or in `docs/`. Start with
> *Start here* below, then `docs/evaluation.md` — its first page is a one-page summary.

---

## Start here — the submitted archive runs offline, with one caveat

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

pytest -q                       # 152 tests, all offline
python tools/run_workflow.py    # Agent 1 -> 2 -> 3 for every vendor. No network needed.
streamlit run app.py            # the review interface, then http://localhost:8501
```

No API key, no account, no GPU, no paid service, no language model.

**The one caveat, and it is a client instruction rather than an oversight.** First
Quadrant Labs asked on 18 August 2026 that the 22 MB cache of verbatim third-party
HTML **not** be redistributed. It is therefore excluded from this archive. The
consequence is stated plainly rather than discovered:

| What you can do in a fresh clone | Needs |
|---|---|
| Read the corpus, the briefs, the source manifest and every export | nothing |
| Re-run **Agent 3** over the saved extraction (`--mode review`, the default) | nothing |
| Re-run **Agent 2** over the original pages (`--mode replay`) | the HTML cache — see *Re-collecting* below |
| Re-fetch everything from the vendors (`--mode collect`) | a network connection |

`--mode replay` in a fresh clone does not fail quietly. It **refuses**, names the
pages whose cache is missing, and points you at the mode that works. That guard
exists because without it the pipeline reported all seven vendors as publishing
nothing — see *Honesty guarantees* below.

## Re-collecting the public sources

Everything needed to reproduce the corpus is in this archive: the vendor register,
the URL patterns, the collection code and the source manifest showing what was
attempted. To rebuild the cache from the live web:

```bash
python tools/run_workflow.py --mode collect              # all seven vendors
python tools/run_workflow.py --mode collect gitlab       # or one at a time
python tools/verify_corpus.py                            # expect 0 FAIL
python tools/export_all.py                               # refresh data/exports/
```

Collection reads `robots.txt` before every fetch, waits 2 seconds per domain,
sends an honest User-Agent, and stops at 10 kept pages or 20 requests per vendor.
A full run takes a few minutes.

**Expect the results to differ from the submitted corpus, and read that as a
finding rather than a fault.** Vendor pages move: Linear's docs page went from
24,444 bytes to 540,090 between 12 and 13 August 2026, and its security page now
publishes `<h2>SOC 2 compliance</h2>` with an empty body where a complete SOC 2
sentence was recorded three days earlier. **The corpus in `data/corpus/`, dated
13 August 2026, is the record of what was evaluated — not the live web.**
`docs/evaluation.md` reports every figure against that frozen corpus.

## Current status

**All three agents, the orchestrator, the export layer and the full interface are
built.** 152 offline tests; `python tools/verify_corpus.py` reports 0 FAIL across
all seven vendors.

| Deliverable | State |
|---|---|
| Working prototype (Streamlit, 5 tabs) | **Complete** |
| Python orchestration code | **Complete** — `src/orchestrator.py` |
| Structured public-source corpus | **Complete** — 7 vendors, 49 pages |
| Sample outputs for ≥5 vendors | **Complete** — 7 briefs × JSON/CSV/Markdown |
| Source manifest (client-requested) | **Complete** — 54 attempts, 5 never collected, 8 unreadable |
| README · architecture note · evaluation summary · screenshots | **Complete** |
| Assumptions and limitations note | **Complete** — `docs/assumptions_limitations.md` |
| Sample test cases (document) | In progress — 152 automated tests exist; the reviewer-facing note is being written |

## Running it

Activate the environment first — `.venv\Scripts\activate` on Windows,
`source .venv/bin/activate` elsewhere. Without it `pytest` is not on the PATH and
PowerShell reports it as an unrecognised command.

```bash
pytest -q                                    # 152 tests, all offline
python tools/run_workflow.py                 # 1 -> 2 -> 3, review mode (default)
python tools/run_workflow.py --mode replay   # re-extract from the cached HTML
python tools/run_workflow.py --mode collect  # re-fetch from the vendors
python tools/verify_corpus.py                # corpus health check; 0 FAIL before any commit
python tools/export_all.py                   # write data/exports/
streamlit run app.py                         # the review interface
```

After any change under `src/`, the order that matters is **run_workflow → verify_corpus →
export_all**. Skipping the first leaves `data/` written by older code, and the checker will
correctly fail artifacts that no longer match the rules.

## The three agents

The project brief allows a maximum of three working roles. There is no manager
agent, no memory layer and no autonomous browsing loop — the flow is strictly
linear so that it stays explainable and debuggable.

| Agent | File | Job |
|---|---|---|
| **1 · Source Collection** | `src/agent1_collect.py` | Reads `robots.txt`, fetches the curated seed URLs first and fills gaps by pattern, caches every page, and records **why** each page was kept, skipped or never found. |
| **2 · Evidence Extraction** | `src/agent2_extract.py` | Cuts each page into heading-anchored blocks and matches them against `config/field_dictionary.yaml`, keeping the heading, snippet, matched terms and source URL as evidence. |
| **3 · Brief Review** | `src/agent3_review.py` | Verifies coverage, identifies missing categories, highlights weak evidence and conflicts, and assembles the brief. It adds no extraction. |

`src/orchestrator.py` is the only place the three are wired together.

## How extraction works, in one paragraph

A page is split into **blocks** — one heading plus the paragraphs beneath it.
Each block is tested against a plain list of phrases held in a YAML file
(`config/field_dictionary.yaml`), matched as whole words, not as regular
expressions. When a block matches, the whole block is kept: heading, snippet,
matched terms and source URL. That produces evidence a human can check, and adding
coverage for a new vendor is a matter of adding a phrase to a data file rather than
editing code. Vendors write the same fact very differently — `SOC 2 Type II`
(Linear), `SOC 2 Type 2` (GitLab), `SOC 2 and 3` (Postman),
`Service Organization Controls` (Linear), or as a logo with alt-text `AICPA SOC
logo` (Atlassian) — which is exactly why a phrase list beats a pattern.

**A field's `value` is always a verbatim quote, never a generated summary.** There
is no language model in this prototype, so any "summary" would be machine-assembled
text a reviewer could not trace back to a page.

## Honesty guarantees

The failure this project exists to prevent is not a missing answer. It is **a
confident answer about a company that nobody checked.** Four mechanisms produce
that, all measured on real pages, and each is guarded:

- **A page can return HTTP 200 and contain no words.** Atlassian's Jira product
  page yields 52 characters from 898 KB. Agent 1 measures readability at
  collection; Agent 2 refuses to treat an unreadable page as searched.
- **A 404 means our URL guess was wrong, not that a vendor is silent.** JetBrains'
  security page 404'd six times before the seed was corrected; it publishes *"SOC 2
  Type II and GDPR compliance"* in plain prose. Page types that were never located
  are reported, not omitted.
- **A quote that passes every check can still be the wrong sentence.** Ranking is
  treated as policy, not plumbing, and the printed quote must be the evidence that
  earned the label.
- **A missing cache must not become a statement about a vendor.** With the HTML
  cache absent — the shape of this archive — Agent 2 once returned every field as
  NOT_FOUND under the sentence *"nothing matched on any page we could read"*, about
  pages nobody had opened. It now attaches a caveat that reaches the brief, and the
  orchestrator refuses the run outright.

Each brief reports **three numbers, never one**: how much evidence was found, how
good it is on the client's confidence definition, and how much could actually be
checked. Read together they separate a vendor we understand from one we merely
found text about. `docs/confidence_rules.md` derives all three.

## Layout

```
app.py       the Streamlit review interface, five tabs in workflow order
config/      vendors.yaml · field_dictionary.yaml · settings.yaml   <- all policy lives here
src/         agent1..3 · orchestrator · review_rules · fetch · parse · schema · export
tools/       run_workflow.py · verify_corpus.py · review_all.py · export_all.py
data/        corpus/ (canonical JSON) · briefs/ · exports/ · cache/html/ (local only)
docs/        architecture · confidence_rules · evaluation · assumptions_limitations · client_guidance
brief.txt    the project brief, extracted verbatim from the PDF
tests/       152 offline tests + five HTML fixtures modelled on real vendor pages
screenshots/ the interface, tab by tab, for GitLab and JetBrains
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
dependency on paid databases or enterprise tooling. Also excluded by our own
design: manager agents, memory layers, autonomous browsing loops, and JavaScript
rendering.

Collection policy: `robots.txt` checked before every fetch (RFC 9309 semantics),
2-second delay per domain, honest User-Agent, hard cap of 10 kept pages and 20
requests per vendor, no JavaScript rendering, everything cached on first fetch.
See `config/settings.yaml` and `docs/assumptions_limitations.md`.
