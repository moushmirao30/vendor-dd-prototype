# START HERE — for a new session picking this project up cold

**Written 19 August 2026 because the assistant's project memory was lost.**
Everything that was in memory is now in this repository, where it cannot be lost
again. That relocation is the lesson: **project memory is convenient and it is not
durable. The repo is.**

---

## Read these four, in this order, before touching anything

| # | File | Why |
|---|---|---|
| 1 | **`HANDOFF.md`** | Everything a fresh session needs. ~80 KB. Its §0 is how to work with me; §5 is all 55 defects; §7 is where things stand; §11 is the live brief-compliance matrix; §12 is the compliance audit |
| 2 | **`docs/client_guidance.md`** | **The client's written reply of 18 August, in full. It outranks every other decision in this repo.** Read it before ANY design choice |
| 3 | **`brief.txt`** | The project brief, extracted verbatim from `Project_Brief_1.pdf`. **Check compliance against this file, never against a summary of it** — four requirements were quietly unmet for nine days because nobody did |
| 4 | **`docs/assumptions_limitations.md`** | What was assumed and what the system structurally cannot do |

---

## The state, in one screen

**28 August 2026. THE PROJECT IS SUBMITTED.** Sent 27 August to
projects@firstquadrantlabs.com and uploaded to the LMS: `vendor-dd-prototype-submission.zip`,
**111 files, 3.0 MB**, built with `git archive` from `134eb6d` and verified by unzipping it and
running `pytest -q` inside the unzipped copy (153 passed, 1 skipped).

⚠ **A review came back on 28 August that does not describe this project.** It names this project
in its heading and then discusses TF-IDF, chunking, retrieval, 57 documents and 103 chunks, a
26-query evaluation set and a UI mockup — none of which exist here. **Read `HANDOFF.md` §13
before acting on any of it**; a reply asking Projects and HR to confirm which submission it
covers went out on 28 August. Do not implement its suggestions against this codebase.

*Earlier versions of this line were wrong twice, in both directions. **Check the clock against
the machine at the start of every session, before trusting any date in this repository,
including this one.***

- **All code is built.** Three agents, orchestrator, export layer, source manifest,
  all five Streamlit tabs. **154 tests passing and `verify_corpus.py` 0 FAIL on all 7 vendors,
  re-run on Windows on 23 August and re-run again the same day in a fresh clone (153 passed,
  1 skipped, one `cache-absent` WARN per vendor). Not recalled.** `verify_corpus` also raises
  **55 WARN**; those are findings about the vendors, ledgered in `docs/evaluation.md` §4.5.
- **10 of 10 brief deliverables complete.** Counted 20 Aug against `brief.txt` verbatim.
  `docs/code_walkthrough.md` was **not** on the brief's list; it was our own idea, drafted on
  23 Aug and cut the same day (see item 6). **Nothing the client asked for is outstanding.**
- **The corpus is FROZEN. Do not re-collect** — every measured figure in every document was
  fact-checked against it, and vendor pages have moved since. `tools/run_workflow.py --mode replay`
  re-reads the frozen cache and is safe.
  **It is not uniformly 13 August:** five vendors are **2026-08-13**, **GitLab is 2026-08-19**,
  and **JetBrains is 2026-08-22**. Never write "the 13 August corpus". Check
  `data/exports/source_manifest.csv`, column `date_collected` — `tools/export_all.py` was re-run
  on 27 Aug and the manifest is current.
- **`screenshots/` holds ELEVEN PNGs**, not twelve. Earlier notes counted `.gitkeep`. No shipped
  document states a count, so the client never saw the wrong number.
- **SUBMITTED 27 Aug** — zip emailed and uploaded to the LMS. **Feedback resolved 30 Aug:**
  the 28 Aug review described someone else's project, it was challenged, and First Quadrant Labs
  apologised and sent the correct one. **Read `HANDOFF.md` §14 before doing anything.**
- **Awaiting their answer** to the 1 Sept reply asking whether to resubmit a revised archive or
  carry the feedback into the next project. **Change no deliverable until they answer.**
