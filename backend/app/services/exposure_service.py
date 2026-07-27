"""
Orchestration layer between the DB and the pure scoring_service functions.

Deliberately thin: this module's only job is "fetch rows -> build the
dataclasses scoring_service expects -> call the pure functions -> shape
the result for the API." All actual scoring math lives in
scoring_service.py and stays unit-testable without a DB.
"""

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Alliance, Country, EnergyDependency, TradeFlow
from app.schemas.analyze import RankedCountry, SectorBreakdown
from app.services.scoring_service import (
    EnergyExposureInput,
    TradeExposureInput,
    alliance_score,
    composite_score,
    energy_score,
    trade_score,
)

# Matches the year our seed data uses. TODO: make this dynamic (most
# recent year with data) once ingestion pulls multiple years.
DATA_YEAR = 2023

# Not a real country - excluded from candidate ranking.
NON_COUNTRY_ISOS = {"WLD"}


def _build_alliance_graph(session: Session) -> nx.Graph:
    graph = nx.Graph()
    for row in session.execute(select(Alliance)).scalars().all():
        graph.add_edge(row.country_a_iso, row.country_b_iso)
    return graph


def _get_trade_value(session: Session, reporter: str, partner: str) -> float | None:
    stmt = select(TradeFlow).where(
        TradeFlow.reporter_iso == reporter,
        TradeFlow.partner_iso == partner,
        TradeFlow.year == DATA_YEAR,
    )
    row = session.execute(stmt).scalar_one_or_none()
    return row.trade_value_usd if row else None


def _get_energy_share(session: Session, country: str, source: str) -> float | None:
    stmt = select(EnergyDependency).where(
        EnergyDependency.country_iso == country,
        EnergyDependency.source_country_iso == source,
        EnergyDependency.year == DATA_YEAR,
    )
    row = session.execute(stmt).scalar_one_or_none()
    return row.import_share_pct if row else None


def rank_exposure(session: Session, party_a_iso: str, party_b_iso: str) -> list[RankedCountry]:
    """
    Score every known country's exposure to a conflict between
    party_a_iso and party_b_iso, ranked descending by composite score.
    Countries with no data on any of the three dimensions are excluded
    (nothing meaningful to rank), rather than shown with a misleading 0.
    """
    graph = _build_alliance_graph(session)
    all_countries = session.execute(select(Country)).scalars().all()

    candidates = [
        c for c in all_countries
        if c.iso_code not in NON_COUNTRY_ISOS and c.iso_code not in (party_a_iso, party_b_iso)
    ]

    results: list[RankedCountry] = []
    for country in candidates:
        trade_inp = TradeExposureInput(
            country_iso=country.iso_code,
            trade_value_with_a_usd=_get_trade_value(session, country.iso_code, party_a_iso),
            trade_value_with_b_usd=_get_trade_value(session, country.iso_code, party_b_iso),
            country_total_trade_usd=_get_trade_value(session, country.iso_code, "WLD"),
        )
        energy_inp = EnergyExposureInput(
            country_iso=country.iso_code,
            import_share_from_a_pct=_get_energy_share(session, country.iso_code, party_a_iso),
            import_share_from_b_pct=_get_energy_share(session, country.iso_code, party_b_iso),
        )

        t = trade_score(trade_inp)
        e = energy_score(energy_inp)
        a = alliance_score(graph, country.iso_code, party_a_iso, party_b_iso)
        composite = composite_score(t, e, a)

        if composite.insufficient_data:
            continue  # nothing meaningful to rank this country on

        results.append(
            RankedCountry(
                iso_code=country.iso_code,
                name=country.name,
                exposure_score=composite.value,
                breakdown=SectorBreakdown(
                    trade_score=t.value if t.value is not None else 0.0,
                    energy_score=e.value if e.value is not None else 0.0,
                    alliance_score=a.value if a.value is not None else 0.0,
                ),
            )
        )

    results.sort(key=lambda r: r.exposure_score, reverse=True)
    return results
