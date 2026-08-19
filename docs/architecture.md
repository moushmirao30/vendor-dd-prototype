# Architecture note

**Vendor Due-Diligence Research Workflow Prototype**
First Quadrant Labs internship project · document written 12 August 2026

---

## 1. What this system is, in one paragraph

A bounded three-agent workflow that reads **public** vendor web pages, extracts a fixed set of
fields from them, and assembles a first-pass research brief in which **every statement is a quote
from a named page**. It runs on a standard laptop with no API key, no account, no GPU and no paid
service, and after one collection run it replays entirely offline. It is a research aid for a human
reviewer. It does not score vendor risk, grant approval, or make a procurement decision, and it
says so on every screen and in every export.

## 2. How the design maps to First Quadrant Labs' four stages

| FQL stage | What it means here |
|---|---|
| **Discovery & Assessment** | One category was chosen (developer productivity tools) and seven vendors within it, at three deliberate difficulty tiers. Each vendor's pages were opened by hand before any code ran, and what was actually found is recorded in `config/vendors.yaml` under `observed_2026_08_10`. The field set was derived from those pages, not from a wish list. |
| **Strategy & Solution Design** | Three agents, strictly linear, no loops. A rule-based extractor rather than a language model. A written confidence rule (`docs/confidence_rules.md`) that a human can apply by hand to any page and get the same answer the code gets. All policy in YAML, all behaviour in Python. |
| **Development & Deployment** | Python, Streamlit, `requests`, BeautifulSoup, `trafilatura`, pandas. JSON as the canonical store. 150 offline tests. One command to run: `streamlit run app.py`. |
| **Monitoring & Optimization** | Every agent emits an audit trail that persists to disk and replays. Every page's content is hashed so a later run can detect the vendor changed it. The confidence of every field is visible next to the quote that produced it, so the system's own weaknesses are legible to the person using it rather than buried. |

The explainability requirement is not a section of this document. It is the reason the system is
shaped the way it is: **a reviewer can trace any sentence in a brief back to a heading on a page,
and can see which clause of a written rule produced its confidence label.**

## 3. The pipeline

```
config/vendors.yaml          config/field_dictionary.yaml     config/settings.yaml
  7 vendors, 44 seed URLs      8 fields, 112 phrases            all policy: UA, delays,
  21 url_patterns over         preferred_source_types           caps, thresholds,
  5 page types                 negative_terms                   noise_phrases
        │                              │                                │
        ▼                              ▼                                ▼
┌───────────────────┐        ┌────────────────────┐        ┌────────────────────┐
│ AGENT 1           │        │ AGENT 2            │        │ AGENT 3            │
│ Source Collection │───────▶│ Evidence Extraction│───────▶│ Brief Review       │
│                   │ Source │                    │Extract-│                    │
│ robots.txt → HTTP │ Records│ raw HTML → blocks  │edFields│ coverage, missing, │
│ → cache → text    │        │ → term match →     │        │ weak evidence,     │
│                   │        │ rank → quote       │        │ conflicts → brief  │
└───────────────────┘        └────────────────────┘        └────────────────────┘
        │                              │                                │
        ▼                              ▼                                ▼
 data/cache/html/            data/corpus/                     data/briefs/
 v2_<hash>.html              <slug>.json         (canonical)  <slug>_brief.json
 (offline replay, NOT        <slug>_run.json     (trail)      + data/exports/
  submitted — §10)           <slug>_fields.json  (+ trail)      CSV · Markdown · manifest

                    ╔══════════════════════════════════════╗
                    ║  src/orchestrator.py                 ║
                    ║  the ONLY place 1 → 2 → 3 are wired  ║
                    ╚══════════════════════════════════════╝
```

Data flows one way. Agent 2 never asks Agent 1 for more pages; Agent 3 never asks Agent 2 to
re-extract. If a page is missing, that absence travels forward as a recorded fact.

### The orchestrator, and why the handoffs needed an owner

