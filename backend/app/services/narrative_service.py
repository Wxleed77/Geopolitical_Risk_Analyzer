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

Each section's LLM call is independent of the others (different
country, different prompt, no shared state) - they're run through a
thread pool instead of a sequential loop, since this was previously
the single biggest contributor to /analyze's 60-90s latency (5+
sequential blocking HTTP calls to OpenRouter, one after another for
no reason - they don't depend on each other's output).
"""

from concurrent.futures import ThreadPoolExecutor

from app.models.tables import ConflictCase
from app.schemas.analyze import NarrativeSection, RankedCountry
from app.services.llm_client import LLMClient

MAX_WORKERS = 5

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


def _generate_country_section(
    country: RankedCountry, party_a_iso: str, party_b_iso: str, llm: LLMClient
) -> NarrativeSection:
    text = llm.complete(system=SYSTEM_PROMPT, user=build_user_prompt(country, party_a_iso, party_b_iso))
    return NarrativeSection(
        heading=f"{country.name} ({country.iso_code})", text=text.strip(), tag="data-derived"
    )


def build_narrative_sections(
    ranked_countries: list[RankedCountry],
    party_a_iso: str,
    party_b_iso: str,
    llm: LLMClient,
) -> list[NarrativeSection]:
    targets = ranked_countries[:TOP_N_TO_NARRATE]
    if not targets:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(targets))) as executor:
        # executor.map preserves input order in its results even though
        # the calls run concurrently - downstream code (heading-based
        # matching) still sees a deterministic order.
        return list(
            executor.map(
                lambda c: _generate_country_section(c, party_a_iso, party_b_iso, llm), targets
            )
        )


def _generate_case_section(case: ConflictCase, llm: LLMClient) -> NarrativeSection:
    text = llm.complete(system=CASE_STUDY_SYSTEM_PROMPT, user=build_case_study_prompt(case))
    return NarrativeSection(heading=case.name, text=text.strip(), tag="qualitative-cited")


def build_case_study_sections(cases: list[ConflictCase], llm: LLMClient) -> list[NarrativeSection]:
    if not cases:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(cases))) as executor:
        return list(executor.map(lambda c: _generate_case_section(c, llm), cases))
