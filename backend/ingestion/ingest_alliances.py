"""
Ingest alliance/treaty data into the normalized `alliance` table.

v1 source note (documented honestly, per blueprint 6.1/6.2):
The live ATOP dataset (atopdata.org) requires network access this
environment doesn't have allowlisted. Source file is a small,
hand-curated CSV of real, publicly verifiable treaties (NATO, ANZUS,
CSTO, etc. - actual historical treaties, not synthetic data) at
data/raw/alliances_seed.csv. Swapping in a live ATOP download later
only requires changing SOURCE_PATH / adding a fetch step - the
normalize/upsert logic below is unchanged either way.

Idempotent: re-running does not create duplicate rows (unique
constraint on country_a_iso, country_b_iso, treaty_name).
"""

import csv
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, init_db
from app.models.tables import Alliance, Country

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
COUNTRIES_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "countries_seed.csv"
ALLIANCES_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "alliances_seed.csv"


def _upsert_countries(session: Session) -> int:
    inserted = 0
    with open(COUNTRIES_SOURCE_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing = session.get(Country, row["iso_code"])
            if existing is not None:
                continue
            session.add(Country(iso_code=row["iso_code"], name=row["name"], region=row["region"]))
            inserted += 1
    session.commit()
    return inserted


def _upsert_alliances(session: Session) -> int:
    inserted = 0
    with open(ALLIANCES_SOURCE_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stmt = select(Alliance).where(
                Alliance.country_a_iso == row["country_a_iso"],
                Alliance.country_b_iso == row["country_b_iso"],
                Alliance.treaty_name == row["treaty_name"],
            )
            if session.execute(stmt).scalar_one_or_none() is not None:
                continue
            session.add(
                Alliance(
                    country_a_iso=row["country_a_iso"],
                    country_b_iso=row["country_b_iso"],
                    treaty_name=row["treaty_name"],
                    year_signed=int(row["year_signed"]),
                    alliance_type=row["alliance_type"],
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
        alliances_inserted = _upsert_alliances(session)
        finished = datetime.now(timezone.utc)

        summary = {
            "source": "alliances_seed_v1 (hand-curated, real treaties)",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "countries_inserted": countries_inserted,
            "alliances_inserted": alliances_inserted,
        }
        logger.info("Alliance ingestion complete: %s", summary)
        return summary
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
