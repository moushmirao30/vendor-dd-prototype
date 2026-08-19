"""
orchestrator.py — the one place where Agent 1, Agent 2 and Agent 3 are wired together.

WHY THIS MODULE EXISTS
----------------------
The project brief lists "Python orchestration code for the agent workflow" as a
deliverable in its own right, and names "simple custom Python orchestration"
rather than a framework. A three-step linear flow does not need LangGraph; it
needs one honest function.

But the deliverable is not the reason this file is worth writing. Before it, the
wiring between the three agents existed in FOUR places — `app.py`,
`tools/review_all.py`, `tools/export_all.py` and the tests — each re-deriving
the same handoffs from the same JSON files. This project has already been bitten
three times by one rule living in two places:

    defect 15  the confidence rule disagreeing with its own documentation
    defect 36  two docstrings disagreeing, which silently killed PARTIAL
    defect 41  Agent 2 over-hedging a NOT_FOUND that Agent 3 reported honestly,
               so one brief carried both sentences at once

Defect 34 is the sharper warning: the fix for defect 26 was wired to an audit
step Agent 1 never emitted, so a shipped safeguard executed ZERO times and
nothing noticed, because no single component owned the handoff. `run_workflow`
owns it. Every handoff between agents happens here, once, in the open.

THE THREE MODES, AND WHY THE THIRD ONE IS THE IMPORTANT ONE
-----------------------------------------------------------
The brief asks the interface to let a reviewer "run OR replay the workflow".
Those are two features, and after the client's guidance of 18 August 2026 they
are three, because the submitted archive no longer contains the HTML cache:

    COLLECT   Agent 1 fetches live, 2 extracts, 3 reviews.
              Needs the network. The only mode that touches a vendor's servers.

    REPLAY    Agent 1 loads the corpus from disk; Agent 2 RE-READS the cached
              HTML and re-extracts; Agent 3 reviews.
              Needs `data/cache/html/`. No network. This is the offline replay
              the README promises and the client asked to see demonstrated.

    REVIEW    Agents 1 and 2 both load their saved output; only Agent 3 runs.
              Needs neither the network nor the cache.
              THIS IS THE ONLY MODE THE SUBMITTED ARCHIVE SUPPORTS, because the
              client asked on 18 Aug that the 22 MB cache of verbatim
              third-party HTML not be redistributed.

Naming the third mode is how the two client instructions are reconciled instead
of merely coexisting: item 3 says do not ship the cache, item 5 says demonstrate
offline replay. The answer is that the archive replays the REVIEW stage offline
out of the box, and replays the full pipeline once the reviewer re-collects —
which the README explains how to do.

THE PREFLIGHT, AND WHY IT REFUSES INSTEAD OF DEGRADING
-------------------------------------------------------
DEFECT 40, found 18 Aug 2026 by deleting `data/cache/html/` and running the
pipeline exactly as a reviewer of the submitted archive would.

Agent 2 skipped every page whose cached HTML it could not find, recorded that
faithfully in its audit trail, and returned eight NOT_FOUND fields per vendor
with an empty evidence list. The brief a human then reads said, under all eight
fields of all seven vendors:

    Status: NOT_FOUND — nothing matched on any page we could read

about pages nobody had opened. Seven real companies reported as publishing no
security information, no privacy policy and no pricing, in a confident,
uncaveated document, produced by the tool whose entire stated purpose is that
"the dangerous failure is not a missing answer, it is a confident answer about a
company that nobody checked".

Agent 2 now attaches a caveat that reaches the brief, so the output is honest
even if this preflight is bypassed — a guard should not be the only guard. But
the orchestrator refuses outright, because a REPLAY that quietly produces a
REVIEW-quality answer is the defect-34 failure again: a mode that silently
becomes a different mode is indistinguishable from one that worked.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from datetime import datetime
from pathlib import Path

from .agent1_collect import (collect_for_vendor, load_previous_run, save_corpus,
                             save_run)
from .agent2_extract import (extract_for_vendor, load_fields, resolve_html_path,
                             save_fields)
from .agent3_review import review_vendor, save_brief

COLLECT = "collect"
REPLAY = "replay"
REVIEW = "review"
MODES = (COLLECT, REPLAY, REVIEW)


@dataclass
class Stage:
    """
    One line of the ORCHESTRATOR's own audit trail.

    Deliberately separate from `CollectionStep`, `ExtractionStep` and
    `ReviewStep`. Those record what happened INSIDE an agent; this records what
    was handed BETWEEN them, which is the layer where defect 34 lived and the
    layer no existing trail covers.
    """

    agent: str          # agent1 | agent2 | agent3 | preflight
    action: str         # ran | replayed | loaded | skipped | refused
    detail: str


@dataclass
class WorkflowResult:
    """
    Everything one pass produced, plus an explicit account of what it did not.

    `stopped_because` is the field that matters. A workflow that stops must say
    so in its RETURN VALUE, not by raising: Streamlit swallows exceptions into a
    red box that loses the surrounding state, and a CLI that dies on a traceback
    teaches nobody anything. "Never let a refusal be a bare boolean" is already
    a principle in this project (defect 4, where a robots.txt refusal carried no
    reason and blamed the vendor). A refusal with no reason attached is the same
    bug in a new place.
    """

    vendor_slug: str
    mode: str
    records: list[dict] = dc_field(default_factory=list)
    fields: list[dict] = dc_field(default_factory=list)
    brief: dict | None = None
    stages: list[Stage] = dc_field(default_factory=list)
    stopped_because: str = ""

    @property
    def ok(self) -> bool:
        return not self.stopped_because and self.brief is not None


# ---------------------------------------------------------------------------
# PREFLIGHT
# ---------------------------------------------------------------------------

def cache_status(records: list[dict], root: Path) -> tuple[list[str], list[str]]:
    """
    Which collected pages still have their cached HTML on THIS machine.

    Returns (present_source_types, missing_source_types).

    Pages Agent 1 marked unreadable are excluded from both lists: Agent 2 will
    not open them either way, so counting them as "missing cache" would raise a
    false alarm about a page that is working exactly as documented. The two
    failures look identical from the filesystem and mean opposite things — one
    is a fact about the vendor's site, the other a fact about our archive — and
    this project's recurring lesson is that collapsing two different findings
    into one label is how a tool starts lying.

    Uses `resolve_html_path`, not its own path logic, so that a corpus written on
    another machine resolves here identically to the way Agent 2 resolves it. A
    preflight that disagrees with the thing it is checking is worse than none.
    """
    present: list[str] = []
    missing: list[str] = []
    for record in records:
        if record.get("content_usable") is False:
            continue
        source_type = record.get("source_type", "?")
        if resolve_html_path(record.get("raw_html_path", ""), root) is None:
            missing.append(source_type)
        else:
            present.append(source_type)
    return present, missing


def _stale_extraction(corpus_dir: Path, slug: str) -> str:
    """
    Was the saved extraction produced from the saved corpus, or from an older one?

    `app.py` already discards an extraction when Agent 1 re-runs, so the UI path
    is safe. Nothing protected the file-based path: `tools/review_all.py` reads
    `<slug>.json` and `<slug>_fields.json` side by side and cannot tell that one
    is newer than the other. Agent 3 would then review yesterday's evidence
    against today's sources and report a coverage figure belonging to neither.

    Returns a human-readable warning, or "" when the pair is consistent. It is a
    warning rather than a refusal because the honest response to "these two files
    may not match" is to say so, not to decide for the reviewer.
    """
    corpus = corpus_dir / f"{slug}.json"
    fields = corpus_dir / f"{slug}_fields.json"
    if not (corpus.exists() and fields.exists()):
        return ""
    if fields.stat().st_mtime < corpus.stat().st_mtime:
        return (f"{slug}_fields.json is OLDER than {slug}.json — the saved "
                f"extraction was built from a different corpus. Re-run Agent 2 "
                f"before trusting this brief.")
    return ""


# ---------------------------------------------------------------------------
# THE WORKFLOW
# ---------------------------------------------------------------------------

def run_workflow(
    vendor: dict,
    cfg: dict,
    field_dictionary: dict,
    settings: dict,
    root: Path,
    mode: str = REVIEW,
    fetcher=None,
    save: bool = True,
) -> WorkflowResult:
    """
    Run Agent 1 -> Agent 2 -> Agent 3 for one vendor and return everything.

    `mode` is COLLECT, REPLAY or REVIEW — see the module docstring.
    `fetcher` is required for COLLECT only, and is injected rather than built
    here so that no test can start a real HTTP request by accident.
    `save` writes each agent's output to `data/` exactly as the UI does; pass
    False to run the pipeline without touching the corpus on disk.

    The three agents are called in a fixed order with no branching between them.
    That is the whole design: the brief forbids manager agents and autonomous
    loops, and a linear flow is the only shape in which a reviewer can point at
    a line and say what ran next.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")

    slug = vendor["slug"]
    corpus_dir = root / settings["output"]["corpus_dir"]
    briefs_dir = root / settings["output"]["briefs_dir"]
    result = WorkflowResult(vendor_slug=slug, mode=mode)
    ran_on = datetime.now().isoformat(timespec="seconds")

    # --- AGENT 1 ------------------------------------------------------------
    if mode == COLLECT:
        if fetcher is None:
            result.stopped_because = ("collect mode needs a PageFetcher; none was "
                                      "supplied. Nothing was fetched.")
            result.stages.append(Stage("agent1", "refused", result.stopped_because))
            return result
        records_obj, steps = collect_for_vendor(
            vendor, cfg["url_patterns"], fetcher,
            max_pages=settings["fetch"]["max_pages_per_vendor"],
            max_requests=settings["fetch"]["max_requests_per_vendor"],
            min_usable_text_chars=settings["fetch"]["min_usable_text_chars"],
            min_readable_chars_per_kb=settings["fetch"]["min_readable_chars_per_kb"],
        )
        records = [r.to_dict() for r in records_obj]
        trail = [s.__dict__ for s in steps]
        if save:
            save_corpus(records_obj, corpus_dir, slug)
            save_run(steps, corpus_dir, slug, ran_on=ran_on)
        result.stages.append(Stage(
            "agent1", "ran",
            f"fetched {len(records)} page(s) live from {vendor['name']}"))
    else:
        previous = load_previous_run(corpus_dir, slug)
        if not previous:
            result.stopped_because = (
                f"no corpus on disk for {slug}. Run Agent 1 in collect mode "
                f"first, or re-collect the public sources as the README "
                f"describes — the submitted archive ships the structured corpus, "
                f"not the pages themselves.")
            result.stages.append(Stage("agent1", "refused", result.stopped_because))
            return result
        records = previous["records"]
        trail = previous["steps"]
        result.stages.append(Stage(
            "agent1", "replayed",
            f"loaded {len(records)} page(s) collected on {previous.get('ran_on', '?')} "
            f"— no network request was made"))

    result.records = records

    # THE HANDOFF THAT DEFECT 34 BROKE, MADE EXPLICIT.
    #
    # Agent 2 must be told which page types Agent 1 never managed to collect.
    # Without it, it cannot tell "we searched and found nothing" from "we never
    # found the page to search" — that is defect 26, JetBrains, whose security
    # page 404'd six times while the field reported NOT_FOUND citing pricing and
    # docs. The fix for it then failed to execute for a further day because
    # Agent 1 emitted the `skip` step for seeded page types only.
    #
    # It is computed HERE rather than inside either agent so there is exactly one
    # definition of the handoff, and it is counted into the trail so that a
    # handoff which stops happening becomes visible instead of silent.
    never_collected = [s["source_type"] for s in trail if s.get("action") == "skip"]
    result.stages.append(Stage(
        "agent1", "loaded",
        f"{len(never_collected)} page type(s) never located and handed to Agent 2: "
        f"{', '.join(never_collected) or 'none'}"))

    # --- PREFLIGHT: defect 40 ----------------------------------------------
    if mode in (COLLECT, REPLAY):
        present, missing = cache_status(records, root)
        if missing:
            result.stopped_because = (
                f"{len(missing)} of {len(present) + len(missing)} readable page(s) "
                f"have no cached HTML on this machine ({', '.join(sorted(set(missing)))}). "
                f"Agent 2 would report them as NOT_FOUND — a statement about "
                f"{vendor['name']} that this run has no evidence for. "
                f"Re-collect the public sources (see the README), or run in "
                f"'{REVIEW}' mode, which reviews the saved extraction and needs "
                f"no cache.")
            result.stages.append(Stage("preflight", "refused", result.stopped_because))
            return result
        result.stages.append(Stage(
            "preflight", "ran",
            f"all {len(present)} readable page(s) present in the local cache — "
            f"Agent 2 can re-read every one"))

    # --- AGENT 2 ------------------------------------------------------------
    if mode in (COLLECT, REPLAY):
        fields_obj, esteps = extract_for_vendor(
            records, field_dictionary, settings, root,
            never_collected=never_collected)
        fields = [f.to_dict() for f in fields_obj]
        if save:
            save_fields(fields_obj, corpus_dir, slug, esteps, ran_on)
        result.stages.append(Stage(
            "agent2", "ran",
            f"{sum(1 for f in fields if f['status'] == 'FOUND')} of {len(fields)} "
            f"fields found from raw cached HTML"))
    else:
        saved = load_fields(corpus_dir, slug)
        if not saved:
            result.stopped_because = (
                f"no saved extraction for {slug}. Review mode reads Agent 2's "
                f"output; it cannot produce it. Run replay mode with the cache "
                f"present, or collect mode with a network connection.")
            result.stages.append(Stage("agent2", "refused", result.stopped_because))
            return result
        fields = saved["fields"]
        stale = _stale_extraction(corpus_dir, slug)
        result.stages.append(Stage(
            "agent2", "replayed",
            f"loaded {len(fields)} field(s) extracted on {saved.get('ran_on', '?')}"
            + (f" — WARNING: {stale}" if stale else "")))

    result.fields = fields

    # --- AGENT 3 ------------------------------------------------------------
    #
    # Agent 3 receives the corpus AND the fields AND Agent 1's trail. It needs
    # all three: the fields to judge, the records to know which pages were
    # readable, and the trail to know which were never found at all. The client
    # confined it to "review and synthesis rather than another complex
    # intelligence layer" — it adds no new extraction, and that is why it can be
    # handed everything without the flow stopping being linear.
    brief_obj, rsteps = review_vendor(
        vendor, fields, records, trail, field_dictionary, settings,
        cfg.get("category", ""))
    if save:
        save_brief(brief_obj, briefs_dir, rsteps)
    result.brief = brief_obj.to_dict()
    result.stages.append(Stage(
        "agent3", "ran",
        f"evidence {brief_obj.evidence_score}/10 {brief_obj.evidence_band}, "
        f"confidence {brief_obj.confidence_band}, "
        f"coverage {brief_obj.coverage_verified}/{brief_obj.coverage_total}, "
        f"{len(brief_obj.review_flags)} review flag(s)"))
    return result
