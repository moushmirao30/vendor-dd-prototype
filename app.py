"""
app.py — the Streamlit review interface.

STATUS: Day 3 skeleton. The layout, navigation and export buttons are real;
the data is placeholder until Agents 1-3 are wired in (Days 4-16).

WHY BUILD THE SHELL FIRST: this screen is what gets demonstrated and screenshotted.
Building it on day 3 means every later piece of work has somewhere obvious to
plug in, and there is never a day where the project has nothing to show.

Run with:  streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

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
def load_vendors() -> dict:
    return yaml.safe_load((CONFIG / "vendors.yaml").read_text(encoding="utf-8"))


cfg = load_vendors()
vendors = cfg["vendors"]

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
    st.button("Agent 1 - Collect sources", width="stretch", disabled=True)
    st.button("Agent 2 - Extract evidence", width="stretch", disabled=True)
    st.button("Agent 3 - Review and brief", width="stretch", disabled=True)
    st.caption("Buttons activate as each agent is built (Days 4-16).")

    st.divider()
    st.caption(f"Difficulty tier: **{vendor['difficulty']}**")

# ---------------------------------------------------------------------------
# Main area: one tab per stage, so a non-technical reviewer can follow the
# workflow left to right and see what each agent did.
# ---------------------------------------------------------------------------
tab_sources, tab_steps, tab_evidence, tab_brief, tab_export = st.tabs(
    ["1 · Sources", "2 · Agent steps", "3 · Evidence", "4 · Vendor brief", "Export"]
)

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
    c2.metric("Manually verified so far", len(verified))

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

with tab_steps:
    st.subheader("What each agent did")
    st.info("Populated once the agents run. Each step will show its inputs, its "
            "outputs and anything it skipped, so the run can be audited.")
    for n, (name, role) in enumerate(
        [("Source Collection Agent", "finds and stores public URLs"),
         ("Evidence Extraction Agent", "pulls structured fields from those pages"),
         ("Brief Review Agent", "checks usability, flags gaps, writes the brief")], 1
    ):
        st.markdown(f"**Step {n} — {name}** · {role}")
        st.progress(0.0, text="not run yet")

with tab_evidence:
    st.subheader("Extracted evidence")
    st.info("Every field will appear here with the heading it came from, the "
            "snippet, the terms that matched and the source URL.")

with tab_brief:
    st.subheader(f"First-pass research brief - {vendor['name']}")
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
