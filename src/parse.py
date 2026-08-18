"""
parse.py — turn a raw HTML page into reviewable evidence blocks.

WHAT THIS FILE IS FOR
---------------------
This is the only file that knows what HTML looks like. Everything downstream
(the Evidence Extraction Agent, the Brief Review Agent, the Streamlit UI) works
with the simple `Block` objects produced here and never touches HTML again.

THE CENTRAL IDEA
----------------
Do NOT search a whole page for a phrase. Instead:
  1. Cut the page into BLOCKS along its own headings.
     One block = one heading + the paragraphs and list items beneath it.
  2. Search each block for terms from config/field_dictionary.yaml.
  3. When a block matches, keep the WHOLE block as evidence.

Why: a match tells you a phrase exists. A block tells you what the page
actually said, under which heading — which is what a human reviewer needs and
what the project brief calls a "source-backed evidence snippet".

WHY NOT REGULAR EXPRESSIONS
---------------------------
Vendors write the same fact differently: "SOC 2 Type II" (Linear),
"SOC 2 Type 2" (GitLab), "SOC 2 and 3" (Postman), "Service Organization
Controls" (Linear), or as an image with alt-text "AICPA SOC logo" (Atlassian).
A regex grows one hack per vendor until nobody can read it, and it still can't
tell you what the page said. A plain list of phrases in a YAML file can be read,
audited and extended by a non-technical reviewer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import Iterable

from bs4 import BeautifulSoup

# HTML tags that start a new block.
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
# HTML tags whose text belongs to the block currently being built.
BODY_TAGS = ("p", "li", "dd", "dt", "td", "blockquote")
# Tags we strip before parsing: they contain code or boilerplate, never evidence.
NOISE_TAGS = ("script", "style", "noscript", "nav", "footer", "form", "svg")


@dataclass
class Block:
    """One heading and everything written under it, until the next heading."""

    heading: str = "(top of page)"
    body: str = ""
    alt_texts: list[str] = field(default_factory=list)  # text found only in <img alt="...">
    source_tag: str = ""                                # which heading tag opened this block

    @property
    def searchable_text(self) -> str:
        """Everything in this block, lower-cased, for term matching."""
        return " ".join([self.heading, self.body, " ".join(self.alt_texts)]).lower()

    def to_dict(self) -> dict:
        return asdict(self)


def _clean(text: str) -> str:
    """Collapse whitespace so snippets read as sentences, not as ragged HTML."""
    return " ".join(text.split())


def page_title(html: str) -> str:
    """The page's <title>, used as `page_title` in the corpus."""
    soup = BeautifulSoup(html, "lxml")
    return _clean(soup.title.get_text()) if soup.title else ""


# If trafilatura keeps less than this share of the page's visible text, we do not
# trust it and fall back to the full text. Chosen from measured GitLab pages on
# 2026-08-10: privacy 79%, terms 67%, pricing 57%, product 42%, docs 23%,
# status 17% — and security 7.6%, where trafilatura discarded the entire
# compliance section including "GitLab maintains a SOC 2 Type 2 report...".
MIN_KEPT_RATIO = 0.15
MIN_TEXT_FOR_RATIO_CHECK = 1000

# A second, absolute guard. GitLab's status page passed the ratio test at 17%
# but produced only 489 characters from a 2,858-character page - technically
# within tolerance, still too thin to be a fair record of the page. A summary
# this short from a substantial page is a summary worth distrusting.
MIN_ABSOLUTE_CHARS = 800
# The gate was 2000, which let a second thin page through: Atlassian's status
# page has 1,578 characters of visible text and trafilatura kept 295 of them —
# 19%, so the ratio guard passed, and 1,578 < 2,000, so the absolute guard never
# ran. The heading "All Systems Operational" was thrown away.
# 1.5x the floor is derivable rather than picked: do not demand 800 characters
# from a page that does not have meaningfully more than 800 to give.
MIN_PAGE_CHARS_FOR_ABSOLUTE_CHECK = int(MIN_ABSOLUTE_CHARS * 1.5)


