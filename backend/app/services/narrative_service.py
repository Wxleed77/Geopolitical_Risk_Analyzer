"""
Turns ranked exposure scores into written narrative sections via LLM.

Deliberately scoped: this ONLY explains numbers that already exist from
scoring_service (real trade/energy/alliance data) - it does not invent
facts, and every section is tagged "data-derived". A future RAG layer
(news/context retrieval) is what unlocks "qualitative-cited" sections
with actual citations - not built yet, so citations always come back
empty from here.

LLMClient is injected (not constructed inside) so this stays
unit-testable with a fake client - no network access needed to test
the prompt-building/tagging logic.
"""

from app.schemas.analyze import NarrativeSection, RankedCountry
from app.services.llm_client import LLMClient

SYSTEM_PROMPT = (
    "You are a geopolitical analyst. You are given ONLY computed exposure "
    "scores (trade/energy/alliance data) for a country regarding a conflict "
    "between two other countries. Write 2-3 sentences explaining WHY this "
    "country is exposed, using ONLY the numbers given. Do not invent facts, "
    "events, or context not present in the data. Do not mention specific "
    "news events, dates, or claims you cannot verify from these numbers alone."
)

TOP_N_TO_NARRATE = 5


def build_user_prompt(country: RankedCountry, party_a_iso: str, party_b_iso: str) -> str:
    b = country.breakdown
    return (
        f"Country: {country.name} ({country.iso_code})\n"
        f"Conflict between: {party_a_iso} and {party_b_iso}\n"
        f"Composite exposure score: {country.exposure_score}/100\n"
        f"Trade exposure sub-score: {b.trade_score}/100\n"
        f"Energy dependency sub-score: {b.energy_score}/100\n"
        f"Alliance proximity sub-score: {b.alliance_score}/100\n"
    )


def build_narrative_sections(
    ranked_countries: list[RankedCountry],
    party_a_iso: str,
    party_b_iso: str,
    llm: LLMClient,
) -> list[NarrativeSection]:
    sections = []
    for country in ranked_countries[:TOP_N_TO_NARRATE]:
        text = llm.complete(
            system=SYSTEM_PROMPT,
            user=build_user_prompt(country, party_a_iso, party_b_iso),
        )
        sections.append(
            NarrativeSection(
                heading=f"{country.name} ({country.iso_code})",
                text=text.strip(),
                tag="data-derived",
            )
        )
    return sections
