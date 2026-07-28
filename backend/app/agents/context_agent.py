"""
Context agent - turns a free-text conflict description into the two
ISO-3166 alpha-3 country codes /analyze needs.

This is intentionally the ONLY agent allowed to guess/infer rather than
strictly ground everything in given data - extraction from ambiguous
natural language is its whole job. The critic agent's "don't invent
beyond the data" rule doesn't apply here; what DOES apply is validating
the extraction actually produced two distinct, real ISO codes before
anything downstream trusts it (done by the caller, not this module -
this module's only job is extraction).
"""

import json
import logging
import re

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You extract the two countries involved in a described conflict or "
    "tension. Respond with ONLY a JSON object, no other text, no markdown "
    "fences, in exactly this shape: "
    '{"country_a": "XXX", "country_b": "YYY"} '
    "where XXX and YYY are ISO 3166-1 alpha-3 country codes (e.g. USA, "
    "CHN, RUS, IRN, DEU, JPN, KOR, GBR, FRA, IND, UKR). If you cannot "
    "identify two distinct countries, respond with "
    '{"country_a": null, "country_b": null}.'
)

ISO3_PATTERN = re.compile(r"\b[A-Z]{3}\b")


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def extract_conflict_parties(raw_input: str, llm: LLMClient) -> tuple[str | None, str | None]:
    """
    Returns (country_a_iso, country_b_iso) - either may be None if
    extraction failed. Caller is responsible for validating the codes
    actually exist in our country data before using them.
    """
    response = llm.complete(system=SYSTEM_PROMPT, user=raw_input)
    cleaned = _strip_code_fences(response)

    try:
        data = json.loads(cleaned)
        a = data.get("country_a")
        b = data.get("country_b")
        if a and b and isinstance(a, str) and isinstance(b, str):
            return a.upper(), b.upper()
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Context agent returned non-JSON response, trying regex fallback: %r", response)

    # Fallback: some free-tier models won't follow the JSON instruction
    # reliably - grab the first two distinct 3-letter uppercase codes
    # mentioned anywhere in the response.
    codes = list(dict.fromkeys(ISO3_PATTERN.findall(response)))  # dedupe, preserve order
    if len(codes) >= 2:
        return codes[0], codes[1]

    return None, None
