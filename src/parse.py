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

from dataclasses import dataclass, field, asdict
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


def main_text(html: str) -> str:
    """
    The page's readable main content, with navigation, footers and boilerplate
    stripped. Stored as `collected_text` in the corpus.

    trafilatura does this well but is not always installed and occasionally
    returns nothing on unusual markup, so there is a BeautifulSoup fallback.
    Evidence extraction never uses this text — it works from the raw HTML so it
    can keep heading structure. This is for the corpus and for human reading.
    """
    try:
        import trafilatura

        extracted = trafilatura.extract(html, include_comments=False,
                                        include_tables=True, no_fallback=False)
        if extracted and extracted.strip():
            return extracted.strip()
    except Exception:
        pass  # fall through to the BeautifulSoup path

    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()
    return _clean(soup.get_text(" "))


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
) -> list[Evidence]:
    """
    Search blocks for any of `terms` and return the matching blocks as Evidence.

    `negative_terms` suppress a block outright (cookie banners, newsletter
    prompts, blog headlines arguing about a standard rather than claiming it).

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
        if any(neg in text for neg in negative_terms):
            continue

        matched = [t for t in terms if t in text]
        if not matched:
            continue

        body_lower = b.body.lower()
        heading_lower = b.heading.lower()
        alt_lower = " ".join(b.alt_texts).lower()

        if any(t in body_lower for t in matched):
            where = "body"
        elif any(t in heading_lower for t in matched):
            where = "heading_only"
        elif any(t in alt_lower for t in matched):
            where = "alt_text_only"
        else:
            where = "heading_only"

        results.append(
            Evidence(
                heading=b.heading,
                snippet=(b.body or " | ".join(b.alt_texts))[:snippet_max_chars],
                matched_terms=matched,
                match_location=where,
                source_url=source_url,
                source_type=source_type,
            )
        )

    return results


def score_field_confidence(
    evidence: list[Evidence],
    authoritative_types: list[str],
    min_body_chars_for_high: int = 40,
) -> str:
    """
    Turn a list of Evidence into one of: High / Medium / Low / NOT_FOUND.

    The rule, in plain English (see docs/confidence_rules.md):
      High    - the vendor states it in prose, on one of its own authoritative
                pages (security / privacy / pricing / status / terms), and the
                surrounding text is substantial (>= min_body_chars_for_high).
      Medium  - stated in prose but on a secondary page (docs, blog, product),
                OR an authoritative page whose heading names it with no prose.
      Low     - only an image alt-text match, or a body too short to be a claim.
      NOT_FOUND - nothing matched. This is a legitimate, useful answer.
    """
    if not evidence:
        return "NOT_FOUND"

    best = "Low"
    for e in evidence:
        authoritative = e.source_type in authoritative_types

        if e.match_location == "body" and len(e.snippet) >= min_body_chars_for_high:
            level = "High" if authoritative else "Medium"
        elif e.match_location == "body":
            level = "Medium" if authoritative else "Low"
        elif e.match_location == "heading_only":
            level = "Medium" if authoritative else "Low"
        else:  # alt_text_only — never counts as more than a hint
            level = "Low"

        if ["Low", "Medium", "High"].index(level) > ["Low", "Medium", "High"].index(best):
            best = level

    return best