def visible_text(html: str) -> str:
    """All visible text on the page, boilerplate included. The safety net."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()
    return _clean(soup.get_text(" "))


def main_text(html: str) -> tuple[str, str]:
    """
    The page's readable main content. Returns (text, extractor_used).

    Stored as `collected_text` in the corpus, and read by humans reviewing the
    corpus. Evidence extraction does NOT use it — `find_evidence` works from the
    raw HTML so it keeps heading structure. That separation turned out to matter:
    on GitLab's security page trafilatura threw away 92% of the text, including
    every certification sentence, while the raw HTML kept them under an
    <h3>SOC Certification</h3> heading. Had the evidence pipeline been built on
    this field, the project would have reported "no certifications found" for a
    vendor that publishes them plainly.

    Guard: a cleaner that keeps almost nothing is not doing its job, so we
    measure what it kept and fall back to the full visible text when it strips
    too much. The extractor actually used is recorded in the corpus so a reviewer
    can see which pages needed the fallback.
    """
    fallback = visible_text(html)

    try:
        import trafilatura

        extracted = trafilatura.extract(html, include_comments=False,
                                        include_tables=True, no_fallback=False)
    except Exception:
        return fallback, "visible-text (trafilatura unavailable)"

    if not extracted or not extracted.strip():
        return fallback, "visible-text (trafilatura returned nothing)"

    extracted = extracted.strip()

    if (len(fallback) > MIN_TEXT_FOR_RATIO_CHECK
            and len(extracted) / len(fallback) < MIN_KEPT_RATIO):
        return fallback, (
            f"visible-text (trafilatura kept only "
            f"{len(extracted) / len(fallback):.0%} of the page)"
        )

    if (len(extracted) < MIN_ABSOLUTE_CHARS
            and len(fallback) > MIN_PAGE_CHARS_FOR_ABSOLUTE_CHECK):
        return fallback, (
            f"visible-text (trafilatura returned only {len(extracted)} chars "
            f"from a {len(fallback)}-char page)"
        )

    return extracted, "trafilatura"


def page_to_blocks(html: str) -> list[Block]:
    """
    Split an HTML page into Block objects.

    Falls back gracefully: pages built entirely from <div>s with no headings
    (common on modern marketing sites) still produce blocks — each paragraph
    becomes its own block with the heading "(no heading)". You lose the heading
    context but you keep the sentence, which is the part that matters.
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()  # remove the tag AND its contents from the tree

    blocks: list[Block] = []
    current = Block()
    body_parts: list[str] = []
    saw_any_heading = False

    def close_current() -> None:
        """Finish the block being built and add it to the list if it has content."""
        current.body = _clean(" ".join(body_parts))
        if current.body or current.alt_texts or current.heading != "(top of page)":
            blocks.append(current)

    for el in soup.find_all(list(HEADING_TAGS) + list(BODY_TAGS) + ["img"]):
        if el.name in HEADING_TAGS:
            saw_any_heading = True
            close_current()
            current = Block(heading=_clean(el.get_text(" ")), source_tag=el.name)
            body_parts = []
        elif el.name == "img":
            # Atlassian publishes its certifications as logos. The ONLY text is
            # the alt attribute. We capture it, but keep it separate from body
            # text so confidence scoring can mark it Low — an alt-text match is
            # a hint that a human should look, not a verified fact.
            alt = _clean(el.get("alt", ""))
            if alt:
                current.alt_texts.append(alt)
        else:
            text = _clean(el.get_text(" "))
            if text:
                body_parts.append(text)

    close_current()

    if not saw_any_heading:
        # FALLBACK PATH — the page has no <h1>..<h6> at all.
        # Some marketing sites build everything from styled <div>s. We cannot
        # recover heading context there, so we make each paragraph its own block.
        # The sentence is preserved; only the "which section was this under?"
        # information is lost. Confidence scoring sees these as heading-less,
        # which is why such matches rarely reach High.
        fallback = [
            Block(heading="(no heading)", body=_clean(el.get_text(" ")), source_tag="fallback")
            for el in soup.find_all(BODY_TAGS)
            if _clean(el.get_text(" "))
        ]
        alts = [_clean(i.get("alt", "")) for i in soup.find_all("img") if _clean(i.get("alt", ""))]
        if alts:
            fallback.append(Block(heading="(no heading)", body="", alt_texts=alts,
                                  source_tag="fallback"))
        if fallback:
            return fallback

    return blocks