- **One live defect, found by the client: three test counts across the documents (defect 56).**
  `README.md` 154 · `docs/architecture.md` 152 · `docs/evaluation.md` §5.2 152. Two edits, §8.
- Repo: `https://github.com/moushmirao30/vendor-dd-prototype` (private, `master`).
  **30 commits, HEAD `134eb6d`, pushed.**
- ⚠ **`.gitattributes` marks `HANDOFF.md`, `START_HERE.md` and itself `export-ignore`. DO NOT
  REMOVE THOSE LINES.** `HANDOFF.md` §0 is an internal working document and must never reach the
  client. The submission email therefore shipped the zip only and offered no repository link.
- Submitted to **projects@firstquadrantlabs.com** and the LMS on 27 Aug 2026.

```powershell
cd "C:\Users\Moushmi Rao\GEN-AGENTIC_AI\Projects\Research Project_1\vendor-dd-prototype"
.venv\Scripts\activate
pytest -q                                    # expect 154
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

**The project is submitted. Items 1–9 below are the pre-submission list and are all closed;
they are kept for the reasoning. The live list is these three.**

**A. SEND THE REPLY — today.** `_to_delete/reply_email.md` asks First Quadrant Labs whether to
   resubmit a revised archive by email or carry their feedback into the next project, and says
   why the question exists: the LMS does not allow resubmission once a project closes. The
   corrected feedback arrived 30 Aug; a reply after a week reads as disengagement.

**B. CHANGE NO DELIVERABLE UNTIL THEY ANSWER.** An unrequested revised archive is a different
   act from a requested one. This includes defect 56.

**C. WHEN THEY ANSWER, the work is four short items and it is in `HANDOFF.md` §7** — demo notes
   with numbered screenshots, a "what to do when a field is weak" section, the two test-count
   edits, and the opening of `docs/evaluation.md` §5 rewritten in your own words. **Three of the
   four make the package shorter.** Their fifth point was that parts of it read as heavily
   AI-assisted; the answer to that is not more writing.

---

### The pre-submission list — all closed, kept for the reasoning

1. ~~**Re-clone and run `python tools/verify_corpus.py` there.**~~ **DONE 23 Aug in `Desktop\clonetest2`: one `cache-absent` WARN per vendor, 0 FAIL, and `pytest -q` 153 passed / 1 skipped.** It was the last unverified thing in the
   project: defect 53 changed how the checker behaves when the HTML cache is absent, and a clone
   is the only place that shows. Expect **one `cache-absent` WARN per vendor**, not 49 FAILs.
2. ~~**Click the research-focus filter once by hand.**~~ **DONE 22 Aug** — that session is where
   defects 48–53 came from.
3. ~~**`docs/test_cases.md`**~~ — **DONE 20 Aug**, and `tools/export_all.py` re-run: the brief
   CSVs now carry **17 columns** including the disclaimer, confirmed by hand. **Re-run
   `export_all.py` after every change under `src/` — nothing automated will remind you.**
4. ~~**A one-page executive summary at the top of `docs/evaluation.md`.**~~ **DONE 20 Aug** — it
   is now the file's first section.
5. ~~Add defects 40–47 to `docs/evaluation.md`.~~ **DONE** — §5.1 (40–47), §5.2 (48–53),
   §5.3 (54–55), the last written 23 Aug.
6. ~~**`docs/code_walkthrough.md`**~~ **CUT 23 Aug.** Drafted, then removed before submission.
   Not a brief deliverable; a document written to help you defend the code is one you have to be
   able to defend; and the volume risk below decides ties. **Do not re-add it under deadline** —
   the reasoning in `src/` comments already does this job, and each one names its defect.
7. Delete `_to_delete/` before packaging (7 stale git lock files). Gitignored, so git will
   never remind you — and `git archive` already excludes it, so this is tidiness, not risk.
8. **`git push`.** The defect 54–55 commit exists only on this machine.
9. **Rebuild the submission zip** from the new HEAD, then unzip it and run `pytest -q` inside it.

**Feature freeze is 21 August. Everything after it is prose.**

---

## ⚠ The standing risk is volume, not missing work

~180 KB of prose across six documents. Every page is defensible; nobody will read
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
