"""
Retrieval layer for citing real historical case studies in narrative.

Design note: NOT using ChromaDB's default embedding model here. That
model downloads from huggingface.co on first use, which this
environment's network allowlist doesn't include - same constraint as
the other external data sources. More importantly, for a corpus this
small (a handful of case studies), matching on the actual conflict-
party ISO codes is a stronger and more precise relevance signal than
semantic embedding similarity would be anyway - "this case study is
literally about USA vs CHN" beats "this case study's prose is
semantically similar to USA vs CHN." A vector DB earns its keep once
the corpus is large enough that exact metadata matching stops being
sufficient - not the case yet.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import ConflictCase
from app.schemas.analyze import Citation


def find_relevant_case_studies(
    session: Session, party_a_iso: str, party_b_iso: str, top_k: int = 2
) -> list[ConflictCase]:
    """
    Ranks case studies by how many of their two conflict parties overlap
    with the query's two parties (2 = same conflict, 1 = shares one
    party, 0 = excluded entirely - not relevant enough to cite).
    """
    query_parties = {party_a_iso, party_b_iso}
    all_cases = session.execute(select(ConflictCase)).scalars().all()

    scored = []
    for case in all_cases:
        case_parties = {case.country_a_iso, case.country_b_iso}
        overlap = len(query_parties & case_parties)
        if overlap > 0:
            scored.append((overlap, case))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [case for _, case in scored[:top_k]]


def build_citation(case: ConflictCase) -> Citation:
    return Citation(
        source=case.name,
        url=f"internal://case_studies/{case.id}",
        snippet=case.documented_outcome[:200],
    )
