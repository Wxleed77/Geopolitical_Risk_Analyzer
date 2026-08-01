import csv
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from app.core.db import SessionLocal, init_db
from app.models.tables import ConflictCase, HistoricalShockImpact

logger = logging.getLogger(__name__)
SOURCE_PATH = BACKEND_DIR.parent / "data" / "case_studies" / "shock_impacts_seed.csv"


def run() -> dict:
    init_db()
    session = SessionLocal()
    inserted = 0
    try:
        with open(SOURCE_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                case = session.execute(
                    select(ConflictCase).where(ConflictCase.name == row["case_name"])
                ).scalar_one_or_none()
                if case is None:
                    logger.warning("Case not found, skipping: %s", row["case_name"])
                    continue
                exists = session.execute(
                    select(HistoricalShockImpact).where(
                        HistoricalShockImpact.case_id == case.id,
                        HistoricalShockImpact.country_iso == row["country_iso"],
                        HistoricalShockImpact.indicator == row["indicator"],
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    continue
                session.add(
                    HistoricalShockImpact(
                        case_id=case.id,
                        country_iso=row["country_iso"],
                        indicator=row["indicator"],
                        change_pct=float(row["change_pct"]),
                        timeframe=row["timeframe"],
                        source_note=row["source_note"],
                    )
                )
                inserted += 1
        session.commit()
        summary = {"shock_impacts_inserted": inserted}
        logger.info("Shock impact ingestion complete: %s", summary)
        return summary
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
