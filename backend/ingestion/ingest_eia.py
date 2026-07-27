"""
Ingest energy dependency data into the normalized `energy_dependency` table.

v1 source note (same caveat as ingest_comtrade.py / ingest_alliances.py):
Live EIA API isn't reachable from this environment (network allowlist
doesn't include eia.gov). Source file is a small, hand-written CSV of
approximate/illustrative import-share figures - captures a real,
well-documented trend (India's post-2022 shift to Russian crude) but
exact percentages are NOT precise enough for real analysis. Swapping in
a live EIA pull later only changes SOURCE_PATH / adds a fetch step -
the upsert logic itself doesn't change.

Also upserts from countries_seed.csv (shared with ingest_alliances.py)
so any newly-referenced country (e.g. IND) exists before FK insert -
safe to run in any order relative to the other ingestion scripts.

Idempotent: re-running does not create duplicate rows (unique on
country_iso, source_country_iso, year, energy_type).
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
from app.models.tables import Country, EnergyDependency

logger = logging.getLogger(__name__)

REPO_ROOT = BACKEND_DIR.parent
COUNTRIES_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "countries_seed.csv"
SOURCE_PATH = REPO_ROOT / "data" / "raw" / "energy_seed.csv"


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


def _upsert_energy_rows(session: Session, rows: list[dict]) -> int:
    inserted = 0
    for row in rows:
        stmt = select(EnergyDependency).where(
            EnergyDependency.country_iso == row["country_iso"],
            EnergyDependency.source_country_iso == row["source_country_iso"],
            EnergyDependency.year == int(row["year"]),
            EnergyDependency.energy_type == row["energy_type"],
        )
        if session.execute(stmt).scalar_one_or_none() is not None:
            continue
        session.add(
            EnergyDependency(
                country_iso=row["country_iso"],
                source_country_iso=row["source_country_iso"],
                year=int(row["year"]),
                import_share_pct=float(row["import_share_pct"]),
                energy_type=row["energy_type"],
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
        energy_rows_inserted = _upsert_energy_rows(session, rows)
        finished = datetime.now(timezone.utc)

        summary = {
            "source": "energy_seed_v1 (illustrative figures, NOT authoritative)",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "countries_inserted": countries_inserted,
            "energy_rows_inserted": energy_rows_inserted,
        }
        logger.info("Energy ingestion complete: %s", summary)
        return summary
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
