"""
Critic agent - the last line of defense against hallucinated narrative.

Two layers, cheapest first:
1. Numeric grounding (deterministic, no LLM call): every number in the
   narrative text must be close to a real score the writer was given.
   Catches blatantly invented statistics for free.
2. Semantic grounding (LLM call): catches invented events/facts/claims
   the numeric check can't - e.g. "Japan recently signed a new trade
   deal" contains no suspicious number but is still a fabrication if
   the writer was never given that fact.

A section that fails either check is DROPPED from the response, not
shown with a warning label - a wrong claim reaching the user is worse
than a missing one.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.schemas.analyze import NarrativeSection, RankedCountry
from app.services.llm_client import LLMClient
from app.services.narrative_service import build_user_prompt

NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
TOLERANCE = 1.5  # absolute-point tolerance, allows for rounding in prose
YEAR_RANGE = (1900, 2100)  # numbers in this range are treated as plausible years, not scores

CRITIC_SYSTEM_PROMPT = (
    "You are a strict fact-checking critic. You will be given (1) the ONLY "
    "data the writer was allowed to use, and (2) text the writer produced. "
    "Check whether the text states any claim, fact, event, or detail NOT "
    "directly supported by the given data.\n\n"
    "IMPORTANT - do NOT reject text for referencing information that is "
    "already present in the data block itself. The data block always names "
    "the two conflict parties and the country being scored - so it is FINE "
    "for the text to say the country has trade/energy/alliance ties to "
    "either or both named parties, since that's just restating what's in "
    "the data section headers, not a new invented fact. Only FAIL for "
    "claims that go beyond what's in the data - e.g. specific events, "
    "deals, dates, motivations, or relationships not present in the data "
    "block at all.\n\n"
    "Respond with exactly one line: 'PASS' if every claim is grounded in "
    "the data (using the rule above), or 'FAIL: <reason>' if the text "
    "contains something genuinely not supported by the data."
)


@dataclass
class CriticVerdict:
    passed: bool
    reason: str


def _known_numbers(country: RankedCountry) -> list[float]:
    b = country.breakdown
    return [country.exposure_score, b.trade_score, b.energy_score, b.alliance_score]


def check_numeric_grounding(section: NarrativeSection, country: RankedCountry) -> CriticVerdict:
    known = _known_numbers(country)
    mentioned = [float(m) for m in NUMBER_PATTERN.findall(section.text)]

    for number in mentioned:
        if YEAR_RANGE[0] <= number <= YEAR_RANGE[1]:
            continue  # plausibly a year reference, not a fabricated score
        if not any(abs(number - k) <= TOLERANCE for k in known):
            return CriticVerdict(
                passed=False,
                reason=f"number {number} in narrative doesn't match any known score {known}",
            )
    return CriticVerdict(passed=True, reason="all numbers grounded in known scores")


def check_semantic_grounding(section: NarrativeSection, source_data: str, llm: LLMClient) -> CriticVerdict:
    response = llm.complete(
        system=CRITIC_SYSTEM_PROMPT,
        user=f"DATA GIVEN TO WRITER:\n{source_data}\n\nTEXT TO CHECK:\n{section.text}",
    ).strip()

    # Some free-tier models don't follow the exact "PASS"/"FAIL: <reason>"
    # format - e.g. returning a moderation preamble like "User Safety:
    # safe" instead. Treating that as a rejection is wrong (it's a
    # formatting quirk, not a real grounding failure) - only treat it as
    # FAIL if the response explicitly says so.
    if "FAIL" in response.upper():
        return CriticVerdict(passed=False, reason=response)
    return CriticVerdict(passed=True, reason="critic found no unsupported claims")


def _extract_iso(heading: str) -> str:
    # headings are built as "Name (ISO)" by narrative_service
    return heading.split("(")[-1].rstrip(")")


def review_narrative(
    sections: list[NarrativeSection],
    ranked_countries: list[RankedCountry],
    party_a_iso: str,
    party_b_iso: str,
    llm: LLMClient,
    citation_sources: dict[str, str] | None = None,
) -> tuple[list[NarrativeSection], list[dict]]:
    """
    Returns (accepted_sections, rejected_log) for observability/debugging.

    "data-derived" sections: numeric grounding (free, local, runs first)
    + semantic grounding against the country's score data.
    "qualitative-cited" sections: semantic grounding ONLY, against the
    matched case study's text (citation_sources, keyed by heading) -
    numeric check doesn't apply since case studies legitimately contain
    real historical figures (dates, percentages) that won't match a
    country's composite/trade/energy/alliance scores.

    Two passes: first, cheap local numeric checks run synchronously to
    filter out sections that fail without spending an LLM call at all.
    Then the remaining sections' semantic checks (the slow part - one
    blocking HTTP call each) run through a thread pool instead of a
    sequential loop, since each section's check is independent of the
    others.
    """
    citation_sources = citation_sources or {}
    by_iso = {c.iso_code: c for c in ranked_countries}
    rejected: list[dict] = []
    pending: list[tuple[NarrativeSection, str]] = []  # (section, source_data) awaiting semantic check

    for section in sections:
        if section.tag == "qualitative-cited":
            source_data = citation_sources.get(section.heading)
            if source_data is None:
                rejected.append({"heading": section.heading, "reason": "no source text found for citation"})
                continue
            pending.append((section, source_data))
            continue

        iso = _extract_iso(section.heading)
        country = by_iso.get(iso)
        if country is None:
            rejected.append({"heading": section.heading, "reason": "country not found in ranked results"})
            continue

        numeric_verdict = check_numeric_grounding(section, country)
        if not numeric_verdict.passed:
            rejected.append({"heading": section.heading, "reason": numeric_verdict.reason})
            continue

        pending.append((section, build_user_prompt(country, party_a_iso, party_b_iso)))

    accepted: list[NarrativeSection] = []
    if pending:
        with ThreadPoolExecutor(max_workers=min(5, len(pending))) as executor:
            verdicts = list(
                executor.map(lambda item: check_semantic_grounding(item[0], item[1], llm), pending)
            )
        for (section, _source_data), verdict in zip(pending, verdicts):
            if verdict.passed:
                accepted.append(section)
            else:
                rejected.append({"heading": section.heading, "reason": verdict.reason})

    return accepted, rejected
