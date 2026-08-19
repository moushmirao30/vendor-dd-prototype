"""
run_workflow.py — run the whole 1 -> 2 -> 3 pipeline from the command line.

The orchestration lives in `src/orchestrator.py`; this file only chooses a
vendor, a mode and prints. Same shape as `tools/verify_corpus.py` and
`tools/review_all.py`: a thin entry point over library code, useful to a
developer and harmless to the deliverable. The Streamlit app calls
`run_workflow` directly and will not call this file.

    python tools/run_workflow.py                    # review mode, every vendor
    python tools/run_workflow.py --mode replay      # re-extract from the cache
    python tools/run_workflow.py --mode replay sentry
    python tools/run_workflow.py --mode collect linear   # the only networked mode

MODES — see the module docstring in src/orchestrator.py for the full reasoning.
    collect  Agent 1 fetches live. Needs the network.
    replay   Agent 2 re-reads the cached HTML. Needs data/cache/html/. No network.
    review   Agent 3 only, from saved output. Needs neither.
             THIS IS THE MODE THE SUBMITTED ARCHIVE SUPPORTS, because the client
             asked on 18 Aug 2026 that the HTML cache not be redistributed.

`review` is the default deliberately. It is the mode that works in a fresh clone
of what we submit, so the first thing a reviewer runs is the thing that cannot
mislead them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.orchestrator import MODES, REVIEW, run_workflow          # noqa: E402


def _load(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / name).read_text(encoding="utf-8"))


def main() -> int:
    argv = sys.argv[1:]
    mode = REVIEW
    if "--mode" in argv:
        i = argv.index("--mode")
        if i + 1 >= len(argv):
            print(f"--mode needs a value: {', '.join(MODES)}")
            return 1
        mode = argv[i + 1]
        del argv[i:i + 2]
    if mode not in MODES:
        print(f"unknown mode {mode!r}. Use one of: {', '.join(MODES)}")
        return 1

    settings = _load("settings.yaml")
    fdy = _load("field_dictionary.yaml")
    field_dictionary = fdy.get("fields", fdy)
    cfg = _load("vendors.yaml")

    vendors = [v for v in cfg["vendors"] if not argv or v["slug"] in argv]
    if not vendors:
        print(f"no vendor matching {argv} in config/vendors.yaml")
        return 1

    fetcher = None
    if mode == "collect":
        # Imported only in the one mode that needs it, so that running the
        # default mode cannot construct anything capable of opening a socket.
        from src.fetch import PageFetcher
        fetcher = PageFetcher(settings, ROOT)

    print(f"\n{'=' * 78}\n  ORCHESTRATOR — mode: {mode}\n{'=' * 78}")
    stopped = 0
    for vendor in vendors:
        result = run_workflow(vendor, cfg, field_dictionary, settings, ROOT,
                              mode=mode, fetcher=fetcher)
        print(f"\n  {vendor['name']}")
        for stage in result.stages:
            print(f"    {stage.agent:9s} {stage.action:9s} {stage.detail}")
        if not result.ok:
            stopped += 1
            print(f"    -> STOPPED. No brief was written.")

    print(f"\n{'=' * 78}")
    print(f"  {len(vendors) - stopped} of {len(vendors)} vendor(s) produced a brief.")
    if stopped:
        # A stop is not automatically a failure — refusing to review pages nobody
        # read is the correct behaviour, and the exit code must not call it a bug.
        print("  A STOP IS A RESULT. Read the reason above: refusing to answer")
        print("  from pages nobody read is the point, not a malfunction.")
    print(f"{'=' * 78}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