# ---------------------------------------------------------------------------
# TERM MATCHING
#
# A term is still a plain phrase written by a human in field_dictionary.yaml.
# What changed is HOW it is compared against the page.
#
# THE BUG THIS REPLACES (found 2026-08-12 by reading Agent 2's first real output
# on the GitLab corpus, not by any test):
#   Matching was `term in text` — a bare substring test. On GitLab's seven pages
#   the term "sla" appeared 13 times and only 2 were the acronym; the other 11
#   were the word "Slack". The term "cli" appeared 9 times and NONE were the
#   command line interface — they were "click", "clicked", "clicking", "client",
#   "decline", "declined". The visible consequence: GitLab's uptime & SLA field
#   was reported FOUND / High, quoting a sentence from GitLab's PRIVACY POLICY
#   about third-party vendors. A brief that says that is worse than one that
#   says NOT_FOUND, because a reviewer has no reason to distrust it.
#
# THE FIX: require a term to sit on its own, not inside a longer word. "sla"
# matches "SLA:" and "an SLA" but not "Slack". "cli" matches "the CLI." but not
# "click".
#
# WHY THE BOUNDARY IS CONDITIONAL: some terms start or end with punctuation —
# "% uptime" is a real term, and it is always preceded by a digit ("99.99%
# uptime"). Demanding a non-alphanumeric character before the "%" would reject
# every genuine match. So the boundary is only applied at an end of the term
# that is itself alphanumeric.
#
# WHY NOT \b: Python's \b is defined against \w, which includes the underscore
# and, under re.UNICODE, accented letters. Spelling the character class out
# keeps the rule readable to someone who does not write regular expressions,
# which matters because this file is meant to be auditable.
# ---------------------------------------------------------------------------

_WORD_CHAR = "a-z0-9"


@lru_cache(maxsize=2048)
def _term_pattern(term: str) -> re.Pattern:
    """
    Compile one dictionary term into a whole-token matcher.

    Cached because a full vendor extraction asks the same ~150 terms about the
    same blocks hundreds of times; compiling each one once keeps a seven-page
    vendor under two seconds.
    """
    body = re.escape(term)
    prefix = f"(?<![{_WORD_CHAR}])" if term[:1].isalnum() else ""
    suffix = f"(?![{_WORD_CHAR}])" if term[-1:].isalnum() else ""
    return re.compile(prefix + body + suffix)


# How much text to keep BEFORE the matched term when a block has to be
# truncated. Enough to see the start of the sentence the term sits in.
SNIPPET_LEAD_CHARS = 120


