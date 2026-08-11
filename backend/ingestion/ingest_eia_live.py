"""
Live fetch from EIA's International Energy Data API v2.

UNTESTED FROM THIS ENVIRONMENT (eia.gov not reachable from this
sandbox) - but the facet NAME below (countryRegionId) is confirmed
correct, verified against a real EIA data-browser URL:

  https://www.eia.gov/opendata/browser/international?data=value&facets=
  activityId%3BproductId%3BcountryRegionId%3Bunit&activityId=2%3B&
  productId=79%3B&countryRegionId=DMA%3B&unit=TBPD%3B&frequency=annual

That confirms the request shape and facet names, but NOT the specific
activityId/productId values you need (that example is for a different
series). Find your own in under a minute:

1. Register free at https://www.eia.gov/opendata/register.php
2. Open https://www.eia.gov/opendata/browser/international in your
   browser (log in with your key)
3. Filter to Activity = "Imports" and Product = "Crude oil" (or
   whichever energy type you want), and your country of interest
4. EIA's browser UI has an "API queries" / "View API calls" panel
   that shows you the EXACT working URL for whatever you've filtered
   to - copy the activityId and productId numbers straight from there
   into FACET_ACTIVITY_IMPORTS / FACET_PRODUCT_CRUDE_OIL below
5. Set EIA_API_KEY in backend/.env

Also worth knowing: EIA is a US government agency, so its
international dataset is strongest for petroleum/gas (things the US
itself tracks closely) and much thinner for bilateral energy flows
that don't involve the US at all (e.g. Germany's imports from Russia)
- for those, IEA's data is better, but IEA's API is partially paywalled.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests

from app.core.config import get_settings
from app.core.db import init_db

logger = logging.getLogger(__name__)

BASE_URL = "https://api.eia.gov/v2/international/data/"
YEAR = 2023

# FACET_PRODUCT_CRUDE_OIL confirmed via the EIA data browser: productId
# 57 = "Crude oil including lease condensate". FACET_ACTIVITY_IMPORTS
# is still a placeholder - add an ACTIVITYID facet in the browser,
# select "Imports" (not "Production"), and read the real number from
# the X-Params panel before trusting this.
FACET_ACTIVITY_IMPORTS = "3"  # still placeholder - look up "Imports" activityId in the EIA browser
FACET_PRODUCT_CRUDE_OIL = "57"  # confirmed: crude oil including lease condensate


def fetch_energy_import_value(api_key: str, country_iso: str) -> float | None:
    params = {
        "api_key": api_key,
        "frequency": "annual",
        "data[0]": "value",
        "facets[activityId][]": FACET_ACTIVITY_IMPORTS,
        "facets[productId][]": FACET_PRODUCT_CRUDE_OIL,
        "facets[countryRegionId][]": country_iso,  # confirmed facet name; country code format not yet verified against ISO3
        "start": str(YEAR),
        "end": str(YEAR),
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json().get("response", {}).get("data", [])
    if not rows:
        return None
    if len(rows) > 1:
        logger.warning(
            "%s returned %d rows instead of 1 - inspect first raw row: %s",
            country_iso, len(rows), rows[0],
        )
    return float(rows[0].get("value", 0))


def run() -> dict:
    settings = get_settings()
    if not settings.eia_api_key:
        raise RuntimeError("EIA_API_KEY is not set. Add it to backend/.env (see .env.example).")

    """if FACET_ACTIVITY_IMPORTS == "3":
        logger.warning(
            "FACET_ACTIVITY_IMPORTS still looks like an unverified placeholder "
            "(productId is confirmed) - see this file's docstring for how to "
            "find the real 'Imports' activityId before trusting this run's output."
        )"""

    init_db()
    fetched = 0
    failed = []
    for country_iso in ["DEU", "JPN", "KOR", "IND"]:
        try:
            value = fetch_energy_import_value(settings.eia_api_key, country_iso)
            if value is None:
                logger.warning("No data returned for %s", country_iso)
                continue
            logger.info("%s crude oil imports: %s", country_iso, value)
            fetched += 1
            # NOTE: not writing to EnergyDependency here yet - the raw
            # value from EIA is a volume/quantity, not the import_share_pct
            # our schema expects. You'd need each country's TOTAL imports
            # too, to compute a share - same two-query pattern as
            # ingest_comtrade_live.py (bilateral value / world total).
            # Left as a follow-up once the facet values above are confirmed.
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed for %s: %s", country_iso, exc)
            failed.append(country_iso)

    summary = {
        "source": "EIA International API v2 (live)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fetched": fetched,
        "failed": failed,
        "note": "Confirm FACET_ACTIVITY_IMPORTS/FACET_PRODUCT_CRUDE_OIL are real values, not placeholders.",
    }
    logger.info("Live EIA fetch complete: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
