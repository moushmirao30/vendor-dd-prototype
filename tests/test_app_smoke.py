"""
test_app_smoke.py — proves the Streamlit interface actually builds for EVERY
vendor, without a browser.

WHY THIS EXISTS: on 2026-08-10 the sources table rendered as an empty grey box
in Chrome while the underlying data was fine. A test that only checked the data
would have passed. These tests assert on what the app hands to Streamlit, and
guard the two defects that were found:
  1. the table must actually contain rows for every vendor
  2. no deprecated Streamlit API may be used anywhere in app.py
"""

from pathlib import Path
import re

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
VENDORS = ["GitLab", "Linear", "Sentry", "Postman", "Atlassian", "GitHub", "JetBrains"]


@pytest.mark.parametrize("vendor", VENDORS)
def test_every_vendor_renders_a_non_empty_source_table(vendor):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox[0].set_value(vendor).run()

    assert not at.exception, f"{vendor} raised: {[e.value for e in at.exception]}"
    assert len(at.dataframe) == 1, "the sources table should be present exactly once"

    df = at.dataframe[0].value
    assert df.shape[0] >= 5, f"{vendor} shows only {df.shape[0]} sources - expected 5+"
    assert list(df.columns) == ["Page type", "URL", "Status"]
    assert df["URL"].str.startswith("http").all(), "every source must be a real URL"


def test_ui_shell_has_all_five_review_stages_and_three_exports():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert len(at.tabs) == 5, "brief requires sources, steps, evidence, brief and export"
    assert len(at.get("download_button")) == 3, "brief requires JSON, CSV and Markdown export"
    assert len(at.button) == 3, "exactly three agent controls - no manager agent"


def test_disclaimer_is_always_visible():
    at = AppTest.from_file(APP, default_timeout=60).run()
    text = " ".join(w.value for w in at.warning)
    assert "First-pass internal research aid" in text
    assert "does not assign vendor risk scores" in text


def test_no_deprecated_streamlit_api_is_used():
    """`use_container_width` was removed after 2025-12-31. Today is well past that."""
    source = Path(APP).read_text(encoding="utf-8")
    assert not re.search(r"use_container_width", source), (
        "use_container_width is deprecated; use width='stretch'"
    )


def test_source_urls_are_distinguishable_from_one_another():
    """
    GitLab hosts product, pricing, security and privacy all on about.gitlab.com.
    An abbreviated display would render four different pages as the same string,
    which would make the source list useless as an audit trail.
    """
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox[0].set_value("GitLab").run()
    urls = at.dataframe[0].value["URL"].tolist()
    assert len(set(urls)) == len(urls), "every source URL must be unique and full-length"
    assert all(u.count("/") >= 3 for u in urls), "URLs must include their path, not just the host"
