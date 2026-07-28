from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.tables import Country as CountryModel
from app.schemas.analyze import Country

router = APIRouter(tags=["countries"])

# Countries with no real data (WLD sentinel) are excluded - selecting
# them in the dropdown would just produce a confusing empty result.
EXCLUDED_ISOS = {"WLD"}


@router.get("/countries", response_model=list[Country])
def list_countries(db: Session = Depends(get_db)) -> list[Country]:
    rows = db.execute(select(CountryModel)).scalars().all()
    return [
        Country(iso_code=r.iso_code, name=r.name, region=r.region)
        for r in rows
        if r.iso_code not in EXCLUDED_ISOS
    ]
