from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException

from app.core.config import get_settings
from app.schemas.analyze import IngestResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def _verify_admin_key(x_admin_key: str | None) -> None:
    settings = get_settings()
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key")


@router.post("/ingest/{source}", response_model=IngestResponse)
def trigger_ingest(source: str, x_admin_key: str | None = Header(default=None)) -> IngestResponse:
    _verify_admin_key(x_admin_key)

    valid_sources = {"comtrade", "eia", "alliances", "case_studies"}
    if source not in valid_sources:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")

    # TODO: dispatch to backend/ingestion/ingest_*.py scripts
    return IngestResponse(
        status="stub-triggered",
        records_ingested=0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
