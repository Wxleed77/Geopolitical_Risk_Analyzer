import uuid

from fastapi import APIRouter, HTTPException

from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse

router = APIRouter(prefix="/analyze", tags=["analyze"])

# TODO: replace with real cache/DB lookup (services/scoring_service.py, agent_service.py)
_QUERY_CACHE: dict[str, AnalyzeResponse] = {}


@router.post("", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    if not payload.raw_input and not (payload.country_a and payload.country_b):
        raise HTTPException(
            status_code=422,
            detail="Provide either raw_input or country_a + country_b.",
        )

    # TODO: wire to agent_service orchestration (trade/energy/historical/context/critic agents)
    query_id = str(uuid.uuid4())
    result = AnalyzeResponse(
        query_id=query_id,
        ranked_countries=[],
        sector_breakdown=[],
        narrative_sections=[],
        citations=[],
        confidence_tags=["stub-response"],
    )
    _QUERY_CACHE[query_id] = result
    return result


@router.get("/{query_id}", response_model=AnalyzeResponse)
def get_analysis(query_id: str) -> AnalyzeResponse:
    result = _QUERY_CACHE.get(query_id)
    if result is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    return result
