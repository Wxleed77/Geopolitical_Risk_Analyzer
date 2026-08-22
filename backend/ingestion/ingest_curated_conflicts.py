"""
Ingest curated conflict analyses - human/AI-researched, source-cited
rankings for major real-world conflict pairs. Distinct from
curate_case_studies.py (that's for RAG citations/backtest, historical
past events) - this is CURRENT verified analysis, the "verified" tier
that takes priority over the live deterministic scoring engine when a
matching conflict exists (see exposure_service / routes_analyze).

Idempotent: re-running does not create duplicate rows.
"""

import csv
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, init_db
from app.models.tables import Country, CuratedConflict, CuratedCountryImpact

logger = logging.getLogger(__name__)

REPO_ROOT = BACKEND_DIR.parent
COUNTRIES_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "countries_seed.csv"
CONFLICTS_SOURCE_PATH = REPO_ROOT / "data" / "curated" / "curated_conflicts_seed.csv"
IMPACTS_SOURCE_PATH = REPO_ROOT / "data" / "curated" / "curated_impacts_seed.csv"


def _read_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        lines = [line for line in f if not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def _upsert_countries(session: Session) -> int:
    inserted = 0
    for row in _read_rows(COUNTRIES_SOURCE_PATH):
        if session.get(Country, row["iso_code"]) is not None:
            continue
        session.add(Country(iso_code=row["iso_code"], name=row["name"], region=row["region"]))
        inserted += 1
    session.commit()
    return inserted


def _upsert_conflicts(session: Session, rows: list[dict]) -> dict:
    """Returns {title: conflict_id} for use by _upsert_impacts."""
    ids_by_title = {}
    for row in rows:
        existing = session.execute(
            select(CuratedConflict).where(CuratedConflict.title == row["title"])
        ).scalar_one_or_none()
        if existing is not None:
            ids_by_title[row["title"]] = existing.id
            continue
        conflict = CuratedConflict(
            title=row["title"],
            country_a_iso=row["country_a_iso"],
            country_b_iso=row["country_b_iso"],
            overview=row["overview"],
            last_verified=date.fromisoformat(row["last_verified"]),
        )
        session.add(conflict)
        session.flush()  # get conflict.id before commit
        ids_by_title[row["title"]] = conflict.id
    session.commit()
    return ids_by_title


def _upsert_impacts(session: Session, rows: list[dict], ids_by_title: dict) -> int:
    inserted = 0
    for row in rows:
        conflict_id = ids_by_title.get(row["conflict_title"])
        if conflict_id is None:
            logger.warning("No conflict found for title %s, skipping impact row", row["conflict_title"])
            continue
        existing = session.execute(
            select(CuratedCountryImpact).where(
                CuratedCountryImpact.curated_conflict_id == conflict_id,
                CuratedCountryImpact.country_iso == row["country_iso"],
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        session.add(
            CuratedCountryImpact(
                curated_conflict_id=conflict_id,
                country_iso=row["country_iso"],
                tier=row["tier"],
                rank_order=int(row["rank_order"]),
                reason=row["reason"],
                source_note=row["source_note"],
            )
        )
        inserted += 1
    session.commit()
    return inserted


def run() -> dict:
    init_db()
    session = SessionLocal()
    try:
        started = datetime.now(timezone.utc)
        countries_inserted = _upsert_countries(session)
        conflict_rows = _read_rows(CONFLICTS_SOURCE_PATH)
        ids_by_title = _upsert_conflicts(session, conflict_rows)
        impact_rows = _read_rows(IMPACTS_SOURCE_PATH)
        impacts_inserted = _upsert_impacts(session, impact_rows, ids_by_title)
        finished = datetime.now(timezone.utc)

        summary = {
            "source": "curated_conflicts_seed_v1 (human-researched, source-cited)",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "countries_inserted": countries_inserted,
            "conflicts_processed": len(ids_by_title),
            "impacts_inserted": impacts_inserted,
        }
        logger.info("Curated conflict ingestion complete: %s", summary)
        return summary
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
