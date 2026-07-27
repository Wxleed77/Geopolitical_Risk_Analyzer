import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.exposure_service import rank_exposure

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

    if payload.raw_input and not (payload.country_a and payload.country_b):
        # Free-text entity extraction needs the context agent (not built yet).
        raise HTTPException(
            status_code=501,
            detail="raw_input parsing requires the agent layer (not yet built). "
            "Pass country_a and country_b directly for now.",
        )

    query_id = str(uuid.uuid4())
    ranked = rank_exposure(db, payload.country_a, payload.country_b)

    # TODO: narrative_sections/citations require the RAG + agent + critic layer (not built yet)
    result = AnalyzeResponse(
        query_id=query_id,
        ranked_countries=ranked,
        sector_breakdown=[r.breakdown for r in ranked],
        narrative_sections=[],
        citations=[],
        confidence_tags=["deterministic-scoring-only", "no-narrative-yet"],
    )
    _QUERY_CACHE[query_id] = result
    return result


@router.get("/{query_id}", response_model=AnalyzeResponse)
def get_analysis(query_id: str) -> AnalyzeResponse:
    result = _QUERY_CACHE.get(query_id)
    if result is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    return result
