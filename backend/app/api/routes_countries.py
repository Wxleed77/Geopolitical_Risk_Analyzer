from fastapi import APIRouter

from app.schemas.analyze import Country

router = APIRouter(tags=["countries"])

# TODO: back with real ISO country table (seed from World Bank / Comtrade reference data)
_COUNTRIES: list[Country] = []


@router.get("/countries", response_model=list[Country])
def list_countries() -> list[Country]:
    return _COUNTRIES