`src/orchestrator.py` holds every handoff between the three agents, once. Before it, the same
wiring was re-derived in four places — `app.py`, `tools/review_all.py`, `tools/export_all.py` and
the tests — and **defect 34 proved what that costs**: the fix for defect 26 was wired to an audit
step Agent 1 never emitted, so a shipped safeguard executed zero times across seven vendors and
every unit test still passed. A handoff nobody owns can stop happening silently. `run_workflow`
owns it, records what it passed as a `Stage`, and is the only caller of Agent 3 in the codebase.

**It exposes three modes, and the third one is an architecture decision, not a convenience:**

| Mode | Agent 1 | Agent 2 | Agent 3 | Needs |
|---|---|---|---|---|
| `collect` | fetches live | extracts | reviews | the network |
| `replay` | loads corpus | **re-reads cached HTML** | reviews | `data/cache/html/` — no network |
| `review` | loads corpus | loads saved fields | reviews | **neither** |

`review` is the default, because it is **the only mode a fresh clone of the submitted archive can
run** — the client asked on 18 August 2026 that the 22 MB cache of verbatim third-party HTML not be
redistributed. Naming the mode is how that instruction and their other one — *demonstrate offline
replay* — stop contradicting each other: **the archive replays the review stage offline out of the
box, and replays the full pipeline once the reviewer re-collects.**

A **preflight** guards the difference. If any readable page has no cached HTML, `replay` refuses
outright and names `review` as the alternative, rather than degrading into it. That is defect 40:
with the cache deleted, Agent 2 silently returned eight NOT_FOUND fields per vendor and the brief
reported all seven vendors as publishing nothing, under the sentence *"nothing matched on any page
we could read"*, about pages nobody had opened. **A mode that quietly becomes a different mode is
indistinguishable from one that worked.**

### The three contracts

Defined once, in `src/schema.py`, as dataclasses:

| Object | Produced by | Carries |
|---|---|---|
| `SourceRecord` | Agent 1 | one collected page: URL, page type, title, cleaned text, HTTP status, cache path, `content_sha256`, `robots_allowed`, which text extractor was used |
| `ExtractedField` | Agent 2 | one answer: `status` (FOUND / PARTIAL / NOT_FOUND), `value` (a **quote**), `confidence`, and a list of evidence, each with heading, snippet, matched terms and source URL |
| `VendorBrief` | Agent 3 | the assembled brief: fields, missing/unclear list, review flags, vendor confidence, and the disclaimer |

Three agents handing dictionaries to each other invent divergent keys by day ten and the interface
silently shows blank fields. A schema file makes the handover a contract instead of a convention.

## 4. Agent 1 — Source Collection

**One job:** decide which public URLs are worth reading, confirm they exist, store them. It
interprets nothing.

**Hybrid discovery.** Three options were considered: a hand-curated URL list (honest, but the
"agent" does no work); pure automatic discovery (impressive, but silently misses vendors like
GitHub whose trust content is not at a guessable path); or **guess, verify, fall back** — chosen.
Agent 1 tries the human-curated seed for each page type first, then probes `url_patterns` for any
page type it still lacks. Every URL is recorded with the HTTP status it returned and whether it
came from a seed or from discovery.

**Seeds first, and why that order was learned the hard way.** Discovery originally ran first, on
"first HTTP 200 wins". For GitLab's `docs` that meant probing `/docs`, `/docs/`, `/help`, then
`/support` — and `/support` returned 200 while redirecting to a single Zendesk help *article*. The
agent preferred one support article over `docs.gitlab.com`, the vendor's entire documentation site,
because both answered 200. **A 200 means the URL exists, not that it is the right page.** A
human-checked URL now outranks a guessed one, which also makes fewer requests — the politer
outcome.

**Collection policy** (all of it in `config/settings.yaml`, none of it in code):

- `robots.txt` read before every fetch, with **RFC 9309** semantics: 2xx parse, 4xx other than 429
  means unrestricted, 429 and 5xx mean disallow. Python's stdlib parser is stricter than the RFC
  and treats a 403 on `robots.txt` as disallow-all; GitLab's CDN returns 403 to urllib's default
  user-agent, which silently dropped four of six sources and blamed the vendor. We fetch
  `robots.txt` with our own user-agent and record which branch of the rule fired.
