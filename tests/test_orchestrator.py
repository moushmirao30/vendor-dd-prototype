"""
Tests for the orchestrator — the handoffs BETWEEN agents.

WHY THESE TESTS LOOK DIFFERENT FROM THE OTHERS
-----------------------------------------------
`test_agent1.py`, `test_agent2.py` and `test_agent3.py` test what happens inside
each agent. Defect 34 happened between them: the fix for defect 26 was wired to
an audit step Agent 1 never emitted, so a shipped safeguard executed zero times
across seven vendors and every unit test still passed. A fix nobody exercised is
a fix nobody verified.

So every test here asserts something about a HANDOFF or a REFUSAL, and none of
them reach the network — `collect` mode is exercised with a fake fetcher, and
`replay` and `review` read fixtures written to a tmp_path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.orchestrator import (COLLECT, REPLAY, REVIEW, cache_status,  # noqa: E402
                              run_workflow)


@pytest.fixture
def settings():
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def field_dictionary():
    fdy = yaml.safe_load((ROOT / "config" / "field_dictionary.yaml").read_text(encoding="utf-8"))
    return fdy.get("fields", fdy)


@pytest.fixture
def cfg():
    return yaml.safe_load((ROOT / "config" / "vendors.yaml").read_text(encoding="utf-8"))


def _workspace(tmp_path: Path, settings: dict) -> Path:
    """A throwaway repo root with the directory layout the orchestrator expects."""
    (tmp_path / settings["output"]["corpus_dir"]).mkdir(parents=True)
    (tmp_path / settings["output"]["briefs_dir"]).mkdir(parents=True)
    (tmp_path / "data" / "cache" / "html").mkdir(parents=True)
    return tmp_path


def _seed_corpus(root: Path, settings: dict, slug: str = "acme",
                 cache: bool = True) -> list[dict]:
    """One vendor, one readable security page, optionally with its cache present."""
    html_dir = root / "data" / "cache" / "html"
    rel = "data/cache/html/acme_security.html"
    if cache:
        (root / rel).write_text(
            "<h1>Security</h1><p>Acme maintains a SOC 2 Type 2 report covering "
            "security and availability, audited annually by an independent firm."
            "</p>", encoding="utf-8")

    records = [{
        "vendor_name": "Acme", "vendor_slug": slug,
        "source_url": "https://acme.example/security", "source_type": "security",
        "page_title": "Security | Acme", "collected_text": "Acme maintains a SOC 2 report.",
        "date_collected": "2026-08-13", "tags": [], "evidence_note": "",
        "http_status": 200, "fetch_ok": True, "raw_html_path": rel,
        "content_sha256": "", "robots_allowed": True, "text_extractor": "test",
        "block_count": 1, "content_usable": True,
    }]
    corpus_dir = root / settings["output"]["corpus_dir"]
    (corpus_dir / f"{slug}.json").write_text(json.dumps(records), encoding="utf-8")
    (corpus_dir / f"{slug}_run.json").write_text(json.dumps({
        "vendor_slug": slug, "ran_on": "2026-08-13T21:34:00",
        "steps": [{"action": "skip", "source_type": "privacy", "url": "",
                   "outcome": "never located", "note": ""}],
    }), encoding="utf-8")
    assert html_dir.exists()
    return records


VENDOR = {"slug": "acme", "name": "Acme", "homepage": "https://acme.example",
          "seeds": {"security": "https://acme.example/security"}}


# ---------------------------------------------------------------------------
# THE DEFECT-40 REFUSAL — the reason this module exists
# ---------------------------------------------------------------------------

def test_replay_refuses_when_the_html_cache_is_missing(tmp_path, settings,
                                                       field_dictionary, cfg):
    """
    THE TEST THIS FILE WAS WRITTEN FOR.

    The client asked on 18 Aug 2026 that the 22 MB HTML cache not be shipped, so
    the archive a reviewer receives is exactly this configuration: a corpus on
    disk, no cached pages. Before the preflight, Agent 2 returned eight
    NOT_FOUND fields with an empty evidence list and the brief read "nothing
    matched on any page we could read" — about pages nobody opened.

    A replay that cannot read anything must stop and say so.
    """
    root = _workspace(tmp_path, settings)
    _seed_corpus(root, settings, cache=False)

    result = run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode=REPLAY)

    assert not result.ok
    assert result.brief is None, "no brief may be produced from pages nobody read"
    assert "no cached HTML" in result.stopped_because
    assert REVIEW in result.stopped_because, \
        "a refusal must name the mode that WOULD work, or it is just a dead end"
    assert any(s.agent == "preflight" and s.action == "refused" for s in result.stages)


def test_replay_runs_when_the_cache_is_present(tmp_path, settings,
                                               field_dictionary, cfg):
    """The mirror of the test above: the guard must not block the healthy path."""
    root = _workspace(tmp_path, settings)
    _seed_corpus(root, settings, cache=True)

    result = run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode=REPLAY)

    assert result.ok, result.stopped_because
    assert result.brief["fields"]["security_trust"]["status"] == "FOUND"
    assert any(s.agent == "preflight" and s.action == "ran" for s in result.stages)


def test_review_mode_works_with_no_cache_at_all(tmp_path, settings,
                                                field_dictionary, cfg):
    """
    REVIEW is the mode the submitted archive supports, so it must not need the
    cache — that is the whole point of naming it separately. This is how the
    client's two instructions are reconciled: item 3 excludes the cache, item 5
    asks that offline replay be demonstrated, and the archive still replays
    Agent 3 offline out of the box.
    """
    root = _workspace(tmp_path, settings)
    _seed_corpus(root, settings, cache=True)
    ok = run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode=REPLAY)
    assert ok.ok

    for cached in (root / "data" / "cache" / "html").glob("*.html"):
        cached.unlink()

    result = run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode=REVIEW)

    assert result.ok, result.stopped_because
    assert result.brief["fields"]["security_trust"]["status"] == "FOUND", \
        "review mode reads Agent 2's saved output; deleting the cache must not " \
        "turn a found field into a silent NOT_FOUND"


# ---------------------------------------------------------------------------
# THE HANDOFF DEFECT 34 BROKE
# ---------------------------------------------------------------------------

def test_never_collected_page_types_are_handed_to_agent_2(tmp_path, settings,
                                                          field_dictionary, cfg):
    """
    Defect 26's fix shipped and executed zero times for a day because nothing
    tested the wiring between Agent 1's trail and Agent 2's argument list. The
    orchestrator owns that handoff, so the orchestrator's tests must assert it.
    """
    root = _workspace(tmp_path, settings)
    _seed_corpus(root, settings, cache=True)

    result = run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode=REPLAY)

    handoff = [s for s in result.stages if "never located" in s.detail]
    assert handoff, "the orchestrator must record what it handed between agents"
    assert "privacy" in handoff[0].detail, \
        "the privacy page was never located and Agent 2 has to be told"

    privacy = result.brief["fields"]["privacy_data_handling"]
    assert privacy["status"] == "NOT_FOUND"
    caveats = [e for e in privacy["evidence"]
               if e.get("match_location") == "tool_limitation"]
    assert caveats, "a NOT_FOUND for a page we never found must carry a caveat"


# ---------------------------------------------------------------------------
# REFUSALS CARRY REASONS (defect 4)
# ---------------------------------------------------------------------------

def test_missing_corpus_refuses_with_an_actionable_reason(tmp_path, settings,
                                                          field_dictionary, cfg):
    root = _workspace(tmp_path, settings)
    result = run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode=REVIEW)

    assert not result.ok
    assert "no corpus on disk" in result.stopped_because
    assert "README" in result.stopped_because


def test_collect_without_a_fetcher_refuses_instead_of_crashing(tmp_path, settings,
                                                               field_dictionary, cfg):
    """
    The fetcher is injected, never constructed here, so no test and no misuse can
    open a socket to a real vendor by accident. Asking for collect mode without
    one is a caller error and must read as one.
    """
    root = _workspace(tmp_path, settings)
    result = run_workflow(VENDOR, cfg, field_dictionary, settings, root,
                          mode=COLLECT, fetcher=None)

    assert not result.ok
    assert "PageFetcher" in result.stopped_because
    assert "Nothing was fetched" in result.stopped_because


def test_an_unknown_mode_is_rejected_loudly(tmp_path, settings, field_dictionary, cfg):
    root = _workspace(tmp_path, settings)
    with pytest.raises(ValueError):
        run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode="rerun")


# ---------------------------------------------------------------------------
# PREFLIGHT DETAIL
# ---------------------------------------------------------------------------

def test_cache_status_ignores_pages_agent_1_already_called_unreadable(tmp_path):
    """
    A JavaScript-rendered page and an absent cache file both mean "Agent 2 will
    not read this", and they mean opposite things. Counting an unusable page as a
    missing cache file would raise a false alarm about a page that is behaving
    exactly as documented — and collapsing two findings into one label is the
    failure this whole prototype exists to report.
    """
    (tmp_path / "data" / "cache" / "html").mkdir(parents=True)
    (tmp_path / "data" / "cache" / "html" / "ok.html").write_text("<p>hi</p>",
                                                                  encoding="utf-8")
    records = [
        {"source_type": "security", "raw_html_path": "data/cache/html/ok.html",
         "content_usable": True},
        {"source_type": "product", "raw_html_path": "data/cache/html/gone.html",
         "content_usable": False},          # unreadable: not a cache problem
        {"source_type": "pricing", "raw_html_path": "data/cache/html/gone.html",
         "content_usable": True},           # readable once, cache absent now
    ]

    present, missing = cache_status(records, tmp_path)

    assert present == ["security"]
    assert missing == ["pricing"], "the unusable product page must not be reported here"


def test_a_stale_extraction_is_reported_not_hidden(tmp_path, settings,
                                                   field_dictionary, cfg):
    """
    `app.py` discards an extraction when Agent 1 re-runs. Nothing protected the
    file-based path, so Agent 3 could review yesterday's evidence against today's
    sources and report a coverage figure belonging to neither.

    A warning, not a refusal: the honest response to "these two files may not
    match" is to say so, not to decide for the reviewer.
    """
    import os
    import time

    root = _workspace(tmp_path, settings)
    _seed_corpus(root, settings, cache=True)
    assert run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode=REPLAY).ok

    corpus_dir = root / settings["output"]["corpus_dir"]
    fields_file = corpus_dir / "acme_fields.json"
    old = time.time() - 3600
    os.utime(fields_file, (old, old))

    result = run_workflow(VENDOR, cfg, field_dictionary, settings, root, mode=REVIEW)

    assert result.ok, "a stale pair is a warning, not a refusal"
    agent2 = [s for s in result.stages if s.agent == "agent2"][0]
    assert "OLDER" in agent2.detail
