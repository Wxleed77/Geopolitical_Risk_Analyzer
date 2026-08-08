"""
Live fetch from EIA's International Energy Data API v2.

UNTESTED FROM THIS ENVIRONMENT (eia.gov not reachable from this
sandbox), AND lower-confidence than ingest_comtrade_live.py: the
general v2 request shape below (api_key, frequency, data[], facets,
start/end, sort) is correct and documented, but the exact facet
parameter names for filtering by reporting country vs partner country
under the "international" route were NOT independently verified here -
EIA's international dataset structure isn't as thoroughly documented
in easily-searchable form as Comtrade's. Before relying on this:

1. Register free at https://www.eia.gov/opendata/register.php
2. Browse https://www.eia.gov/opendata/browser/international in your
   browser (requires the free key) to find the exact route path and
   facet names for "petroleum imports by country" or "natural gas
   imports by country" - the FACET_* constants below are best-guess
   placeholders, confirm/fix them against what the browser shows.
3. Set EIA_API_KEY in backend/.env

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
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal, init_db
from app.models.tables import EnergyDependency

logger = logging.getLogger(__name__)

BASE_URL = "https://api.eia.gov/v2/international/data/"
YEAR = 2023

# BEST-GUESS PLACEHOLDER - verify against the EIA data browser (see
# docstring above) before trusting this. EIA international facets are
# typically something like activityId (e.g. imports), productId (e.g.
# crude oil), countryId (ISO-ish EIA country codes, NOT always plain
# ISO3 - some differ).
FACET_ACTIVITY_IMPORTS = "3"  # placeholder guess for "imports" activityId
FACET_PRODUCT_CRUDE_OIL = "53"  # placeholder guess for crude oil productId


def fetch_energy_import_value(api_key: str, country_iso: str) -> float | None:
    """
    PLACEHOLDER IMPLEMENTATION - the params dict below needs to be
    checked/corrected against the EIA data browser for your specific
    query before this will return real data. Written to show the
    request shape, not guaranteed correct facet values.
    """
    params = {
        "api_key": api_key,
        "frequency": "annual",
        "data[0]": "value",
        "facets[activityId][]": FACET_ACTIVITY_IMPORTS,
        "facets[productId][]": FACET_PRODUCT_CRUDE_OIL,
        "facets[countryId][]": country_iso,  # may need EIA-specific code, not ISO3
        "start": str(YEAR),
        "end": str(YEAR),
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json().get("response", {}).get("data", [])
    if not rows:
        return None
    return float(rows[0].get("value", 0))


def run() -> dict:
    settings = get_settings()
    if not settings.eia_api_key:
        raise RuntimeError("EIA_API_KEY is not set. Add it to backend/.env (see .env.example).")

    logger.warning(
        "ingest_eia_live.py uses placeholder facet values - verify against "
        "https://www.eia.gov/opendata/browser/international before trusting output."
    )

    init_db()
    db = SessionLocal()
    fetched = 0
    failed = []
    try:
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
                # our schema expects. You'd need total imports too, to
                # compute a share - left as a follow-up once the facet
                # values above are confirmed correct.
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed for %s: %s", country_iso, exc)
                failed.append(country_iso)

        summary = {
            "source": "EIA International API v2 (live, placeholder facets)",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "fetched": fetched,
            "failed": failed,
            "note": "Facet values unverified - see docstring before trusting this output.",
        }
        logger.info("Live EIA fetch complete: %s", summary)
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
