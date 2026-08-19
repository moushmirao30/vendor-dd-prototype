"""
app.py — the Streamlit review interface.

STATUS: all three agents live. Tabs 4 and 5 wired 18 Aug 2026.

WHY THIS FILE CALLS `run_workflow` AND NOT THE AGENTS
-----------------------------------------------------
Agents 1 and 2 are still invoked directly by the two sidebar buttons, because
each has its own button and its own spinner and a reviewer is meant to watch
them run one at a time. Agent 3 is NOT. It goes through
`src.orchestrator.run_workflow` in REVIEW mode, for the reason that module
exists: the wiring between agents lived in four places and defect 34 proved
that a handoff nobody owns can stop happening without anyone noticing. Adding a
fifth copy here — inside the file that gets demonstrated — would be the worst
place to put it.

WHY THE SHELL WAS BUILT FIRST: this screen is what gets demonstrated and
screenshotted. Building it early means every later piece of work has somewhere
obvious to plug in, and there is never a day where the project has nothing to show.

Run with:  streamlit run app.py
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.agent1_collect import (collect_for_vendor, save_corpus, save_run,
                                load_previous_run)
from src.agent2_extract import extract_for_vendor, load_fields, save_fields
from src.agent3_review import load_brief
from src.export import brief_to_csv, brief_to_markdown
from src.fetch import PageFetcher
from src.orchestrator import REVIEW, run_workflow

ROOT = Path(__file__).parent
CONFIG = ROOT / "config"

st.set_page_config(page_title="Vendor Due-Diligence Research Prototype", layout="wide")

# Row height used to give tables an explicit pixel height.
# WHY THIS EXISTS: st.dataframe draws its cells into an HTML <canvas>. Inside a
# st.tabs panel the canvas can mount before the browser has resolved the panel's
# size, and it then collapses to zero height — the toolbar renders but the rows
# are invisible. Passing an explicit height stops that. Verified in Chrome on
# 2026-08-10 against Streamlit 1.61.
ROW_PX = 36


def table_height(n_rows: int) -> int:
    """Explicit pixel height for a table of n_rows (+1 for the header row)."""
    return min(ROW_PX * (n_rows + 1) + 4, 520)


@st.cache_data
def _read_yaml(name: str, mtime: float) -> dict:
    """Cached YAML read. `mtime` is part of the cache key - see load_yaml."""
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def load_yaml(name: str) -> dict:
    """
    Read a config file, re-reading it whenever the file changes on disk.

    WHY THE MTIME ARGUMENT: caching purely on the filename means an edit to
    config/settings.yaml is ignored until the cache is cleared. That broke a run
    on 2026-08-10 with `KeyError: 'max_requests_per_vendor'` - a key that was
    already in the file. Worse, this project TELLS the reviewer that policy lives
    in the YAML files and they can change it; a stale cache would make those
    edits silently do nothing. Including the modification time in the cache key
    makes "edit the YAML, rerun the app" work as documented.
    """
    return _read_yaml(name, (CONFIG / name).stat().st_mtime)


# ---------------------------------------------------------------------------
# STALE-MODULE GUARD
#
# Streamlit re-executes app.py on every rerun, but Python keeps the modules
# under src/ in sys.modules — so editing src/parse.py changes nothing until the
# server is restarted. That single fact has cost three debugging cycles on this
# project: a `TypeError: unexpected keyword argument`, and later a
# `TypeError: list indices must be integers or slices, not str` when a freshly
# reloaded app.py called into a stale src/. Both times the traceback pointed at
# code that was already correct on disk.
#
# `st.cache_resource` is per-PROCESS, not per-session, so the value below is
# captured once when the server starts and survives every rerun. Comparing it
# with the live mtime tells us the source changed underneath a running server,
# which is the one thing a traceback can never tell you.
# ---------------------------------------------------------------------------
SRC = ROOT / "src"
STALE_TOLERANCE_SECONDS = 2   # filesystem timestamp granularity, not a fudge


def stale_modules() -> list[str]:
    """
    Which files in `src/` have been edited since this process imported them.

    HOW IT KNOWS. Python writes `src/__pycache__/<name>.cpython-3xx.pyc` at the
    moment it imports a module, so that file's timestamp is a record of when the
    RUNNING process loaded that code. If the `.py` is newer than its `.pyc`, the
    module in memory is not the module on disk.

    Why not simply snapshot the newest mtime at server start: the snapshot is
    taken the first time this function runs, which is no help the one time it
    matters most — a server that has been up since before the edits. The
    `__pycache__` timestamps predate this guard, so they can answer for a server
    that started an hour ago.

    Known limit, stated rather than hidden: running `pytest` re-imports `src/`
    in a separate process and refreshes the `.pyc` files, so a test run between
    the edit and the page reload can mask a genuinely stale server. The guard can
    therefore miss, but it does not cry wolf.
    """
    cache = SRC / "__pycache__"
    if not cache.is_dir():
        return []

    stale: list[str] = []
    for source in sorted(SRC.glob("*.py")):
        compiled = sorted(cache.glob(f"{source.stem}.cpython-*.pyc"))
        if not compiled:
            continue
        loaded_at = max(c.stat().st_mtime for c in compiled)
        if source.stat().st_mtime > loaded_at + STALE_TOLERANCE_SECONDS:
            stale.append(source.name)
    return stale


_stale = stale_modules()
if _stale:
    st.error(
        f"**Restart the server.** `{'`, `'.join(_stale)}` changed on disk after "
        "this Streamlit process imported them, so the app is running a mix of old "
        "and new code. Streamlit reloads `app.py` but never the modules it "
        "imports. Press `Ctrl+C` in the terminal and run `streamlit run app.py` "
        "again. **Any error below this box is almost certainly that, not a bug in "
        "the code on disk.**",
        icon=":material/warning:",
    )

cfg = load_yaml("vendors.yaml")
settings = load_yaml("settings.yaml")
vendors = cfg["vendors"]

# Results of each agent run, keyed by vendor slug, kept for the session so the
# reviewer can switch vendors and come back without re-fetching.
st.session_state.setdefault("collected", {})
st.session_state.setdefault("extracted", {})
st.session_state.setdefault("reviewed", {})
st.session_state.setdefault("last_action", "")

# ---------------------------------------------------------------------------
# Persistent disclaimer. The brief requires the output to state plainly that
# this is a first-pass aid. Putting it in the UI chrome means it cannot be
# forgotten on any screen or in any screenshot.
# ---------------------------------------------------------------------------
st.warning(
    "**First-pass internal research aid.** Built from public web pages only. "
    "This tool does not assign vendor risk scores, grant security or compliance "
    "approval, or make procurement decisions. Every field requires human review."
)

st.title("Vendor Due-Diligence Research Workflow")
st.caption(f"Category: {cfg['category'].replace('_', ' ')} · "
           f"{len(vendors)} vendors · public sources only")

# ---------------------------------------------------------------------------
# Sidebar: vendor selection and the optional research-category filter that the
# brief lists under "Expected Input".
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Controls")
    selected_name = st.selectbox("Vendor", [v["name"] for v in vendors])
    vendor = next(v for v in vendors if v["name"] == selected_name)

    st.multiselect(
        "Research focus (optional filter)",
        ["security", "privacy", "support", "pricing", "product capability"],
        help="Leave empty to extract every field.",
    )

    st.divider()
    st.subheader("Run the workflow")

    run_agent1 = st.button("Agent 1 - Collect sources", width="stretch", type="primary")
    st.caption(
        f"Keeps up to {settings['fetch']['max_pages_per_vendor']} public pages, "
        f"making at most {settings['fetch']['max_requests_per_vendor']} requests, "
        f"{settings['fetch']['delay_seconds_per_domain']}s apart, after reading "
        "robots.txt. Cached after the first run, so a second run is instant and "
        "works offline."
    )

    # Agent 2 reads the cached HTML Agent 1 saved, so it needs no network and
    # is disabled until there is a corpus to read. Disabling it is honest: an
    # enabled button that can only fail teaches the reviewer nothing.
    has_corpus = (ROOT / settings["output"]["corpus_dir"] /
                  f"{vendor['slug']}.json").exists()
    run_agent2 = st.button("Agent 2 - Extract evidence", width="stretch",
                           disabled=not has_corpus)
    st.caption(
        "Reads the pages Agent 1 cached and matches them against "
        f"{sum(len(f['terms']) for f in load_yaml('field_dictionary.yaml').values())} "
        "phrases in config/field_dictionary.yaml. Offline, no network, no model."
        if has_corpus else "Run Agent 1 first - Agent 2 reads its cached pages.")

    # Agent 3 needs Agent 2's saved fields and NOTHING ELSE — no network, no
    # HTML cache. That is why the button runs `run_workflow` in REVIEW mode and
    # not REPLAY: review is the only mode that works in the archive we submit,
    # after the client asked on 18 Aug that the cache not be shipped. The screen
    # a reviewer opens should therefore default to it.
    has_fields = (ROOT / settings["output"]["corpus_dir"] /
                  f"{vendor['slug']}_fields.json").exists()
    run_agent3 = st.button("Agent 3 - Review and brief", width="stretch",
                           disabled=not has_fields)
    st.caption(
        "Reviews Agent 2's saved fields: coverage, missing categories, weak "
        "evidence, conflicts. No network and no HTML cache needed - this is the "
        "mode a reviewer of the submitted archive can run."
        if has_fields else "Run Agent 2 first - Agent 3 reviews what it extracted.")

    st.divider()
    st.caption(f"Difficulty tier: **{vendor['difficulty']}**")

# ---------------------------------------------------------------------------
# Main area: one tab per stage, so a non-technical reviewer can follow the
# workflow left to right and see what each agent did.
# ---------------------------------------------------------------------------
# STATE IS COMPUTED BEFORE ANYTHING IS DRAWN.
#
# These blocks used to sit BELOW st.tabs(). That is the natural way to write
# it and it is wrong: Streamlit renders top to bottom in a single pass, so a
# confirmation set here was written into session_state AFTER the banner above
# had already been drawn, and only appeared on the NEXT interaction. The fix
# for a silent agent (defect 18) was itself silent for one click.
#
# Rule for this file: decide what is true, then draw it. Never the reverse.

if run_agent1:
    fetcher = PageFetcher(settings, ROOT)
    with st.spinner(f"Collecting public sources for {vendor['name']}…"):
        records, steps = collect_for_vendor(
            vendor, cfg["url_patterns"], fetcher,
            max_pages=settings["fetch"]["max_pages_per_vendor"],
            max_requests=settings["fetch"]["max_requests_per_vendor"],
            min_usable_text_chars=settings["fetch"]["min_usable_text_chars"],
            min_readable_chars_per_kb=settings["fetch"]["min_readable_chars_per_kb"],
        )
        path = save_corpus(records, ROOT / settings["output"]["corpus_dir"], vendor["slug"])
        save_run(steps, ROOT / settings["output"]["corpus_dir"], vendor["slug"],
                 ran_on=datetime.now().isoformat(timespec="seconds"))
    st.session_state["collected"][vendor["slug"]] = {
        "records": [r.to_dict() for r in records],
        "steps": [s.__dict__ for s in steps],
        "corpus_path": str(path.relative_to(ROOT)),
        "ran_on": datetime.now().isoformat(timespec="seconds"),
        "from_disk": False,
    }
    st.session_state["last_action"] = (
        f"**Agent 1 finished for {vendor['name']}.** {len(records)} pages kept "
        f"from {len([s for s in steps if s.action != 'skip'])} URLs tried, "
        f"{len([s for s in steps if s.action == 'skip'])} flagged for follow-up. "
        "Agent 2 is now enabled in the sidebar."
    )
    # A fresh collection makes any earlier extraction stale: it was built from
    # different pages. Clearing it stops the Evidence tab showing yesterday's
    # findings beside today's sources with nothing to say they disagree.
    st.session_state["extracted"].pop(vendor["slug"], None)

    # RERUN, OR THE AGENT 2 BUTTON STAYS DEAD (found 2026-08-12 on Atlassian).
    #
    # The sidebar is drawn BEFORE this block runs — it has to be, because the
    # button's return value is what triggers the block. So `has_corpus` was
    # evaluated while <slug>.json did not yet exist, and Agent 2 rendered
    # disabled. Collect a vendor for the first time and the next button in the
    # workflow is unclickable, with nothing on screen explaining why. It only
    # woke up if you touched something else first.
    #
    # This went unnoticed on GitLab because its corpus was already on disk from
    # an earlier session, so `has_corpus` was true before Agent 1 ever ran. The
    # first genuinely new vendor exposed it. A demo path that only works for
    # data you already have is not a demo path.
    #
    # st.rerun() restarts the script top to bottom with the corpus now written,
    # so the sidebar redraws with Agent 2 enabled and the confirmation banner
    # showing. session_state carries both across the rerun.
    st.rerun()

if run_agent2:
    field_dictionary = load_yaml("field_dictionary.yaml")
    corpus_dir = ROOT / settings["output"]["corpus_dir"]
    source = (st.session_state["collected"].get(vendor["slug"])
              or load_previous_run(corpus_dir, vendor["slug"]) or {})
    with st.spinner(f"Extracting evidence for {vendor['name']}…"):
        ran_on = datetime.now().isoformat(timespec="seconds")
        # Hand Agent 2 the page types Agent 1 never managed to collect. Without
        # this it can only see the pages that DID arrive, so it cannot tell the
        # difference between "we searched and found nothing" and "we never found
        # the page to search" - see defect 26 (JetBrains).
        never_collected = [s["source_type"] for s in source.get("steps", [])
                           if s.get("action") == "skip"]
        fields, esteps = extract_for_vendor(
            source.get("records", []), field_dictionary, settings, ROOT,
            never_collected=never_collected)
        save_fields(fields, corpus_dir, vendor["slug"], esteps, ran_on)
    st.session_state["extracted"][vendor["slug"]] = {
        "fields": [f.to_dict() for f in fields],
        "steps": [s.__dict__ for s in esteps],
        "ran_on": ran_on,
        "from_disk": False,
    }
    found = sum(1 for f in fields if f.status == "FOUND")
    st.session_state["last_action"] = (
        f"**Agent 2 finished for {vendor['name']}.** {found} of {len(fields)} "
        f"fields found, {sum(1 for f in fields if f.status == 'NOT_FOUND')} "
        f"NOT_FOUND. Open **3 - Evidence** to read the quotes and their sources."
    )

if run_agent3:
    # ONE CALL. The orchestrator owns every handoff between the three agents —
    # see src/orchestrator.py. Calling `review_vendor` directly from here would
    # make this the FIFTH place that re-derives the same wiring from the same
    # JSON files, in the file that gets demonstrated.
    with st.spinner(f"Reviewing {vendor['name']}…"):
        result = run_workflow(vendor, cfg, load_yaml("field_dictionary.yaml"),
                              settings, ROOT, mode=REVIEW)
    if not result.ok:
        # A refusal is a result, not a crash (defect 4: never let a refusal be a
        # bare boolean). `stopped_because` always names the reason AND the mode
        # that would work, so the message on screen is actionable rather than red.
        st.session_state["last_action"] = (
            f"**Agent 3 stopped for {vendor['name']}.** {result.stopped_because}")
    else:
        st.session_state["reviewed"][vendor["slug"]] = {
            "brief": result.brief,
            "stages": [s.__dict__ for s in result.stages],
            "from_disk": False,
        }
        b = result.brief
        st.session_state["last_action"] = (
            f"**Agent 3 finished for {vendor['name']}.** Evidence "
            f"{b['evidence_score']}/10 {b['evidence_band']} · confidence "
            f"{b['confidence_band']} ({b['confidence_counts'].get('High', 0)} of "
            f"{b['coverage_total']} core fields High) · coverage "
            f"{b['coverage_verified']}/{b['coverage_total']} · "
            f"{len(b['review_flags'])} review flag(s). Open **4 - Vendor brief**.")
    st.rerun()

# REPLAY: if this vendor was collected in an earlier session, load that run from
# disk. The brief asks the interface to "run or replay the workflow"; without
# this, refreshing the browser wiped the audit trail and the app looked unused
# even though the corpus was saved.
collected = st.session_state["collected"].get(vendor["slug"])
if collected is None:
    collected = load_previous_run(ROOT / settings["output"]["corpus_dir"], vendor["slug"])

extracted = st.session_state["extracted"].get(vendor["slug"])
if extracted is None:
    saved = load_fields(ROOT / settings["output"]["corpus_dir"], vendor["slug"])
    if saved and saved["fields"]:
        extracted = {**saved, "from_disk": True}

# Same replay contract for Agent 3 as for Agents 1 and 2 (defects 9 and 19): a
# brief already on disk must survive a browser refresh, or the app looks unused
# while `data/briefs/` is full.
reviewed = st.session_state["reviewed"].get(vendor["slug"])
if reviewed is None:
    saved_brief = load_brief(ROOT / settings["output"]["briefs_dir"], vendor["slug"])
    if saved_brief:
        reviewed = {"brief": saved_brief,
                    "stages": [{"agent": "agent3", "action": "replayed",
                                "detail": "brief loaded from data/briefs/ — "
                                          "no agent was re-run"}],
                    "from_disk": True}

# CONFIRMATION BANNER, ABOVE THE TABS ON PURPOSE.
#
# WHY (defect 18, found 2026-08-12 by watching a real click in the browser):
# pressing "Agent 2" produced no visible change at all unless you were already
# looking at the Evidence tab. The run takes under two seconds, so the spinner
# is gone before it registers, and the Sources tab - where the app opens - is
# byte-identical before and after. The button was pressed, nothing appeared, and
# the reasonable conclusion was that it had not worked. It had: the fields were
# already on disk. An agent that succeeds silently is indistinguishable from one
# that fails silently, and this screen is the demo.
if st.session_state.get("last_action"):
    st.success(st.session_state["last_action"], icon=":material/check:")

tab_sources, tab_steps, tab_evidence, tab_brief, tab_export = st.tabs(
    ["1 · Sources", "2 · Agent steps", "3 · Evidence", "4 · Vendor brief", "Export"]
)

# ---------------------------------------------------------------------------
# Run Agent 1 when asked. Everything it did is stored so the UI can show the
# audit trail rather than just the result.
# ---------------------------------------------------------------------------

with tab_sources:
    st.subheader(f"Public sources for {vendor['name']}")

    verified = vendor.get("verified", [])
    rows = [
        {
            "Page type": stype,
            "URL": url,
            "Status": "verified 2026-08-10" if stype in verified
                      else "candidate - confirmed at run time",
        }
        for stype, url in vendor["seeds"].items()
    ]
    df = pd.DataFrame(rows)

    c1, c2 = st.columns(2)
    c1.metric("Public sources listed", len(rows))
    c2.metric("Human-verified by hand", len(verified),
              help="URLs a person opened and read on 2026-08-10. Separate from what Agent 1 confirms automatically at run time.")

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        height=table_height(len(df)),
        column_config={
            # Show the FULL url, not just the host. Four of GitLab's six pages
            # live on about.gitlab.com — abbreviating to the host made them look
            # identical, which defeats the point of an auditable source list.
            "URL": st.column_config.LinkColumn("URL", width="large"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
        },
    )
    st.caption(
        "Only 'verified' rows have been opened and read by a human. Everything else "
        "is a candidate URL that the Source Collection Agent must confirm, recording "
        "its HTTP status in the corpus."
    )

    if vendor.get("observed_2026_08_10"):
        with st.expander("Collection notes from manual verification"):
            st.write(vendor["observed_2026_08_10"])

    if collected:
        st.divider()
        origin = ("loaded from a previous run on " + collected.get("ran_on", "unknown")
                  if collected.get("from_disk") else "collected in this session")
        st.markdown(f"##### Pages actually collected  \n<small>{origin}</small>",
                    unsafe_allow_html=True)
        corpus = pd.DataFrame(collected["records"])
        # COLUMN ORDER IS DELIBERATE. `date_collected` was dropped and the URL
        # moved last because at a normal window width the table overflowed and
        # `characters` and `text via` sat off-screen behind a horizontal
        # scrollbar - and `text via` is the entire visible outcome of the
        # content-cleaner fix (defect 7). A reviewer who never scrolls right
        # never learns which pages needed the fallback extractor. The collection
        # date is already printed above the table.
        view = corpus[["source_type", "page_title", "http_status"]].copy()
        view["characters"] = corpus["collected_text"].str.len()
        if "text_extractor" in corpus:
            view["text via"] = corpus["text_extractor"]
        view["source_url"] = corpus["source_url"]
        st.dataframe(
            view, width="stretch", hide_index=True, height=table_height(len(view)),
            column_config={"source_url": st.column_config.LinkColumn("URL", width="large")},
        )

with tab_steps:
    st.subheader("What each agent did")

    st.markdown("**Step 1 — Source Collection Agent** · finds and stores public URLs")
    if not collected or not collected.get("steps"):
        st.progress(0.0, text="not run yet — press 'Agent 1' in the sidebar")
    else:
        steps_df = pd.DataFrame(collected["steps"])
        found = int((steps_df["outcome"] == "found").sum())
        skipped = int((steps_df["action"] == "skip").sum())
        st.progress(1.0, text=f"complete — {found} pages collected, {skipped} not found")

        m1, m2, m3 = st.columns(3)
        m1.metric("URLs tried", len(steps_df[steps_df["action"] != "skip"]))
        m2.metric("Pages collected", found)
        m3.metric("Flagged for follow-up", skipped)

        st.caption(
            "Every URL this agent tried, in order. `probe` = guessed from a URL "
            "pattern; `seed-fallback` = taken from the curated list because "
            "discovery failed; `skip` = never resolved, needs a human."
        )
        st.dataframe(steps_df, width="stretch", hide_index=True,
                     height=table_height(len(steps_df)))
        st.caption(f"Corpus written to `{collected['corpus_path']}`")

    st.markdown("**Step 2 — Evidence Extraction Agent** · pulls structured fields "
                "from those pages")
    if not extracted:
        st.progress(0.0, text="not run yet — press 'Agent 2' in the sidebar")
    elif not extracted.get("steps"):
        st.progress(1.0, text=f"complete - extracted on {extracted['ran_on']}, but "
                              "that run was saved before audit trails were "
                              "persisted. Press Agent 2 again to record one.")
    else:
        esteps = pd.DataFrame(extracted["steps"])
        pages = int((esteps["action"] == "parse-page").sum())
        misses = int((esteps["action"] == "no-match").sum())
        origin = ("replayed from a run on " + extracted["ran_on"]
                  if extracted.get("from_disk") else "run in this session")
        st.progress(1.0, text=f"complete - {pages} pages parsed, "
                              f"{misses} fields NOT_FOUND - {origin}")
        st.caption(
            "`parse-page` = a cached page split into heading blocks · `match` = a "
            "field found evidence on that page · `no-match` = nothing matched, "
            "recorded with how many terms were tried so NOT_FOUND is a finding "
            "rather than a shrug · `missing-html` = the cached page could not be read."
        )
        st.dataframe(esteps, width="stretch", hide_index=True,
                     height=table_height(len(esteps)))

    st.markdown("**Step 3 — Brief Review Agent** · checks usability, flags gaps, "
                "writes the brief")
    st.progress(0.0, text="not built yet")

with tab_evidence:
    st.subheader("Extracted evidence")

    if not extracted:
        st.info("Run Agent 1, then Agent 2. Every field will appear here with the "
                "heading it came from, the snippet, the terms that matched and "
                "the source URL.")
    else:
        fields = extracted["fields"]
        summary = pd.DataFrame([
            {"Field": f["label"], "Status": f["status"],
             "Confidence": f["confidence"],
             "Evidence": len(f["evidence"]),
             "From": (f["evidence"][0]["source_type"] if f["evidence"] else "-")}
            for f in fields
        ])
        st.dataframe(summary, width="stretch", hide_index=True,
                     height=table_height(len(summary)))
        st.caption(
            "**From** is the page type the top quote came from. Compare it with the "
            "field name: evidence for integrations that came off a privacy page is "
            "technically a match and practically worth a second look. That comparison "
            "is a reviewer's job, which is why the column is here rather than hidden."
        )

        st.divider()
        for f in fields:
            icon = {"FOUND": "🟢", "PARTIAL": "🟡", "NOT_FOUND": "⚪"}[f["status"]]
            with st.expander(f"{icon} {f['label']} — {f['status']} "
                             f"({f['confidence']})", expanded=False):
                if not f["evidence"]:
                    st.write("**Nothing matched on any collected page.** "
                             "This vendor does not publish this on the pages we are "
                             "permitted to read. Flag for manual follow-up.")
                    continue
                st.markdown(f"**Quoted from the vendor's page:**  \n> {f['value']}")
                st.caption("This text is copied from the page, not written by the "
                           "tool. There is no language model in this prototype.")
                for i, e in enumerate(f["evidence"], 1):
                    st.markdown(
                        f"**{i}. {e['heading']}**  \n"
                        f"{e['snippet']}  \n"
                        f"<small>matched `{'`, `'.join(e['matched_terms'])}` "
                        f"in the {e['match_location'].replace('_', ' ')} · "
                        f"{e['source_type']} page · "
                        f"[{e['source_url']}]({e['source_url']})</small>",
                        unsafe_allow_html=True)

with tab_brief:
    st.subheader(f"First-pass research brief - {vendor['name']}")

    if not reviewed:
        st.info("Generated by the Brief Review Agent. Run Agents 1 and 2, then "
                "press **Agent 3 - Review and brief** in the sidebar.")
    else:
        brief = reviewed["brief"]
        if reviewed.get("from_disk"):
            st.caption(":material/history: Replayed from `data/briefs/` - no agent "
                       "was re-run. Press Agent 3 to regenerate.")

        # The page banner above the tabs already carries this for the TOOL. Here
        # it is shown small, because what matters is that the disclaimer travels
        # inside the brief object itself and therefore inside every export — the
        # brief requires the OUTPUT to state it, not the screen. Printing the same
        # paragraph twice full-size on one page trains a reader to skip both.
        st.caption(f":material/warning: {brief['disclaimer']}")

        # --- THREE NUMBERS, THREE QUESTIONS (defect 42) --------------------
        #
        # These are drawn side by side and never one at a time. Until 18 Aug the
        # header showed a single figure called "Confidence" that actually measured
        # how much quotable text was found, above field cards that each carried the
        # client's confidence rule and disagreed with it. Postman read 10/10 High on
        # coverage 2/5; Sentry read 10/10 High on 5/5. A reviewer comparing the two
        # on one number could not tell them apart, which is the exact failure this
        # prototype exists to report.
        counts = brief.get("confidence_counts") or {}
        total = brief.get("coverage_total", 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Evidence", f"{brief['evidence_score']}/10 {brief['evidence_band']}",
                  help="How MUCH quotable material was found. Extraction quality "
                       "only - it cannot tell you whether anyone could read the "
                       "page it should have come from.")
        c1.caption("How MUCH was found")
        c2.metric("Confidence", brief.get("confidence_band", "-"),
                  help="The client's definition, applied per field and reported as "
                       "counts rather than a score - any threshold we chose would "
                       "be one we picked while looking at our own seven vendors. "
                       "The band is the weakest core field.")
        # st.metric's `delta` was the obvious place for these two sub-lines and it
        # is wrong: Streamlit prefixes a delta with a directional arrow, so
        # "all verified" rendered as "up all verified". An arrow that points
        # somewhere meaningless on a number a procurement reader is meant to trust
        # is a small lie in the same family as the large ones this tool reports.
        c2.caption(f"How GOOD it is - **{counts.get('High', 0)} of {total}** core "
                   f"fields at High, {counts.get('Medium', 0)} Medium, "
                   f"{counts.get('Low', 0)} Low")
        c3.metric("Coverage", f"{brief['coverage_verified']}/{total}",
                  help="How much could actually be CHECKED. A core field resting on "
                       "a page nobody could read does not count as verified.")
        c3.caption("How much could be CHECKED - core fields whose evidence carries "
                   "no collection caveat")
        if brief.get("coverage_caveated"):
            st.caption(f"Caveated core fields: **{', '.join(brief['coverage_caveated'])}** "
                       f"- these rest on pages that could not be read. The evidence "
                       f"score counts what was found; it cannot count what was never "
                       f"looked at.")

        st.markdown(f"**Overview** (quoted from the vendor's own product page): "
                    f"{brief.get('vendor_overview') or '_none could be quoted_'}")
        st.caption(f"Category: {brief.get('product_category', '')} - curated, not "
                   f"extracted. Generated {brief.get('generated_on', '')}.")

        st.divider()

        # --- THE CHAIN THE CLIENT ASKED TO SEE ----------------------------
        #
        # Their words, 18 Aug 2026: the interface must show
        #   Source -> Extracted Evidence -> Structured Field -> Confidence
        #        -> Review Flag -> Final Brief
        # so it is labelled literally, one numbered link at a time. The point is
        # not decoration: a reviewer who can see all six links can audit the tool
        # instead of trusting it, and every earlier defect in this project was
        # found by exactly that act of looking at one link and asking whether it
        # followed from the one before.
        st.markdown("#### The chain, field by field")
        st.caption("**Source → Extracted evidence → Structured field → Confidence "
                   "→ Review flag → Final brief.** Open any field to follow one "
                   "statement from the page it came from to the line in the brief.")

        flags = brief.get("review_flags", [])
        missing = brief.get("missing_or_unclear", [])

        for name, f in brief.get("fields", {}).items():
            icon = {"FOUND": "🟢", "PARTIAL": "🟡", "NOT_FOUND": "⚪"}.get(f["status"], "⚪")
            label = f.get("label", name)
            # A flag or a missing-note is matched to its field by the label it was
            # written with. Agent 3 composes both as "<label>: <reason>".
            own_flags = [x for x in flags if x.startswith(label)]
            own_missing = [x for x in missing if x.startswith(label)]
            badge = " · 🚩" if own_flags else ""

            with st.expander(f"{icon} {label} — {f['status']} · confidence "
                             f"{f.get('confidence', '-')}{badge}", expanded=False):
                real = [e for e in f.get("evidence", [])
                        if e.get("match_location") != "tool_limitation"]
                notes = [e for e in f.get("evidence", [])
                         if e.get("match_location") == "tool_limitation"]
                top = real[0] if real else {}

                st.markdown("**1 · Source**")
                if top:
                    st.markdown(f"`{top.get('source_type','?')}` page — "
                                f"[{top.get('source_url','')}]({top.get('source_url','')})")
                else:
                    st.markdown("_No source produced evidence for this field._")

                st.markdown("**2 · Extracted evidence** — copied from the page, "
                            "not written by the tool")
                if top:
                    st.markdown(f"> **{top.get('heading','')}**  \n> {top.get('snippet','')}")
                    st.caption(f"matched `{'`, `'.join(top.get('matched_terms', []) or [])}` "
                               f"in the {str(top.get('match_location','')).replace('_',' ')}")
                    if f.get("terms_not_shown"):
                        st.caption(f":material/visibility_off: cites "
                                   f"`{'`, `'.join(f['terms_not_shown'])}` from elsewhere "
                                   f"on the page — present, but not visible in the quote "
                                   f"above, so you cannot verify it from this card alone.")
                else:
                    st.markdown("_Nothing matched._")

                st.markdown("**3 · Structured field**")
                st.markdown(f"`{name}` → status **{f['status']}**")

                st.markdown("**4 · Confidence**")
                st.markdown(f"**{f.get('confidence','-')}** — {f.get('confidence_reason','')}")
                st.caption(f"Extraction quality (a separate axis): "
                           f"{f.get('extraction_quality','-')}. The client asked on "
                           f"18 Aug that confidence not rest on sentence length, so "
                           f"the two are measured and shown apart.")

                st.markdown("**5 · Review flag**")
                if own_flags or own_missing:
                    for x in own_flags:
                        st.markdown(f"- 🚩 {x[len(label):].lstrip(': ')}")
                    for x in own_missing:
                        st.markdown(f"- :material/help: {x[len(label):].lstrip(': ')}")
                else:
                    st.markdown("_No flag. The evidence sits where this fact belongs "
                                "and carries no collection caveat._")
                for n in notes:
                    st.warning(f"**{n.get('heading','')}** — {n.get('snippet','')}",
                               icon=":material/warning:")

                st.markdown("**6 · Final brief**")
                st.markdown(f"> {f.get('value') or '_no value — see the flag above_'}")

        st.divider()
        left, right = st.columns(2)
        with left:
            st.markdown("#### Missing or unclear")
            if missing:
                for m in missing:
                    st.markdown(f"- {m}")
            else:
                st.markdown("_Every field was populated._")
            st.caption("The client asked us to distinguish information **not found** "
                       "on the vendor's public sources from information that **could "
                       "not be evaluated** because the page could not be reliably "
                       "extracted. Each line above says which it is, per field, tested "
                       "against that field's own home page.")
        with right:
            st.markdown("#### Review flags")
            if flags:
                for fl in flags:
                    st.markdown(f"- 🚩 {fl}")
            else:
                st.markdown("_No flags raised._")
            st.caption("Flags are the product. A flag list nobody reads is a defect "
                       "nobody fixes.")

        st.markdown("#### Key sources")
        for s in brief.get("key_sources", []):
            st.markdown(f"- [{s}]({s})")

        with st.expander("How this brief was produced — the orchestrator's trail"):
            st.dataframe(pd.DataFrame(reviewed["stages"]), width="stretch",
                         hide_index=True,
                         height=table_height(len(reviewed["stages"])))
            st.caption("These are the handoffs BETWEEN agents, not the steps inside "
                       "them. Defect 34: a safeguard wired to a handoff nobody owned "
                       "ran zero times for a day and every unit test still passed.")

with tab_export:
    st.subheader("Export")
    st.caption("The brief requires the result to be exportable as JSON, CSV or "
               "Markdown. All three are produced from the same brief object by "
               "`src/export.py`, so the file downloaded here is byte-identical to "
               "the one `tools/export_all.py` writes into `data/exports/`.")

    if not reviewed:
        st.info("Run Agent 3 first — there is no brief to export yet.")
        c1, c2, c3 = st.columns(3)
        c1.download_button("Download JSON", "", file_name=f"{vendor['slug']}_brief.json",
                           disabled=True, width="stretch")
        c2.download_button("Download CSV", "", file_name=f"{vendor['slug']}_brief.csv",
                           disabled=True, width="stretch")
        c3.download_button("Download Markdown", "", file_name=f"{vendor['slug']}_brief.md",
                           disabled=True, width="stretch")
    else:
        brief = reviewed["brief"]
        md = brief_to_markdown(brief)
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "Download JSON", json.dumps(brief, indent=2, ensure_ascii=False),
            file_name=f"{vendor['slug']}_brief.json", mime="application/json",
            width="stretch", type="primary")
        c2.download_button(
            # utf-8-sig, matching src/export.py: Excel on Windows opens plain UTF-8
            # as Latin-1 and turns every quotation mark in a vendor's prose into
            # mojibake. Three bytes to stop a reviewer's first impression of the
            # corpus being "the text is broken".
            "Download CSV", brief_to_csv(brief).encode("utf-8-sig"),
            file_name=f"{vendor['slug']}_brief.csv", mime="text/csv", width="stretch")
        c3.download_button(
            "Download Markdown", md, file_name=f"{vendor['slug']}_brief.md",
            mime="text/markdown", width="stretch")

        st.divider()
        st.markdown("#### What the submitted archive contains")
        st.caption("The client asked on 18 August 2026 that the 22 MB cache of "
                   "verbatim third-party HTML **not** be redistributed. What ships "
                   "instead is the structured corpus, the source manifest, and the "
                   "collection code — and the consequence, stated rather than "
                   "hidden: a fresh clone cannot re-extract until the reviewer "
                   "re-collects. It CAN still replay this review offline, which is "
                   "the mode this screen just used.")
        exports = ROOT / "data" / "exports"
        listing = sorted(exports.glob("*")) if exports.exists() else []
        if listing:
            st.dataframe(
                pd.DataFrame([{"File": f.name, "KB": round(f.stat().st_size / 1024, 1)}
                              for f in listing]),
                width="stretch", hide_index=True, height=table_height(len(listing)))
            st.caption("Written by `python tools/export_all.py`. `corpus.csv` is every "
                       "page kept; `source_manifest.csv` is every page ATTEMPTED — "
                       "including the 404s and the JavaScript shells — which is the "
                       "only thing that lets a reader tell 'the vendor is silent' "
                       "from 'we could not look'.")

        st.divider()
        st.markdown("#### Markdown preview")
        st.code(md, language="markdown")
