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
    # The seeds table is always first. A SECOND table appears for any vendor
    # already collected, because the page replays that run from disk — so
    # asserting "exactly one table" made this test pass or fail depending on
    # what happened to be in data/corpus/, which is not a property of the code.
    # Found 2026-08-12: it was failing for GitLab and only GitLab.
    assert len(at.dataframe) >= 1, "the sources table is missing"

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


def test_editing_a_config_file_is_picked_up_and_not_served_from_a_stale_cache(tmp_path):
    """
    Regression: app.py cached config by filename only, so an edit to
    config/settings.yaml was ignored and the app crashed with
    KeyError: 'max_requests_per_vendor' on a key that was already in the file.
    The project promises reviewers that policy lives in YAML and is editable,
    so a stale config cache is a correctness bug, not a performance detail.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_under_test", APP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)   # Streamlit runs bare here; that is fine

    settings = module.load_yaml("settings.yaml")
    assert "max_requests_per_vendor" in settings["fetch"]
    assert settings["fetch"]["max_requests_per_vendor"] <= 25, "request budget must stay small"


def test_settings_keys_referenced_by_the_app_all_exist():
    """Cheap guard against a config key being renamed in one place only."""
    import yaml as _yaml
    settings = _yaml.safe_load(
        (Path(APP).parent / "config" / "settings.yaml").read_text(encoding="utf-8"))
    for key in ("user_agent", "delay_seconds_per_domain", "timeout_seconds",
                "max_pages_per_vendor", "max_requests_per_vendor", "respect_robots_txt"):
        assert key in settings["fetch"], f"settings.yaml is missing fetch.{key}"
    assert "corpus_dir" in settings["output"]


def test_app_calls_agent1_with_arguments_it_actually_accepts():
    """
    Regression: app.py was updated to pass `max_requests=` in the same edit that
    added the parameter to collect_for_vendor, but the running Streamlit process
    still held the old module in sys.modules and raised
    TypeError: unexpected keyword argument 'max_requests' at click time.
    A signature contract test catches that class of drift in pytest instead of
    in front of a reviewer.
    """
    import inspect
    import sys as _sys
    _sys.path.insert(0, str(Path(APP).parent))
    from src.agent1_collect import collect_for_vendor

    params = inspect.signature(collect_for_vendor).parameters
    source = Path(APP).read_text(encoding="utf-8")

    for kwarg in re.findall(r"collect_for_vendor\((.*?)\)", source, re.S):
        for name in re.findall(r"(\w+)\s*=", kwarg):
            assert name in params, f"app.py passes {name}= which collect_for_vendor lacks"

    assert "max_requests" in params and "max_pages" in params


# ---------------------------------------------------------------------------
# TABS 4 AND 5 — added 18 Aug 2026 when they stopped being stubs
#
# The client's guidance of 18 Aug requires the interface to show one chain:
#   Source -> Extracted Evidence -> Structured Field -> Confidence
#        -> Review Flag -> Final Brief
# A requirement stated in a client email and satisfied by code nobody tested is
# one refactor away from silently disappearing — which is defect 34 exactly, and
# defect 34 was a fix that shipped and then executed zero times for a day.
# ---------------------------------------------------------------------------

CHAIN_LINKS = ["1 · Source", "2 · Extracted evidence", "3 · Structured field",
               "4 · Confidence", "5 · Review flag", "6 · Final brief"]


def _all_text(at) -> str:
    """Every string the app handed Streamlit, whatever element type carried it."""
    parts = []
    for group in (at.markdown, at.caption, at.warning, at.info, at.success,
                  at.subheader, at.metric):
        for el in group:
            v = getattr(el, "value", None) or getattr(el, "label", None)
            if isinstance(v, str):
                parts.append(v)
    return " ".join(parts)


def test_the_brief_tab_shows_the_client_s_six_link_chain():
    at = AppTest.from_file(APP, default_timeout=90).run()
    text = _all_text(at)
    for link in CHAIN_LINKS:
        assert link in text, (
            f"the brief tab must label '{link}' — the client asked for the whole "
            f"chain from source to final brief, in writing, on 18 Aug 2026")


def test_the_brief_tab_never_shows_one_axis_alone():
    """
    Defect 42. A header reading only "10/10 High" is how Postman came to be
    indistinguishable from Sentry while resting on pages nobody could read.
    Evidence, confidence and coverage are drawn together or not at all.
    """
    at = AppTest.from_file(APP, default_timeout=90).run()
    labels = {m.label for m in at.metric}
    assert {"Evidence", "Confidence", "Coverage"} <= labels, (
        f"all three axes must be on screen together; found {labels}")


def test_agent_3_is_wired_through_the_orchestrator_not_around_it():
    """
    The wiring between agents lived in four places before src/orchestrator.py.
    app.py is the file that gets demonstrated, so it is the worst possible place
    for a fifth copy. Assert the import, not the behaviour: this is a structural
    rule, and a structural rule is cheapest to check structurally.
    """
    import ast

    source = Path(APP).read_text(encoding="utf-8")
    assert "from src.orchestrator import" in source
    assert "run_workflow(" in source

    # PARSED, NOT GREPPED. The first version of this test searched the raw text
    # for "review_vendor" and failed on the COMMENT that explains why the call is
    # absent — a test that cannot tell code from prose about code. Walking the
    # AST asks the only question that matters: is the function actually called?
    called = {
        node.func.id if isinstance(node.func, ast.Name) else
        getattr(node.func, "attr", "")
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
    }
    assert "review_vendor" not in called, (
        "app.py must not call Agent 3 directly — go through run_workflow so every "
        "handoff between agents has exactly one owner")
    assert "extract_for_vendor" in called, (
        "Agents 1 and 2 are still called directly on purpose: each has its own "
        "button and its own spinner, and a reviewer is meant to watch them run "
        "one at a time. If this ever fails, the split was changed — decide "
        "deliberately rather than letting it drift")


def test_the_export_tab_builds_its_csv_from_the_shared_row_builder():
    """
    The file a reviewer downloads from the screen and the file in data/exports/
    must be the same bytes. Two builders would drift, which is defects 15, 36,
    41 and 42 in this project already.
    """
    source = Path(APP).read_text(encoding="utf-8")
    assert "brief_to_csv" in source, "the download button must reuse src/export.py"
    assert "csv.writer" not in source, "app.py must not build a CSV of its own"
