from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.tables import ConflictCase
from app.schemas.analyze import (
    AnalyzeResponse,
    BacktestCase,
    BacktestRunRequest,
    BacktestRunResponse,
)
from app.services.exposure_service import rank_exposure

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/cases", response_model=list[BacktestCase])
def list_cases(db: Session = Depends(get_db)) -> list[BacktestCase]:
    cases = db.execute(select(ConflictCase)).scalars().all()
    return [
        BacktestCase(
            id=str(c.id),
            name=c.name,
            country_a=c.country_a_iso,
            country_b=c.country_b_iso,
            start_date=c.start_date,
        )
        for c in cases
    ]


@router.post("/{case_id}/run", response_model=BacktestRunResponse)
def run_backtest(
    case_id: str, payload: BacktestRunRequest, db: Session = Depends(get_db)
) -> BacktestRunResponse:
    case = db.get(ConflictCase, int(case_id)) if case_id.isdigit() else None
    if case is None:
        raise HTTPException(status_code=404, detail="case_id not found")

    # LIMITATION (honest, not hidden): ingestion only holds a single-year
    # snapshot (2023) of trade/energy data, not per-date historical
    # series. So this can't truly "roll back" to payload.cutoff_date -
    # it scores using whatever data currently exists, which is only a
    # fair backtest for cases whose start_date is close to that snapshot
    # year. Real backtesting needs dated historical ingestion (future work).
    ranked = rank_exposure(db, case.country_a_iso, case.country_b_iso)
    predicted = AnalyzeResponse(
        query_id=f"backtest-{case_id}",
        ranked_countries=ranked,
        sector_breakdown=[r.breakdown for r in ranked],
        narrative_sections=[],
        citations=[],
        confidence_tags=[
            "deterministic-scoring-real-data",
            "NOT-time-adjusted-uses-current-snapshot-only",
        ],
    )
    return BacktestRunResponse(
        predicted=predicted,
        documented_outcome=case.documented_outcome,
        comparison_notes=(
            "Automatic comparison not implemented - the predicted ranking above "
            "used present-day (2023 snapshot) data, not data as of the "
            "requested cutoff_date, since only a single-year snapshot is "
            "ingested. Compare the ranked countries above against the "
            "documented_outcome text manually for now."
        ),
    )