def snippet_around(text: str, terms: list[str], max_chars: int) -> str:
    """
    Cut `max_chars` out of `text`, centred on the FIRST place a term appears.

    WHY THIS EXISTS (defect 20, found 2026-08-12 in the browser): the snippet
    used to be `text[:max_chars]` — the first 600 characters of the block,
    regardless of where the match was. On GitLab's pricing page that produced an
    evidence card reading "matched `sla` in the body" above 600 characters about
    SAST scanning and Container Registry, with no "SLA" anywhere in the quoted
    text, because the match sat at character 900 and had been cut away.

    That is not a cosmetic problem. The entire promise of this tool is that
    every statement traces back to the words on the page. A citation that does
    not contain the thing it cites is worse than no citation, because a reviewer
    checking it concludes the tool is lying rather than that it is truncating.

    Ellipses mark both ends so the reviewer can see the quote is an excerpt.
    """
    if len(text) <= max_chars:
        return text

    lower = text.lower()
    starts = [m.start() for m in
              (_term_pattern(t).search(lower) for t in terms) if m]
    first = min(starts) if starts else 0

    start = max(0, first - SNIPPET_LEAD_CHARS)
    if start > 0:
        # Begin at a word boundary rather than mid-word, but only if one is
        # close by — otherwise we would push past the match itself.
        space = text.find(" ", start)
        if 0 <= space < first:
            start = space + 1

    end = min(len(text), start + max_chars)
    excerpt = text[start:end]
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt = excerpt + "…"
    return excerpt


def strip_noise(text: str, noise_phrases: list[str] | None) -> str:
    """
    Remove interface furniture from text before it is quoted to a reviewer.

    DEFECT 29, found 13 Aug 2026 by reading GitHub's evidence cards. Four of them
    quoted the vendor as saying:

        "There was an error while loading. Please reload this page . SOC1, SOC2,
         type 2 reports annually GitHub offers AICPA System and Organization
         Controls (SOC) 1 Type 2 and SOC 2 Type 2 reports…"

    GitHub's pricing page renders a placeholder for panels that fail to load, and
    the placeholder text was captured faithfully, quoted verbatim, and presented
    as due-diligence material. It is real text on the page, so nothing upstream
    was wrong; it is simply not something the vendor is telling us.

    This is NOT `negative_terms`. A negative term suppresses the whole block, and
    suppressing this block would have thrown away the SOC 2 sentence sitting
    inside it — trading a cosmetic defect for a material one. Noise phrases are
    cut out of the text and the rest of the block is kept.

    It is not cosmetic either. "There was an error while loading." is a
    41-character complete sentence, and `evidence_level` awards High to any
    authoritative block containing a sentence of 40 characters or more. Left in,
    a page that failed to render could earn High confidence on the strength of
    its own error message.

    Matching is case-insensitive and literal. Whitespace is re-collapsed
    afterwards so the quote still reads as prose rather than as a gapped string.
    """
    if not noise_phrases or not text:
        return text
    cleaned = text
    for phrase in noise_phrases:
        if not phrase:
            continue
        cleaned = re.sub(re.escape(phrase), " ", cleaned, flags=re.IGNORECASE)
    # Tidy the punctuation left stranded where a phrase was removed, then
    # re-collapse whitespace. Without this a quote can begin with " . " or carry
    # a double full stop where the placeholder used to be.
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"([.,;:!?])\1+", r"\1", cleaned)
    return _clean(cleaned)


def term_in(term: str, text: str) -> bool:
    """
    Does `term` appear in `text` as its own word or phrase?

    `text` is expected to be lower-cased already (Block.searchable_text does
    this). Kept as a named function rather than an inline expression so tests
    can assert the rule directly: `term_in("sla", "slack") is False`.
    """
    return bool(term and _term_pattern(term).search(text))


# ---------------------------------------------------------------------------
# PROSE vs LIST
#
# A sentence ends at . ! or ? followed by whitespace and a capital letter or a
# digit. Deliberately simple: it splits marketing prose correctly, and when it
# is wrong it errs by returning MORE text, never less.
# ---------------------------------------------------------------------------

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_HAS_SENTENCE_PUNCTUATION = re.compile(r"[.!?](\s|$)")


def split_sentences(text: str) -> list[str]:
    """Break a snippet into sentences. Used to quote one, and to measure them."""
    return [s.strip() for s in _SENTENCE_END.split(text.strip()) if s.strip()]


