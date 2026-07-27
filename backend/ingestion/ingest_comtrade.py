"""
Ingest bilateral trade data into the normalized `trade_flow` table.

v1 source note (same honesty caveat as ingest_alliances.py):
Live UN Comtrade API isn't reachable from this environment (network
allowlist doesn't include comtrade.un.org). Source file is a small,
hand-written CSV of approximate/illustrative trade figures - good
enough to validate the ingestion -> scoring pipeline end-to-end, but
NOT precise enough for real analysis. Swapping in a live Comtrade
pull later only changes SOURCE_PATH / adds a fetch step upstream of
_upsert_trade_flows - the upsert logic itself doesn't change.

"WLD" is seeded as a sentinel Country row (not a real country) so
FK constraints hold - it follows UN Comtrade's own convention for a
reporter's total trade with the world, used as the trade_score
denominator.

Idempotent: re-running does not create duplicate rows (unique on
reporter_iso, partner_iso, hs_sector_code, year, flow_type).
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
from app.models.tables import Country, TradeFlow

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "data" / "raw" / "trade_seed.csv"


def _read_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        lines = [line for line in f if not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def _ensure_world_sentinel(session: Session) -> None:
    if session.get(Country, "WLD") is None:
        session.add(Country(iso_code="WLD", name="World (aggregate)", region="Global"))
        session.commit()


def _upsert_trade_flows(session: Session, rows: list[dict]) -> int:
    inserted = 0
    for row in rows:
        stmt = select(TradeFlow).where(
            TradeFlow.reporter_iso == row["reporter_iso"],
            TradeFlow.partner_iso == row["partner_iso"],
            TradeFlow.hs_sector_code == row["hs_sector_code"],
            TradeFlow.year == int(row["year"]),
            TradeFlow.flow_type == row["flow_type"],
        )
        if session.execute(stmt).scalar_one_or_none() is not None:
            continue
        session.add(
            TradeFlow(
                reporter_iso=row["reporter_iso"],
                partner_iso=row["partner_iso"],
                hs_sector_code=row["hs_sector_code"],
                year=int(row["year"]),
                trade_value_usd=float(row["trade_value_usd"]),
                flow_type=row["flow_type"],
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
        _ensure_world_sentinel(session)
        rows = _read_rows(SOURCE_PATH)
        trade_flows_inserted = _upsert_trade_flows(session, rows)
        finished = datetime.now(timezone.utc)

        summary = {
            "source": "trade_seed_v1 (illustrative figures, NOT authoritative)",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "trade_flows_inserted": trade_flows_inserted,
        }
        logger.info("Trade ingestion complete: %s", summary)
        return summary
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
