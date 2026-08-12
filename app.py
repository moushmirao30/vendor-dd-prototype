"""
app.py — the Streamlit review interface.

STATUS: Agent 1 (Source Collection) is live. Agents 2 and 3 are stubs.

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
from src.fetch import PageFetcher

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

    st.button("Agent 3 - Review and brief", width="stretch", disabled=True)
    st.caption("Agent 3 activates as it is built (Days 14-16).")

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

if run_agent2:
    field_dictionary = load_yaml("field_dictionary.yaml")
    corpus_dir = ROOT / settings["output"]["corpus_dir"]
    source = (st.session_state["collected"].get(vendor["slug"])
              or load_previous_run(corpus_dir, vendor["slug"]) or {})
    with st.spinner(f"Extracting evidence for {vendor['name']}…"):
        ran_on = datetime.now().isoformat(timespec="seconds")
        fields, esteps = extract_for_vendor(
            source.get("records", []), field_dictionary, settings, ROOT)
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
    if extracted:
        st.info("Agents 1 and 2 have run. The Brief Review Agent (Agent 3) is not "
                "built yet - it will assemble these fields into a brief, score the "
                "vendor using docs/confidence_rules.md, and raise review flags. "
                "Until then, read the evidence on the previous tab.")
    else:
        st.info("Generated by the Brief Review Agent once Agents 1-2 have run.")

with tab_export:
    st.subheader("Export")
    st.caption("The brief requires JSON, CSV and Markdown export.")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Download JSON", json.dumps({"status": "not generated yet"}, indent=2),
                       file_name=f"{vendor['slug']}_brief.json", disabled=True,
                       width="stretch")
    c2.download_button("Download CSV", "", file_name=f"{vendor['slug']}_brief.csv",
                       disabled=True, width="stretch")
    c3.download_button("Download Markdown", "", file_name=f"{vendor['slug']}_brief.md",
                       disabled=True, width="stretch")
