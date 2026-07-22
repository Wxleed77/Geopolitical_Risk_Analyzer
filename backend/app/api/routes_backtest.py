from fastapi import APIRouter, HTTPException

from app.schemas.analyze import (
    AnalyzeResponse,
    BacktestCase,
    BacktestRunRequest,
    BacktestRunResponse,
)

router = APIRouter(prefix="/backtest", tags=["backtest"])

# TODO: load from data/case_studies (curated by ingestion/curate_case_studies.py)
_CASES: list[BacktestCase] = []


@router.get("/cases", response_model=list[BacktestCase])
def list_cases() -> list[BacktestCase]:
    return _CASES


@router.post("/{case_id}/run", response_model=BacktestRunResponse)
def run_backtest(case_id: str, payload: BacktestRunRequest) -> BacktestRunResponse:
    case = next((c for c in _CASES if c.id == case_id), None)
    if case is None:
        raise HTTPException(status_code=404, detail="case_id not found")

    # TODO: run scoring/agent pipeline against pre-cutoff data, compare to documented outcome
    predicted = AnalyzeResponse(
        query_id=f"backtest-{case_id}",
        ranked_countries=[],
        sector_breakdown=[],
        narrative_sections=[],
        citations=[],
        confidence_tags=["stub-backtest"],
    )
    return BacktestRunResponse(
        predicted=predicted,
        documented_outcome="TODO: pull from case study corpus",
        comparison_notes="TODO: generate via critic/comparison logic",
    )
