"""
Live fetch of bilateral ENERGY trade from UN Comtrade - replaces the
EIA-based approach entirely. EIA's international dataset is country-
level aggregate only (total imports from everywhere), not bilateral
partner-to-partner data, so it can't answer "how much does Germany
import specifically FROM Russia" - which is what energy_score needs.
Comtrade can, using the same reporter/partner/World pattern already
proven working in ingest_comtrade_live.py, just with energy-specific
commodity codes instead of cmdCode=TOTAL:
  - 2709 = crude petroleum oils
  - 2711 = natural gas and other gaseous hydrocarbons

import_share_pct is computed the same way trade_score's denominator
works: bilateral energy value / that reporter's total-world energy
import value, times 100 - a real, defensible bilateral share, not a
raw untranslated volume like the EIA attempt would have produced.

UNTESTED FROM THIS ENVIRONMENT (comtradeapi.un.org not reachable from
this sandbox) - but reuses the exact request shape already CONFIRMED
working in ingest_comtrade_live.py (same API, same auth, same
aggregate-row filters), just a different cmdCode. Should need no
further debugging - if it does, the issue is almost certainly the
same kind of thing already solved in that script.

Runtime note: 2 energy types x 5 reporters x 5 partners (4 conflict
parties + WLD) = 50 API calls. At ~4s between calls plus occasional
429 retries, expect this to take several minutes - that's normal, not
a hang.
"""

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal, init_db
from app.models.tables import EnergyDependency
from ingestion.country_codes import ISO3_TO_M49, WORLD_PARTNER_CODE

logger = logging.getLogger(__name__)

API_URL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
YEAR = 2023
SLEEP_SECONDS = 4

ENERGY_COMMODITIES = {
    "crude_oil": "2709",
    "natural_gas": "2711",
}

REPORTERS = ["DEU", "JPN", "KOR", "TUR", "CHN"]
CONFLICT_PARTIES = ["USA", "IRN", "CHN", "RUS"]


def fetch_trade_value(session_http: requests.Session, api_key: str, cmd_code: str, reporter_iso: str, partner_iso: str | None) -> float | None:
    reporter_m49 = ISO3_TO_M49.get(reporter_iso)
    partner_m49 = WORLD_PARTNER_CODE if partner_iso is None else ISO3_TO_M49.get(partner_iso)
    if reporter_m49 is None or partner_m49 is None:
        return None

    params = {
        "reporterCode": reporter_m49,
        "partnerCode": partner_m49,
        "period": YEAR,
        "cmdCode": cmd_code,
        "flowCode": "M",
        "customsCode": "C00",
        "motCode": "0",
        "partner2Code": "0",
    }
    headers = {"Ocp-Apim-Subscription-Key": api_key}

    resp = session_http.get(API_URL, params=params, headers=headers, timeout=30)
    if resp.status_code == 429:
        logger.warning("Rate limited on %s/%s -> %s, waiting 15s and retrying once", cmd_code, reporter_iso, partner_iso or "WLD")
        time.sleep(15)
        resp = session_http.get(API_URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if not data:
        return None
    if len(data) > 1:
        logger.warning("%s/%s -> %s returned %d rows - summing", cmd_code, reporter_iso, partner_iso or "WLD", len(data))
    return sum(float(row.get("primaryValue", 0)) for row in data)


def _upsert_energy_dependency(db: Session, country_iso: str, source_iso: str, energy_type: str, share_pct: float) -> bool:
    stmt = select(EnergyDependency).where(
        EnergyDependency.country_iso == country_iso,
        EnergyDependency.source_country_iso == source_iso,
        EnergyDependency.year == YEAR,
        EnergyDependency.energy_type == energy_type,
    )
    existing_rows = db.execute(stmt).scalars().all()
    was_new = len(existing_rows) == 0
    for row in existing_rows:
        db.delete(row)
    db.add(
        EnergyDependency(
            country_iso=country_iso,
            source_country_iso=source_iso,
            year=YEAR,
            import_share_pct=share_pct,
            energy_type=energy_type,
        )
    )
    db.commit()
    return was_new


def run() -> dict:
    settings = get_settings()
    if not settings.comtrade_api_key:
        raise RuntimeError("COMTRADE_API_KEY is not set. Add it to backend/.env (see .env.example).")

    init_db()
    db = SessionLocal()
    http = requests.Session()
    inserted = 0
    updated = 0
    failed = []

    try:
        for energy_type, cmd_code in ENERGY_COMMODITIES.items():
            for reporter in REPORTERS:
                world_total = fetch_trade_value(http, settings.comtrade_api_key, cmd_code, reporter, None)
                time.sleep(SLEEP_SECONDS)
                if not world_total:
                    logger.warning("No %s world total for %s, skipping its partners", energy_type, reporter)
                    continue
                logger.info("%s %s -> WLD: $%s", reporter, energy_type, f"{world_total:,.0f}")

                for partner in CONFLICT_PARTIES:
                    if partner == reporter:
                        continue
                    try:
                        bilateral = fetch_trade_value(http, settings.comtrade_api_key, cmd_code, reporter, partner)
                        if bilateral is None:
                            logger.warning("No %s data for %s -> %s", energy_type, reporter, partner)
                            time.sleep(SLEEP_SECONDS)
                            continue
                        share_pct = min((bilateral / world_total) * 100, 100.0)
                        is_new = _upsert_energy_dependency(db, reporter, partner, energy_type, share_pct)
                        inserted += 1 if is_new else 0
                        updated += 0 if is_new else 1
                        logger.info("%s %s from %s: %.2f%%", reporter, energy_type, partner, share_pct)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Failed %s %s -> %s: %s", energy_type, reporter, partner, exc)
                        failed.append(f"{energy_type}:{reporter}->{partner}")
                    time.sleep(SLEEP_SECONDS)

        summary = {
            "source": "UN Comtrade Plus API (live, energy commodities)",
            "year": YEAR,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
        }
        logger.info("Live energy fetch complete: %s", summary)
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