def longest_sentence_length(text: str) -> int:
    """
    Length of the longest complete sentence in `text`, or 0 if there are none.

    THIS IS THE MEASUREMENT THE CONFIDENCE RULE NEEDS, AND IT REPLACES A WRONG
    ONE (defect 15, found 2026-08-12 by reading the code against its own
    documentation).

    docs/confidence_rules.md has always said the 40-character floor exists
    "because a fragment such as 'SOC 2 and 3' is a label, not a claim". The code
    measured `len(snippet)` — the length of the whole matched BLOCK. A block
    that is a bullet list of certifications concatenates well past 40
    characters, so the rule the document described was never the rule the code
    applied. Measured consequence on the real GitLab corpus: the uptime field
    scored **High** on the pricing bullet "Advanced CI/CD Team Project
    Management SLA Management Priority Support" — a feature list, scored as a
    reliability commitment.

    Returning 0 when the text contains no sentence-ending punctuation at all is
    the important half. "Includes $12 in GitLab Credits per user per month*" is
    49 characters and would clear a naive length test; it is still a label.
    A claim a vendor can be held to is written as a sentence.
    """
    if not _HAS_SENTENCE_PUNCTUATION.search(text):
        return 0
    sentences = split_sentences(text)
    return max((len(s) for s in sentences), default=0)


@dataclass
class Evidence:
    """One matched block, ready to be shown to a human reviewer."""

    heading: str
    snippet: str
    matched_terms: list[str]
    match_location: str  # "body" | "heading_only" | "alt_text_only"
    source_url: str = ""
    source_type: str = ""


