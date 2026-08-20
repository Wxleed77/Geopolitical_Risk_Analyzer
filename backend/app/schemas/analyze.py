from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    raw_input: Optional[str] = None
    country_a: Optional[str] = None
    country_b: Optional[str] = None
    conflict_type: Optional[str] = None


class SectorBreakdown(BaseModel):
    trade_score: float
    energy_score: float
    alliance_score: float
    financial_score: Optional[float] = None


class RankedCountry(BaseModel):
    iso_code: str
    name: str
    exposure_score: float = Field(ge=0, le=100)
    breakdown: SectorBreakdown


class NarrativeSection(BaseModel):
    heading: str
    text: str
    tag: str  # "data-derived" | "qualitative-cited"


class Citation(BaseModel):
    source: str
    url: str
    snippet: Optional[str] = None


class ShockDataPoint(BaseModel):
    """Real historical indicator movement backing a case-study citation -
    the actual number, not the LLM's paraphrase of it, so the frontend
    can chart it directly instead of parsing prose."""
    case_name: str
    country_iso: str
    indicator: str  # "fuel_price" | "cpi" | "currency"
    change_pct: float
    timeframe: str


class AnalyzeResponse(BaseModel):
    query_id: str
    ranked_countries: list[RankedCountry]
    sector_breakdown: list[SectorBreakdown]
    narrative_sections: list[NarrativeSection]
    citations: list[Citation]
    historical_shocks: list[ShockDataPoint] = []
    confidence_tags: list[str]


class BacktestCase(BaseModel):
    id: str
    name: str
    country_a: str
    country_b: str
    start_date: date


class BacktestRunRequest(BaseModel):
    cutoff_date: date


class BacktestRunResponse(BaseModel):
    predicted: AnalyzeResponse
    documented_outcome: str
    comparison_notes: str


class Country(BaseModel):
    iso_code: str
    name: str
    region: str


class IngestResponse(BaseModel):
    status: str
    records_ingested: int
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    db: str
    vector_db: str
