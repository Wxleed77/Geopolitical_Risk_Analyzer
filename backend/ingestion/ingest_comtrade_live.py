"""
Live fetch from UN Comtrade Plus API - replaces the trade_seed.csv
approach with real bilateral trade figures.

UNTESTED FROM THIS ENVIRONMENT: comtradeapi.un.org is not in this
sandbox's network allowlist, so this has only been checked against
current API documentation, not run against the live endpoint. Test on
a machine with normal internet access.

Setup:
1. Register free at https://comtradeplus.un.org/
2. Get your subscription key from the API Management section
3. Set COMTRADE_API_KEY in backend/.env

API docs: https://uncomtrade.org/docs/
Endpoint used: GET https://comtradeapi.un.org/data/v1/get/C/A/HS
  - C = Commodities, A = Annual, HS = Harmonized System classification
  - cmdCode=TOTAL for total trade (not broken down by product)
  - Free tier is rate-limited (check current limits in your account -
    they've changed over time) - this script sleeps between calls to
    be conservative; tune SLEEP_SECONDS if you hit rate limit errors.

Known limitation: Iran's Comtrade data is often sparse/estimated due
to sanctions-related reporting gaps - expect missing rows even with a
valid live API key, not just in the old seed data.
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
from app.models.tables import TradeFlow
from ingestion.country_codes import ISO3_TO_M49, WORLD_PARTNER_CODE

logger = logging.getLogger(__name__)

API_URL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
YEAR = 2023
SLEEP_SECONDS = 4  # be conservative on the free tier

# Which reporter -> partner pairs to fetch. Add more pairs as needed -
# each is one API call. WORLD_PARTNER_CODE gets the reporter's total
# trade (the denominator trade_score needs).
def build_query_pairs() -> list[tuple[str, str | None]]:
    reporters = ["DEU", "JPN", "KOR", "IND", "TUR", "CHN"]
    conflict_parties = ["USA", "IRN", "CHN", "RUS"]
    pairs = []
    for reporter in reporters:
        pairs.append((reporter, None))  # world total
        for partner in conflict_parties:
            if partner != reporter:
                pairs.append((reporter, partner))
    return pairs


def fetch_trade_value(session_http: requests.Session, api_key: str, reporter_iso: str, partner_iso: str | None) -> float | None:
    reporter_m49 = ISO3_TO_M49.get(reporter_iso)
    if reporter_m49 is None:
        logger.warning("No M49 code for reporter %s, skipping", reporter_iso)
        return None
    partner_m49 = WORLD_PARTNER_CODE if partner_iso is None else ISO3_TO_M49.get(partner_iso)
    if partner_m49 is None:
        logger.warning("No M49 code for partner %s, skipping", partner_iso)
        return None

    params = {
        "reporterCode": reporter_m49,
        "partnerCode": partner_m49,
        "period": YEAR,
        "cmdCode": "TOTAL",
        "flowCode": "M",  # imports - flip to "X" for exports if you want that direction too
        # These three force Comtrade to return ONE aggregate row instead
        # of breaking the same trade down across customs procedure /
        # transport mode / secondary-partner dimensions. Omitting them is
        # what caused DEU->WLD to return 2,659 rows earlier - summing
        # those was wrong (produced $11.9T, ~4-8x too high). This is the
        # real fix, but still UNTESTED from this sandbox - confirm the
        # DEU->WLD number lands near $1.5-3T (its real order of magnitude)
        # after this change, not the $1M or $11.9T we saw before.
        "customsCode": "C00",
        "motCode": "0",
        "partner2Code": "0",
    }
    headers = {"Ocp-Apim-Subscription-Key": api_key}

    resp = session_http.get(API_URL, params=params, headers=headers, timeout=30)
    if resp.status_code == 429:
        logger.warning("Rate limited on %s -> %s, waiting 15s and retrying once", reporter_iso, partner_iso or "WLD")
        time.sleep(15)
        resp = session_http.get(API_URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if not data:
        return None
    if len(data) > 1:
        # If this still fires after the filter above, something else is
        # fragmenting the result - print the first raw row so you can see
        # which field is actually varying, then we can filter on that too.
        logger.warning(
            "%s -> %s STILL returned %d rows after aggregate filters - "
            "inspect this raw row to find what's varying: %s",
            reporter_iso, partner_iso or "WLD", len(data), data[0],
        )
    return sum(float(row.get("primaryValue", 0)) for row in data)


def _upsert_trade_flow(db: Session, reporter_iso: str, partner_iso: str, value: float) -> bool:
    # Match on (reporter, partner, year) ONLY - not flow_type. Old seed
    # rows used flow_type="total" while this script writes "import"; if
    # we matched on flow_type too, live data would insert ALONGSIDE old
    # seed rows instead of replacing them, causing duplicate rows and a
    # MultipleResultsFound crash downstream. Delete-then-insert instead,
    # so live data always cleanly wins over stale seed data for this key.
    stmt = select(TradeFlow).where(
        TradeFlow.reporter_iso == reporter_iso,
        TradeFlow.partner_iso == partner_iso,
        TradeFlow.hs_sector_code == "TOTAL",
        TradeFlow.year == YEAR,
    )
    existing_rows = db.execute(stmt).scalars().all()
    was_new = len(existing_rows) == 0
    for row in existing_rows:
        db.delete(row)
    db.add(
        TradeFlow(
            reporter_iso=reporter_iso,
            partner_iso=partner_iso,
            hs_sector_code="TOTAL",
            year=YEAR,
            trade_value_usd=value,
            flow_type="import",
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
        for reporter, partner in build_query_pairs():
            partner_label = partner or "WLD"
            try:
                value = fetch_trade_value(http, settings.comtrade_api_key, reporter, partner)
                if value is None:
                    logger.warning("No data returned for %s -> %s", reporter, partner_label)
                    continue
                is_new = _upsert_trade_flow(db, reporter, partner_label, value)
                if is_new:
                    inserted += 1
                else:
                    updated += 1
                logger.info("%s -> %s: $%s", reporter, partner_label, f"{value:,.0f}")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed %s -> %s: %s", reporter, partner_label, exc)
                failed.append(f"{reporter}->{partner_label}")
            time.sleep(SLEEP_SECONDS)

        summary = {
            "source": "UN Comtrade Plus API (live)",
            "year": YEAR,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
        }
        logger.info("Live Comtrade fetch complete: %s", summary)
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
