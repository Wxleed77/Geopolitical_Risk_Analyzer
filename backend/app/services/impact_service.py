from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import ConflictCase, HistoricalShockImpact
from app.schemas.analyze import NarrativeSection
from app.services.llm_client import LLMClient

SYSTEM_PROMPT = (
    "You are explaining how a conflict could feel for ordinary people in a "
    "country, using ONLY real historical precedent data given to you "
    "(what happened to fuel prices, inflation, or currency in a comparable "
    "past event). Write 2-3 sentences. Do not invent numbers beyond what's "
    "given. Frame it as 'in a comparable past event, X happened' - not as "
    "a certain prediction."
)


def get_shock_data_for_case(session: Session, case: ConflictCase) -> list[HistoricalShockImpact]:
    return session.execute(
        select(HistoricalShockImpact).where(HistoricalShockImpact.case_id == case.id)
    ).scalars().all()


def build_shock_prompt(case: ConflictCase, impacts: list[HistoricalShockImpact]) -> str:
    lines = [f"Historical precedent: {case.name}"]
    for imp in impacts:
        lines.append(
            f"- {imp.country_iso} {imp.indicator}: {imp.change_pct}% ({imp.timeframe}) - {imp.source_note}"
        )
    return "\n".join(lines)


def build_impact_sections(
    case: ConflictCase, impacts: list[HistoricalShockImpact], llm: LLMClient
) -> list[NarrativeSection]:
    if not impacts:
        return []
    prompt = build_shock_prompt(case, impacts)
    text = llm.complete(system=SYSTEM_PROMPT, user=prompt)
    return [
        NarrativeSection(
            heading=f"Household impact precedent: {case.name}",
            text=text.strip(),
            tag="qualitative-cited",
        )
    ]