- Honest `User-Agent` naming the project. **No browser impersonation, ever.** A vendor that refuses
  our honest identity is recorded as a finding for manual review — the brief bans bypassing access
  controls, and a tool that quietly evades them cannot be defended.
- 2 seconds between requests to the same domain. 10 pages kept, **20 requests made** per vendor —
  two separate caps, because capping only successes means the politest outcome makes the fewest
  requests and the rudest makes the most, which is backwards.
- No crawling, no link-following. Each candidate is one request.
- **No caps applied silently.** When the request budget stops a probe, a `budget-stop` step is
  written to the trail naming the page type that was never attempted.
- Every page cached to disk on first fetch, keyed by a versioned content hash. After one run the
  whole workflow replays offline and a vendor changing their site cannot break a demonstration.

## 5. Agent 2 — Evidence Extraction

**One job:** turn collected pages into structured fields, each carrying the exact text it came
from. It decides nothing about the vendor. **It does not write sentences. It quotes.**

### Blocks, not pages

A page is cut into **blocks** along its own headings: one block is one heading plus the paragraphs
and list items beneath it. Each block is then tested against a plain phrase list.

A match tells you a phrase exists. A block tells you what the page *said*, under which heading —
which is what a reviewer needs and what the brief calls a source-backed evidence snippet.

### A phrase list, not a regular expression

Vendors write the same fact differently. Observed on real pages, 10 August 2026:

| Vendor | How it writes "SOC 2" |
|---|---|
| Linear | `SOC 2 Type II` — and separately, spelled out: `Service Organization Controls` |
| GitLab | `SOC 2 Type 2` |
| Postman | `SOC 2 and 3` |
| Atlassian | an image, whose `alt` attribute reads `AICPA SOC logo` |
| GitHub | does not publish it |

A regex grows one hack per vendor until nobody can read it, and it still cannot tell you what the
page said. `config/field_dictionary.yaml` is a list of phrases a non-technical reviewer can read,
audit and extend without touching Python. Every term marked `# observed` was copied from a real
page.

**Matching is whole-token, not substring.** This is not a detail. With a bare substring test,
across GitLab's seven pages the term `sla` matched 13 times and only 2 were the acronym — the other
11 were the word "Slack". `cli` matched 9 times and *never once* meant the command line: click,
clicked, clicking, client, decline, declined. GitLab's uptime field was reported FOUND / High,
quoting its privacy policy on third-party vendors. `parse.term_in` now requires a term to stand as
its own word or phrase, with the boundary applied only at ends of the term that are themselves
alphanumeric so that a term like `% uptime` still matches `99.99% uptime`.

### The decision that saved the project

**Evidence extraction reads raw HTML. It never reads `collected_text`.**

`collected_text` is the cleaned, human-readable version of a page, produced by `trafilatura` for
people browsing the corpus. On GitLab's security page `trafilatura` kept **12%** of the visible text
and discarded every certification sentence with it. Had extraction been built on that field, this
system would have reported "no certifications found" for a vendor that publishes them in plain prose
under an `<h3>SOC Certification</h3>` heading.

