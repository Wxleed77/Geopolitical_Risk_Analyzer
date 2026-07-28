"""
Ingest historical conflict case studies - real, well-documented events
(not synthetic). Feeds two things: the /backtest endpoints (compare our
scoring engine's output against documented real-world outcomes) and the
RAG layer (rag_service.py cites these for narrative context).

Also upserts from countries_seed.csv (shared with the other ingestion
scripts) so any newly-referenced country (e.g. UKR) exists before FK
insert - safe to run in any order.

Idempotent: re-running does not create duplicate rows (unique on `name`).
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
from app.models.tables import ConflictCase, Country

logger = logging.getLogger(__name__)

REPO_ROOT = BACKEND_DIR.parent
COUNTRIES_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "countries_seed.csv"
SOURCE_PATH = REPO_ROOT / "data" / "case_studies" / "case_studies_seed.csv"


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


def _upsert_case_studies(session: Session, rows: list[dict]) -> int:
    inserted = 0
    for row in rows:
        stmt = select(ConflictCase).where(ConflictCase.name == row["name"])
        if session.execute(stmt).scalar_one_or_none() is not None:
            continue
        session.add(
            ConflictCase(
                name=row["name"],
                country_a_iso=row["country_a_iso"],
                country_b_iso=row["country_b_iso"],
                start_date=date.fromisoformat(row["start_date"]),
                description=row["description"],
                documented_outcome=row["documented_outcome"],
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
        rows = _read_rows(SOURCE_PATH)
        cases_inserted = _upsert_case_studies(session, rows)
        finished = datetime.now(timezone.utc)

        summary = {
            "source": "case_studies_seed_v1 (real, documented historical events)",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "countries_inserted": countries_inserted,
            "cases_inserted": cases_inserted,
        }
        logger.info("Case study ingestion complete: %s", summary)
        return summary
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