def find_evidence(
    blocks: Iterable[Block],
    terms: list[str],
    negative_terms: list[str] | None = None,
    snippet_max_chars: int = 600,
    source_url: str = "",
    source_type: str = "",
    noise_phrases: list[str] | None = None,
) -> list[Evidence]:
    """
    Search blocks for any of `terms` and return the matching blocks as Evidence.

    `negative_terms` suppress a block outright (cookie banners, newsletter
    prompts, blog headlines arguing about a standard rather than claiming it).

    `noise_phrases` are cut out of the quoted text but leave the block standing —
    interface furniture such as a failed-panel placeholder. See `strip_noise`
    for why the two mechanisms have to be different.

    `match_location` records WHERE the term was found, because that determines
    how much the evidence is worth:
        body           -> the page states it in prose            (strongest)
        heading_only   -> a heading names it, nothing explains it (weaker)
        alt_text_only  -> only an image's alt attribute          (weakest)
    """
    negative_terms = [t.lower() for t in (negative_terms or [])]
    terms = [t.lower() for t in terms]
    results: list[Evidence] = []

    for b in blocks:
        text = b.searchable_text
        if any(term_in(neg, text) for neg in negative_terms):
            continue

        matched = [t for t in terms if term_in(t, text)]
        if not matched:
            continue

        body_lower = b.body.lower()
        heading_lower = b.heading.lower()
        alt_lower = " ".join(b.alt_texts).lower()

        if any(term_in(t, body_lower) for t in matched):
            where = "body"
        elif any(term_in(t, heading_lower) for t in matched):
            where = "heading_only"
        elif any(term_in(t, alt_lower) for t in matched):
            where = "alt_text_only"
        else:
            where = "heading_only"

        # QUOTE THE PART THAT ACTUALLY MATCHED (defect 22, found while measuring
        # defect 20 on the real GitLab corpus).
        #
        # The snippet used to be `b.body or alt_texts` — body if there was any.
        # So a block with prose AND images, where the term matched only an image's
        # alt attribute, was quoted with its prose. GitLab's security page has a
        # "VPAT Compliance" block whose prose is about its Accessibility
        # Conformance Report and whose image alt-text mentions GDPR: the card read
        # "matched `gdpr`" above a sentence about accessibility. Same failure as
        # defect 20 — a citation that does not contain what it cites — from a
        # different direction.
        #
        # `heading_only` keeps the body, because the heading is displayed above
        # the snippet in its own right, so the reviewer still sees the match.
        #
        # DEFECT 28 (found 13 Aug 2026 by asking why GitHub's own /security page
        # contributed nothing to its security field). GitHub publishes
        #     <h2>GitHub's API stays secure with ISO, SOC 2, and GDPR.</h2>
        # with NO paragraph beneath it. `b.body` was therefore "", there were no
        # alt texts, and `quotable` fell through to the empty string — so the
        # single most precise sentence GitHub publishes about its security became
        # an evidence card with an EMPTY QUOTE, scored on 0 characters, and was
        # dropped by the three-evidence cap.
        #
        # A heading with nothing under it is still the vendor's own words. Fall
        # back to it rather than emitting a citation with no text in it. The
        # `heading_only` label is kept — we are not pretending it was prose — and
        # `evidence_level` decides what it is worth by measuring the sentence.
        #
        # A ROUTE NOT TAKEN, RECORDED BECAUSE IT LOOKED RIGHT AND WAS NOT.
        # The first attempt fell back only when the heading was a complete
        # sentence, dropping the block otherwise. Measured against the corpus,
        # that turned Linear's pricing field and Sentry's data-residency field
        # from a weak FOUND into a clean NOT_FOUND — a flat statement that Linear
        # publishes no pricing information, about a vendor whose pricing page we
        # read successfully. Trading a poor quote for a false negative is the
        # exact failure defect 23 exists to prevent, so the fallback stays
        # unconditional and `evidence_level` grades it instead.
        if where == "alt_text_only":
            quotable = " | ".join(b.alt_texts)
        else:
            quotable = b.body or " | ".join(b.alt_texts) or b.heading

        # Noise is removed BEFORE the snippet window is cut, so the 600
        # characters a reviewer sees are 600 characters of vendor text rather
        # than 600 characters partly spent on a placeholder, and so the sentence
        # measurement in `evidence_level` never scores the placeholder.
        quotable = strip_noise(quotable, noise_phrases)
        if not quotable:
            # Nothing left to quote: the block was a bare section label, or it
            # was nothing but interface furniture. Either way an evidence card
            # with no quote is not evidence, and printing one invites a reviewer
            # to trust a citation they cannot read. Before this, such blocks were
            # emitted with `snippet=""` and still counted toward the field's
            # confidence — a field could be FOUND on the strength of a quote that
            # did not exist.
            continue

        results.append(
            Evidence(
                heading=b.heading,
                snippet=snippet_around(quotable, matched, snippet_max_chars),
                matched_terms=matched,
                match_location=where,
                source_url=source_url,
                source_type=source_type,
            )
        )

    return results


LEVEL_ORDER = ["Low", "Medium", "High"]


