import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.agents.context_agent import extract_conflict_parties
from app.agents.critic_agent import review_narrative
from app.models.tables import Country
from app.services.exposure_service import rank_exposure
from app.services.llm_client import LLMClient
from app.services.narrative_service import (
    build_case_study_prompt,
    build_case_study_sections,
    build_narrative_sections,
)
from app.services.rag_service import build_citation, find_relevant_case_studies
from app.services.impact_service import build_impact_sections, build_shock_prompt, get_shock_data_for_case

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analyze"])

# TODO: replace with real cache/DB-backed query log (ConflictQuery table)
_QUERY_CACHE: dict[str, AnalyzeResponse] = {}


@router.post("", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    if not payload.raw_input and not (payload.country_a and payload.country_b):
        raise HTTPException(
            status_code=422,
            detail="Provide either raw_input or country_a + country_b.",
        )

    country_a, country_b = payload.country_a, payload.country_b
    extracted_via_context_agent = False

    if payload.raw_input and not (country_a and country_b):
        settings = get_settings()
        if not settings.llm_api_key:
            raise HTTPException(
                status_code=501,
                detail="raw_input parsing requires an LLM (context agent) - "
                "LLM_API_KEY is not set. Pass country_a and country_b directly for now.",
            )
        country_a, country_b = extract_conflict_parties(payload.raw_input, LLMClient())
        if not country_a or not country_b:
            raise HTTPException(
                status_code=422,
                detail="Could not identify two distinct countries from raw_input. "
                "Try rephrasing, or pass country_a/country_b directly.",
            )
        known_isos = {c.iso_code for c in db.query(Country).all()}
        missing = [iso for iso in (country_a, country_b) if iso not in known_isos]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Identified {country_a}/{country_b} from raw_input, but no data "
                f"exists for: {', '.join(missing)}. Data is only seeded for a subset of "
                "countries currently.",
            )
        extracted_via_context_agent = True

    query_id = str(uuid.uuid4())
    ranked = rank_exposure(db, country_a, country_b)

    relevant_cases = find_relevant_case_studies(db, country_a, country_b)
    citations = [build_citation(case) for case in relevant_cases]

    confidence_tags = ["deterministic-scoring-real-data"]
    if extracted_via_context_agent:
        confidence_tags.append(f"parties-extracted-from-raw_input:{country_a}-vs-{country_b}")

    narrative_sections = []
    settings = get_settings()
    if settings.llm_api_key:
        try:
            client = LLMClient()
            narrative_sections = build_narrative_sections(ranked, country_a, country_b, client)
            citation_sources = {case.name: build_case_study_prompt(case) for case in relevant_cases}
            if relevant_cases:
                narrative_sections += build_case_study_sections(relevant_cases, client)

            for case in relevant_cases:
                impacts = get_shock_data_for_case(db, case)
                if impacts:
                    impact_sections = build_impact_sections(case, impacts, client)
                    narrative_sections += impact_sections
                    for sec in impact_sections:
                        citation_sources[sec.heading] = build_shock_prompt(case, impacts)

            narrative_sections, rejected = review_narrative(
                narrative_sections,
                ranked,
                country_a,
                country_b,
                client,
                citation_sources=citation_sources,
            )
            confidence_tags.append("narrative-critic-reviewed")
            if rejected:
                logger.info("Critic rejected %d narrative section(s): %s", len(rejected), rejected)
                confidence_tags.append(f"critic-rejected-{len(rejected)}-section(s)")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Narrative generation failed, continuing without it: %s", exc)
            confidence_tags.append("narrative-generation-failed")
    else:
        confidence_tags.append("narrative-skipped-no-llm-api-key")

    result = AnalyzeResponse(
        query_id=query_id,
        ranked_countries=ranked,
        sector_breakdown=[r.breakdown for r in ranked],
        narrative_sections=narrative_sections,
        citations=citations,
        confidence_tags=confidence_tags,
    )
    _QUERY_CACHE[query_id] = result
    return result


@router.get("/{query_id}", response_model=AnalyzeResponse)
def get_analysis(query_id: str) -> AnalyzeResponse:
    result = _QUERY_CACHE.get(query_id)
    if result is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    return result