*(Re-derived 19 August 2026 against the frozen corpus. This paragraph previously said "7.6%, 487 of
6,415 characters", measured on a collection two days older. The figure decayed the moment the page
moved — the same failure as defect 33 — and `SourceRecord.text_extractor` now records the fallback
and its reason on every row, so the number can always be re-read rather than remembered:
GitLab's security row reads `visible-text (trafilatura kept only 12% of the page)`.)*

It did not, because extraction works from the raw HTML in the cache, which also preserves the
heading structure that makes a snippet meaningful. `main_text` now additionally refuses a cleaner
that keeps less than 15% of a page or fewer than 800 characters of a substantial one, and records
which extractor was used in the corpus so a reviewer can see which pages needed the fallback.

**Two independent paths to the same page, one for humans and one for evidence, meant a failure in
one did not become a wrong answer in the other.** That is the single most valuable structural
decision in this project, and it was not foresight — it was separation of concerns paying off under
test.

### `value` is a quote, never a summary

There is no language model here. Anything reading like a written summary would have to be assembled
by string-joining, and a machine-assembled sentence is exactly the kind of statement a reviewer
cannot trace to a source. So `value` is the single sentence from the page containing the matched
term, copied character for character. When no sentence is long enough to stand alone — a bare
bullet list of certifications — the surrounding block is returned instead, because `SOC 2 and 3`
alone tells a reviewer nothing about what was claimed.

### Ranking is policy, not plumbing

Only `max_evidence_per_field` items survive, and the top one becomes the quote printed in the
brief — so the sort order decides what a human reads. Evidence is ordered by: confidence level →
where the term sat (prose, heading, image alt-text) → whether the page is the field's natural home
(`preferred_source_types`) → whether the page is authoritative → how many distinct terms matched →
**shorter block first**.

That last clause is reversed from the obvious choice, deliberately. Sorting by longest snippet
seems generous — more context for the reviewer — but the longest blocks on any vendor site are
boilerplate slabs: a whole status board, an entire pricing table. It put 600 characters of
"Website Operational API Operational…" above "GitLab maintains a SOC 2 Type 2 report…", which
ranked third and never became the field's value. Past the length floor, a short block that mentions
the term is a focused claim; a long one is furniture that happens to contain the word.

`preferred_source_types` **orders** evidence and never filters it. GitLab genuinely states its
FedRAMP position on its *pricing* page; suppressing that because it was "the wrong page" would be
the extractor overruling the vendor.

### Citations must contain what they cite

An evidence card that reads *"matched `sla` in the body"* above text with no "SLA" in it is worse
than no citation, because a reviewer who checks it concludes the tool is lying rather than
truncating. Two separate bugs produced exactly that — a snippet taken from the start of a block
rather than around the match, and a snippet taken from a block's prose when the match was in an
image's `alt` attribute. Measured on the GitLab corpus: **8 of 92 candidate evidence blocks were
orphan citations; now 0** — re-checked 19 August across all seven vendors, 385 candidate blocks and
122 shown after the three-per-field cap, still 0. Guarded by a property test over every fixture
rather than by two examples.

### 5.1 The difference between "not published" and "we could not read it"

This is the most consequential rule in the system, and it exists because of one measurement.

An HTTP 200 means a server answered. It does not mean the answer contained words. Atlassian's Jira
product page satisfies every check Agent 1 makes — 200, robots-allowed, cached, `fetch_ok` — and
yields 52 characters of text and no heading blocks at all. Every field sourced from that page will
match nothing.

Reported naively, the brief would then tell a procurement team that **Atlassian does not publish
pricing information.** Atlassian publishes it perfectly well. We cannot read it. Those are entirely
different findings, only one of them is true, and the false one is a statement about a real company
in a client-facing document. Of every defect found in this project, this is the only one capable of
that.

So usability is measured at collection and carried forward:

- Agent 1 records `block_count` and `content_usable` on every `SourceRecord`, and writes an
  `unusable-page` line into its audit trail naming the byte count, the character count and the block
  count, so the judgement is auditable rather than a bare boolean.
- Agent 2 does not count an unusable page as searched. Its `no-match` trail entry reads *"no match
  across 2 **readable** page(s)"*, followed by a caution naming the pages that could not be read.
- The `ExtractedField` itself carries that caution, because **a reviewer reads the brief, not the
  audit trail.** A NOT_FOUND resting on an unreadable corpus arrives with "verify this field by hand
  before recording it as not published" attached to it.
- And the inverse is enforced too: when every collected page was readable, NOT_FOUND is a genuine
  finding about the vendor and is **not** hedged. A caveat attached to everything is a caveat nobody
  reads.

The threshold lives in `config/settings.yaml` (`min_usable_text_chars`, currently 300) and was set
from measured pages, not chosen in the abstract.

## 6. Agent 3 — Brief Review

The client confined this agent in writing on 18 August 2026: *"focus on review and synthesis rather
than introducing another complex intelligence layer. It should verify evidence coverage, identify
missing categories, highlight conflicts or weak evidence, and prepare the final brief."* It adds no
extraction and reads no new pages. That is why it can be handed the corpus, the fields and Agent 1's
audit trail all at once without the flow ceasing to be linear.

### Every judgement lives in one module, imported twice

`src/review_rules.py` holds the predicates. `tools/verify_corpus.py` imports them to decide whether
a corpus may be committed; `src/agent3_review.py` imports them to decide what the reviewer is told.
**The alternative — writing them twice — is the failure this project has already made three times:**
defect 15 (the confidence rule disagreeing with its documentation), defect 36 (two docstrings
disagreeing, which silently killed the `PARTIAL` status), and defect 41 (one over-hedging rule
living in three files, two of them stale, so a single brief contradicted itself). A build-time
checker and a shipped brief computing "coverage" two different ways is the same bug wearing a
fourth hat.

What is deliberately **not** in that module: anything requiring meaning. These are mechanical
predicates over structure — which page, which status, is there a caveat, is the cited term visible
in the printed quote. They cannot tell you whether a sentence is *true*, or whether it answers the
question a procurement team actually asked. Saying so plainly is the point of the prototype.

### Three axes, because one number hid the thing that mattered

| Measure | Question | Field on `VendorBrief` |
|---|---|---|
| **Evidence** | How **much** quotable material was found? | `evidence_score`, `evidence_band` |
| **Confidence** | How **good** is it, on the client's definition? | `confidence_band`, `confidence_counts` |
| **Coverage** | How much could **actually be checked**? | `coverage_verified`, `coverage_total`, `coverage_caveated` |

Until 19 August the first pair was called `confidence_score` / `overall_confidence` and was computed
entirely from the extraction axis — the sentence-length measure the client had asked us not to base
confidence on. Postman and Sentry both read **10/10 → High** on coverage 2/5 and 5/5, above field
cards that each said Medium (defect 42). Confidence is reported as **counts, not a score**:
compressing three levels into 0–10 needs thresholds chosen while looking at our own seven vendors,
and a count cannot be tuned. The band is the weakest core field — a stated principle, not a
calibrated cut-off. Full derivation in `docs/confidence_rules.md` §Step 6.

### What it flags, all firing on real data

- **Evidence from outside a field's natural home.** On GitLab, integrations/API and
  support/documentation both draw their strongest evidence from the *privacy policy*, because that
  page is authoritative and full of complete sentences. The match is real; the finding is weak.
- **Gated evidence.** Sentry publishes that its SOC 2 reports are *"available to customers … upon
  request"* — a genuine claim whose proof cannot be read from public sources.
- **A claim not present in the sentence that earned the label** — nine blocks across the corpus.
- **Not found vs could not be evaluated**, per field, tested against *that field's own* home page.
  Testing the vendor's worst page instead hedged a genuine JetBrains finding into a tool limitation
  (defect 39). Currently 3 could-not-be-evaluated against 7 genuine not-founds.

### What it does not flag, and why that is reported rather than hidden

`conflicting_values` compares numeric and categorical values for the same field across sources —
percentages, audit levels. It is unit-tested and **returns zero on the real corpus.** That is
reported as a finding, not omitted: semantic contradiction between two prose statements needs a
language model this prototype deliberately does not have.

An earlier negation-based detector fired on three of seven vendors and **every hit was false** —
it compared three blocks of the *same* privacy policy against each other, because a privacy policy
contains both "we do not sell your data" and ordinary positive statements. It was **deleted, not
tuned**. There is no threshold that turns "this paragraph contains the word not" into evidence of
contradiction, and **a detector that produces false positives is worse than one that produces
nothing, because it teaches the reviewer to skim past flags — and the flags are the product.**

## 7. The interface

One Streamlit page, five tabs in workflow order — Sources, Agent steps, Evidence, Vendor brief,
Export — so a non-technical reviewer can follow the process left to right and see what each agent
did rather than only what it produced.

Three principles the interface earned the hard way:

1. **An agent that succeeds silently is indistinguishable from one that fails silently.** Agent 2
   completes in under two seconds and changes only one tab. Pressed from the Sources tab, it
   produced no visible change whatsoever, and the reasonable conclusion was that it had not worked
   — while its output sat on disk. Both agents now write a confirmation banner *above* the tabs,
   visible from any of them.
2. **Run or replay are two features.** The brief asks the interface to let a reviewer "run **or
   replay** the workflow". Results initially lived only in Streamlit's session state, so a browser
   refresh erased the entire audit trail while the corpus sat on disk. Both agents now persist their
   trail alongside their output, and the interface labels which run it is showing.
3. **Confidence is never shown without its evidence.** Every field expands to the quote, the terms
   that matched, where they matched, the page type and a clickable source URL. The summary table
   includes a `From` column naming the page each top quote came from, precisely so a reviewer can
   notice when an integrations claim arrived from a privacy policy.
4. **No axis is ever shown alone.** The brief tab draws evidence, confidence and coverage side by
   side, because a single number called "confidence" made Postman indistinguishable from Sentry
   while resting on pages nobody could read (defect 42). A test asserts all three reach the screen.

### The chain, made literal

The client asked in writing on 18 August 2026 that the interface show one path end to end:

```
Source → Extracted Evidence → Structured Field → Confidence → Review Flag → Final Brief
```

Tab 4 labels it exactly that way, one numbered link per field, so a reviewer can follow a single
statement from the page it came from to the line in the brief. **That is the difference between
auditing the tool and trusting it** — and every defect in this project was found by precisely that
act: looking at one link and asking whether it follows from the one before.

Tab 4 calls `orchestrator.run_workflow` in `review` mode rather than calling Agent 3 directly.
Agents 1 and 2 keep their own buttons, because each has its own spinner and a reviewer is meant to
watch them run one at a time; Agent 3 does not, and `app.py` is the worst possible place for a fifth
copy of the wiring (§3). A test asserts both halves of that split via the AST, so it cannot drift.

### Verified in a browser, not only in AppTest

`streamlit.testing.v1.AppTest` checks what the app hands Streamlit. It cannot see what a browser
draws, and this project has already shipped a table that rendered as an empty grey box while its
data was fine. Both new tabs were therefore rendered in headless Chromium and screenshotted before
being called done — which immediately caught `st.metric`'s `delta` prefixing a directional arrow, so
"all verified" rendered as "↑ all verified". **An arrow pointing nowhere meaningful, on a number a
procurement reader is meant to trust, is a small instance of exactly the failure this tool reports.**

The disclaimer sits in the page chrome, not in a tab, so it cannot be absent from any screen or any
screenshot.

## 8. Storage

**JSON is canonical; CSV is an export.** Page text contains commas, quotation marks and newlines,
and a CSV primary store corrupts that silently — the worst failure mode available, because nothing
reports an error. SQLite was considered and rejected: nothing here needs queries or transactions,
and a plain JSON file is one a reviewer can open, read and diff without a tool.

Cache paths in the corpus are **repo-relative**. They were absolute (`C:\Users\...`), which meant a
corpus replayed only on the machine that wrote it — while the README promised offline replay to
everyone — and published a personal home directory inside a client-facing artifact.

## 9. Choices made, and what was declined

| Decision | Alternative rejected | Reason |
|---|---|---|
| Rule-based extraction | an LLM extractor | keeps "runs on a standard laptop, no API key, low cost" literally true, and makes every output traceable to a phrase in a YAML file a reviewer can read. Expect **more** NOT_FOUND results than an LLM would give; that is the honest answer and the rubric rewards it. Any model backend stays behind an off-by-default flag. |
| Plain Python orchestration | LangGraph, CrewAI | a three-step linear flow has no state machine to manage. A framework here would add a dependency, a vocabulary and a failure surface, and would remove the thing being demonstrated: that each step is legible. |
| One heading-block per match | sentence-level or whole-page matching | a sentence loses the context a reviewer needs; a page loses the location. |
| Policy in YAML | constants in Python | the interface tells reviewers that policy lives in the config files and they may change it. That has to be true, which is also why the config cache is keyed on file modification time. |
| 8 fields, 5 of them scored | more fields | data residency, encryption and uptime are absent from most vendors' pages by convention rather than by omission; scoring them would make the score mean less. |
| 7 vendors across 3 difficulty tiers | 7 easy vendors | Atlassian (certifications as images), GitHub (nothing published) and JetBrains (unverified URLs) are in the set **so that the evaluation has real failure modes to report**. A prototype that only ever succeeds has not been tested. |

## 10. Scope boundaries

Deliberately **not** built, per the brief: manager or supervisor agents · memory layers ·
autonomous browsing loops · a production procurement platform · official vendor risk scores ·
compliance, legal or security approval · access to private vendor portals · any dependency on paid
databases or enterprise tooling · aggressive scraping or restriction bypassing · JavaScript
rendering.

Two of those deserve a note rather than a line.

**JavaScript rendering is a real limit, and it is now measured.** An earlier draft of this document
claimed rendering was "unnecessary, not merely excluded", on the strength of status pages:
Statuspage-hosted pages, which is where uptime information actually lives, are server-rendered and
read correctly with `requests` and BeautifulSoup. That much is true. The general claim was not, and
collecting Atlassian on 12 August 2026 disproved it: its Jira **product** page returns 898 KB of
HTML and yields **52 characters** of visible text and **zero** heading blocks; its **pricing** page
yields **66 characters** from 1.21 MB. Both are rendered in the browser. Atlassian's security, privacy,
support and status pages read fine.

So the honest statement is narrower: **no-JavaScript costs nothing on trust, legal and status pages,
and costs everything on modern marketing pages.** That is a favourable trade for this project, whose
fields come mostly from the former — but it is a trade, not a free choice, and the consequence had to
be built for rather than argued away. See §5.1.

**Restriction bypassing is excluded on principle, not for want of technique**: a vendor's refusal is
data, and a tool whose findings depend on ignoring that refusal cannot be presented to a client.

## 11. Known limits of the architecture

- It measures how well-evidenced a statement is, **not whether the statement is true, and not
  whether it is about the thing you asked.** GitHub's `security_trust` value is
  *"GitHub's API stays secure with ISO, SOC 2, and GDPR."* — a full sentence on the vendor's own
  security page, so both axes rate it High. It is a claim about the **API**, not the platform. No
  rule-based system reads scope. This is a human-review case by design, which is why the quote and
  its URL are printed beside every label.

  **The history of that one sentence is worth more than the example.** It is a bare `<h2>` with no
  paragraph under it. Until 18 August 2026 the extractor quoted a block's *body*, so this heading
  produced an **empty quote**, scored `heading_only`, ranked **9th of 9** and was dropped by the
  three-per-field cap — the field's own top-priority page contributed nothing, and the value came
  instead from GitHub's **terms of service**: *"…the content of your Account and its security are up
  to you."*, matching one term. Fixing it took three changes, because any one alone did nothing:
  quote the heading when there is no body, score the **sentence** rather than the HTML tag, and rank
  on the statement rather than the tag (defects 27 and 28). An earlier version of this section
  asserted the High rating before it was true. **A claim that turns out to be accidentally right is
  worth less than a defect explained**, so the mechanism is recorded here rather than the verdict.
- It rewards a vendor with a long, well-written privacy policy. On the GitLab corpus, three of five
  core fields drew their strongest evidence from that one page.
- It cannot read PDFs, images, or anything behind a login. Atlassian and GitHub lose points for
  publishing in formats this system deliberately does not parse — a limit of the method, not a
  judgement about those vendors.
- Numbers such as the 40-character claim floor and the 15% cleaner ratio are **chosen, not
  derived**. They live in `config/settings.yaml` so that a reviewer who disagrees can change one
  and re-run. The vendor-level **confidence** measure deliberately has no such number: it is
  reported as counts of core fields per level rather than a score, because compressing three levels
  into 0–10 would need two thresholds chosen while looking at these seven vendors, and a count
  cannot be tuned.
- **A written figure decays the moment the data moves.** Three worked examples in this repository
  have gone stale and been caught — in `config/settings.yaml` (defect 33), in
  `docs/confidence_rules.md`, and in §5 of this file. Every measured number here now names the date
  it was derived, and re-deriving them is treated as a defect-finding technique rather than
  housekeeping: it is how defects 33 and 43 were both found.

Every output states plainly that it is a first-pass internal research aid and that final review
remains manual. That sentence is the architecture's conclusion, not its disclaimer: the system is
built to make a human reviewer faster and better informed, and it is built to be honest about
where it cannot help.
