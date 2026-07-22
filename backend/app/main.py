from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_admin, routes_analyze, routes_backtest, routes_countries
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.analyze import HealthResponse

configure_logging()
settings = get_settings()

app = FastAPI(
    title="Geopolitical Conflict Impact Analyzer",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_analyze.router)
app.include_router(routes_backtest.router)
app.include_router(routes_admin.router)
app.include_router(routes_countries.router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # TODO: real DB / vector_db ping once scoring_service + rag_service exist
    return HealthResponse(status="ok", db="ok", vector_db="ok")