def evidence_level(
    e: Evidence,
    authoritative_types: list[str],
    min_body_chars_for_high: int = 40,
) -> str:
    """
    Score ONE piece of evidence: High, Medium or Low.

    Split out from `score_field_confidence` so that two things can share it:
    the field's overall confidence (the best level across all its evidence) and
    the ranking in Agent 2 (strongest first). Sharing one function is what makes
    the brief coherent — the quote a reviewer reads is always the piece of
    evidence that produced the confidence level printed beside it. When these
    were computed separately, GitLab's uptime field printed **High** above a
    quoted feature bullet that was itself only Medium, because a different,
    lower-ranked block had earned the High. A brief whose headline and its
    citation disagree is worse than one that scores conservatively.

    SECOND HALF OF DEFECT 28 (13 Aug 2026). The rule used to be keyed on
    `match_location == "body"` first and the sentence length second, so a heading
    could never reach High no matter what it said. That is right for a heading
    that is a LABEL — "SOC Certification", "Security" — and wrong for a heading
    that is a complete sentence. GitHub states
        "GitHub's API stays secure with ISO, SOC 2, and GDPR."
    in an <h2> with no paragraph under it: 52 characters, terminal punctuation,
    three named standards, on GitHub's own security page. Capping that at Medium
    ranked it ninth of nine candidates and kept it out of the brief entirely.

    So the test is now the SAME test for both: does this evidence contain a
    complete sentence long enough to be a claim? `longest_sentence_length`
    already returns 0 for text with no sentence punctuation, so a label-style
    heading still cannot reach High — it fails on its own merits rather than on
    where it happened to sit in the HTML. Prose that is not a sentence
    ("Advanced CI/CD Team Project Management SLA Management") is unchanged: it
    still scores Medium at best. Image alt-text is unchanged: never above Low,
    because a logo is not a claim regardless of how it reads.
    """
    authoritative = e.source_type in authoritative_types
    # The measured claim, not the surrounding furniture. See
    # longest_sentence_length.
    claim_length = longest_sentence_length(e.snippet)

    if e.match_location == "alt_text_only":
        return "Low"  # a logo is never a claim
    if claim_length >= min_body_chars_for_high:
        return "High" if authoritative else "Medium"
    if e.match_location == "heading_only":
        # A HEADING WITH NO STATEMENT UNDER IT IS A LABEL, AND A LABEL IS A
        # SIGNAL TO GO AND LOOK — WHICH IS WHAT `Low` -> `PARTIAL` IS FOR.
        #
        # This used to return Medium on an authoritative page, which made
        # `PARTIAL` unreachable: across seven vendors and 56 field results,
        # PARTIAL was produced exactly zero times, and a three-state vocabulary
        # with a dead state is a vocabulary that is lying about its precision.
        #
        # Linear's pricing page carries <h2>Pricing</h2> with no paragraph under
        # it. Sentry's carries <h2>Data Residency</h2>. Reporting either as
        # FOUND/Medium overstates it — nothing was quoted that a reviewer could
        # act on. Reporting NOT_FOUND understates it and is worse, because both
        # vendors plainly do publish the thing. PARTIAL is the honest middle:
        # "we saw the label, nobody wrote the claim, go and read the page."
        return "Low"
    return "Medium" if authoritative else "Low"


def score_field_confidence(
    evidence: list[Evidence],
    authoritative_types: list[str],
    min_body_chars_for_high: int = 40,
) -> str:
    """
    Turn a list of Evidence into one of: High / Medium / Low / NOT_FOUND.

    The rule, in plain English (see docs/confidence_rules.md):
      High    - the vendor states it in a SENTENCE, on one of its own
                authoritative pages (security / trust / privacy / pricing /
                status / terms), and that sentence is substantial
                (>= min_body_chars_for_high characters). The sentence may be
                set as a heading — see evidence_level, defect 28.
      Medium  - stated in a sentence but on a secondary page (docs, blog,
                product), OR prose on an authoritative page that never forms a
                sentence, such as a bullet list.
      Low     - an image alt-text match, or a BARE HEADING with nothing written
                under it, or a fragment on a secondary page.
      NOT_FOUND - nothing matched. This is a legitimate, useful answer.

    THE BARE-HEADING LINE CHANGED ON 13 AUG 2026. It used to read "named only in
    a heading ... on an authoritative page" under Medium, which contradicted
    `agent2_extract.status_from_confidence`, whose own docstring assigns "only a
    heading" to PARTIAL. The code followed this docstring, so PARTIAL was
    unreachable and never once occurred across seven vendors and 56 fields. Two
    docstrings describing one rule differently is how a codebase stops being
    auditable; the PARTIAL reading won because a label is a reason to go and
    look, which is exactly what PARTIAL means.

    "Sentence", not "block": see parse.longest_sentence_length. A bullet list of
    certifications is long, and it is still a label rather than a claim.
    """
    if not evidence:
        return "NOT_FOUND"

    return max(
        (evidence_level(e, authoritative_types, min_body_chars_for_high)
         for e in evidence),
        key=LEVEL_ORDER.index,
    )
