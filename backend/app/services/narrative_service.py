"""
Turns ranked exposure scores AND cited case studies into narrative
sections via LLM.

Two kinds of section, each with its own prompt:
- "data-derived": explains a country's exposure using ONLY its computed
  scores (trade/energy/alliance) - build_narrative_sections.
- "qualitative-cited": summarizes a real historical case study
  (rag_service.find_relevant_case_studies) as precedent - uses ONLY
  that case's description/outcome, never invents beyond it -
  build_case_study_sections.

LLMClient is injected (not constructed inside) so this stays
unit-testable with a fake client - no network access needed to test
the prompt-building/tagging logic.
"""

from app.models.tables import ConflictCase
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

CASE_STUDY_SYSTEM_PROMPT = (
    "You are a geopolitical analyst. You are given a real historical case "
    "study (a past conflict and its documented outcome). Write 2-3 "
    "sentences summarizing why this precedent is relevant context, using "
    "ONLY the information given. Do not invent additional facts, figures, "
    "or events beyond what's stated."
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


def build_case_study_prompt(case: ConflictCase) -> str:
    return (
        f"Case: {case.name}\n"
        f"Description: {case.description}\n"
        f"Documented outcome: {case.documented_outcome}\n"
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


def build_case_study_sections(cases: list[ConflictCase], llm: LLMClient) -> list[NarrativeSection]:
    sections = []
    for case in cases:
        text = llm.complete(
            system=CASE_STUDY_SYSTEM_PROMPT,
            user=build_case_study_prompt(case),
        )
        sections.append(
            NarrativeSection(heading=case.name, text=text.strip(), tag="qualitative-cited")
        )
    return sections
