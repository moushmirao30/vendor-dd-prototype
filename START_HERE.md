# START HERE — for a new session picking this project up cold

**Written 19 August 2026 because the assistant's project memory was lost.**
Everything that was in memory is now in this repository, where it cannot be lost
again. That relocation is the lesson: **project memory is convenient and it is not
durable. The repo is.**

---

## Read these four, in this order, before touching anything

| # | File | Why |
|---|---|---|
| 1 | **`HANDOFF.md`** | Everything a fresh session needs. ~80 KB. Its §0 is how to work with me; §5 is all 47 defects; §7 is where things stand; §11 is the live brief-compliance matrix; §12 is the compliance audit |
| 2 | **`docs/client_guidance.md`** | **The client's written reply of 18 August, in full. It outranks every other decision in this repo.** Read it before ANY design choice |
| 3 | **`brief.txt`** | The project brief, extracted verbatim from `Project_Brief_1.pdf`. **Check compliance against this file, never against a summary of it** — four requirements were quietly unmet for nine days because nobody did |
| 4 | **`docs/assumptions_limitations.md`** | What was assumed and what the system structurally cannot do |

---

## The state, in one screen

**20 August 2026 = day 13 of 20. 7 days to the 27 August submission target,
9 to the 29 August deadline.** Day 1 was 8 Aug, so day N = 7 Aug + N.

*This line first read "19 August = day 12". The session that wrote it crossed a real
midnight and the note was wrong before anyone read it — Rule 3, committed by the session
that wrote Rule 3. **Check the clock against the machine at the start of every session,
before trusting any date in this repository, including this one.***

- **All code is built.** Three agents, orchestrator, export layer, source manifest,
  all five Streamlit tabs. **152 tests. `verify_corpus.py` 0 FAIL on all 7 vendors.**
- **9 of 10 brief deliverables complete.** Missing: **`docs/test_cases.md` — one item.**
  Counted 20 Aug against `brief.txt` verbatim. `docs/code_walkthrough.md` is **not** on the
  brief's list; it is our own idea, worth writing and the first thing to drop.
- **The corpus is FROZEN at 13 August. Do not re-collect** — every measured figure
  in every document was fact-checked against it, and vendor pages have moved since.
  `tools/run_workflow.py --mode replay` re-reads the frozen cache and is safe.
- Repo: `https://github.com/moushmirao30/vendor-dd-prototype` (private, `master`).
- Submit to **projects@firstquadrantlabs.com** AND upload to the LMS.

```powershell
cd "C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\vendor-dd-prototype"
.venv\Scripts\activate
pytest -q                                    # expect 152
python tools/run_workflow.py --mode replay   # 1->2->3, offline, from the frozen cache
python tools/verify_corpus.py                # expect 0 FAIL — READ THE WARN ROWS
python tools/export_all.py                   # refresh data/exports/
streamlit run app.py                         # http://localhost:8501
```

**Order matters:** after any change under `src/`, run `run_workflow --mode replay`
FIRST, then `verify_corpus`, then `export_all`. Skipping the replay leaves `data/`
written by older code and the checker will correctly fail artifacts that no longer
match the rules.

---

## What to do next, in priority order

1. **Commit and push. Do this before reading anything else.** Four files are untracked and
   exist on one laptop only — `docs/client_guidance.md`, `brief.txt`,
   `docs/assumptions_limitations.md` and this file. The repo's own lesson is that memory is not
   durable and the repo is; four of the files carrying that lesson are not yet in the repo.
2. **Click the research-focus filter once by hand** in the running app. Its wiring
   is proven by AppTest but no browser has confirmed it visually.
3. **`docs/test_cases.md`** — a brief deliverable. **Keep it short.**
4. **A one-page executive summary at the top of `docs/evaluation.md`** — the
   three-axis table, the 16.3% figure, the four failure modes. Highest-value
   remaining item.
5. Add defects 40–47 to `docs/evaluation.md`.
6. **`docs/code_walkthrough.md`** — the one that lets me defend the code in review.
   **Not a brief deliverable.** Optional, and the first thing to cut.
7. Delete `_to_delete/` before packaging. Gitignored, so git will never remind you.

**Feature freeze is 21 August. Everything after it is prose.**

---

## ⚠ The standing risk is volume, not missing work

~180 KB of prose across five documents. Every page is defensible; nobody will read
them all. The brief requires the **Streamlit interface** to be usable by a
non-technical operations lead — not the documents — and the interface is good.
**Write nothing longer. The repo needs a shorter entry point, not more depth.**

---

## The five rules that caught almost everything

**1 · VERIFY BEFORE PRESENTING.** Do not report a finding you have not reproduced.
Run it, attack your own result, correct it, then show it. Say explicitly what you
checked, what you could **not** check, and why. *Three of four candidate findings
on 18 Aug were false. One of nine in the compliance audit was false. Checking is
not overhead; it is the job.*

**2 · STRICTLY ADHERE TO THE BRIEF.** Before adding a feature, field, document or
dependency, name the line in `brief.txt` it serves. Before removing one, name the
line that permits it. Departures from the brief's suggested approach must be
written down with their reason — a silent omission is a compliance failure even
when the engineering choice is right.

**3 · RE-READ THE CLOCK EVERY SESSION.** Absolute dates only, cross-checked against
`git log`. Three date errors happened here in both directions, including one where
a long session crossed a real midnight and a correct note became wrong.

**4 · ONE RULE, ONE PLACE.** Four defects came from a single rule implemented twice
and drifting. Every judgement lives in `src/review_rules.py`; `verify_corpus.py`
and `agent3_review.py` both import it.

**5 · READ YOUR OWN WARN ROWS.** `verify_corpus` printed *"Agent 3 owes a
coverage-aware score here"* on every run for days. That was defect 42, in plain
sight. **A warning nobody reads is a defect nobody fixes.**

---

## The one sentence the whole project resolves against

> **The dangerous failure is not a missing answer. It is a confident answer about a
> company that nobody checked.**

Every design argument in `HANDOFF.md` resolves against that line. When in doubt,
ask which option makes an unchecked claim less likely to reach a reader — and
remember that the project has twice committed that failure itself, both times by
putting an honest record in the audit trail and a misleading sentence in the
document a human actually reads.

---

## How to work with me — the short version

Full version in `HANDOFF.md` §0. I am Moushmi; you are my **mentor/advisor**, not
my assistant.

- **Never open with agreement.** First sentence challenges an assumption or names a
  gap.
- **Tag confidence:** `[Certain]` / `[Likely]` / `[Guessing]`. If most of a reply is
  guessing, say so first.
- **Uncomfortable truth first** — line one, not paragraph three.
- **Disagree with structure:** "I disagree because X. Instead do Y. The risk in your
  approach is Z."
- **Hold your position under pushback** unless I give you genuinely new information.
- **I know Python basics only.** Write the code, then explain it line by line so I
  can defend it in a review. Never hand over unexplained code.
