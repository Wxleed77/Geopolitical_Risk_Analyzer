"""
Looks up and formats curated (human-researched, verified) conflict
analyses - the "verified" tier that takes priority over the live
deterministic scoring engine when a matching conflict exists.

Tier-to-score mapping below is a DISPLAY anchor only, not a computed
value - curated analysis is deliberately qualitative (high/medium/low
+ real written reasoning), since pretending a precise decimal score
for informed research judgment would be false precision. The anchors
just let the existing gauge/sort UI render something sensible.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Country, CuratedConflict, CuratedCountryImpact
from app.schemas.analyze import Citation, NarrativeSection, RankedCountry, SectorBreakdown

TIER_SCORE_ANCHOR = {"high": 85.0, "medium": 50.0, "low": 15.0}


def find_curated_conflict(session: Session, party_a_iso: str, party_b_iso: str) -> CuratedConflict | None:
    """Order-independent match - USA/CHN and CHN/USA both hit the same row."""
    stmt = select(CuratedConflict).where(
        ((CuratedConflict.country_a_iso == party_a_iso) & (CuratedConflict.country_b_iso == party_b_iso))
        | ((CuratedConflict.country_a_iso == party_b_iso) & (CuratedConflict.country_b_iso == party_a_iso))
    )
    return session.execute(stmt).scalar_one_or_none()


def build_curated_response(session: Session, conflict: CuratedConflict) -> dict:
    impacts = session.execute(
        select(CuratedCountryImpact)
        .where(CuratedCountryImpact.curated_conflict_id == conflict.id)
        .order_by(CuratedCountryImpact.rank_order)
    ).scalars().all()

    country_names = {
        c.iso_code: c.name
        for c in session.execute(
            select(Country).where(Country.iso_code.in_([i.country_iso for i in impacts]))
        ).scalars().all()
    }

    ranked_countries = [
        RankedCountry(
            iso_code=impact.country_iso,
            name=country_names.get(impact.country_iso, impact.country_iso),
            exposure_score=TIER_SCORE_ANCHOR[impact.tier],
            breakdown=SectorBreakdown(trade_score=0.0, energy_score=0.0, alliance_score=0.0),
        )
        for impact in impacts
    ]

    narrative_sections = [
        NarrativeSection(
            heading=f"{country_names.get(impact.country_iso, impact.country_iso)} ({impact.country_iso})",
            text=impact.reason,
            tag="curated-verified",
        )
        for impact in impacts
    ]

    overview_section = NarrativeSection(
        heading=conflict.title, text=conflict.overview, tag="curated-verified"
    )

    citations = [
        Citation(source=f"{conflict.title} - {impact.country_iso}", url="internal://curated", snippet=impact.source_note)
        for impact in impacts
    ]

    return {
        "ranked_countries": ranked_countries,
        "narrative_sections": [overview_section] + narrative_sections,
        "citations": citations,
        "last_verified": conflict.last_verified.isoformat(),
    }
