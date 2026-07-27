from app.agents.critic_agent import (
    check_numeric_grounding,
    check_semantic_grounding,
    review_narrative,
)
from app.schemas.analyze import NarrativeSection, RankedCountry, SectorBreakdown


def _country(iso="JPN", name="Japan", composite=40.88, trade=35.33, energy=5.0, alliance=100.0):
    return RankedCountry(
        iso_code=iso,
        name=name,
        exposure_score=composite,
        breakdown=SectorBreakdown(trade_score=trade, energy_score=energy, alliance_score=alliance),
    )


class FakeLLMClient:
    def __init__(self, canned_response: str):
        self.canned_response = canned_response
        self.calls = []

    def complete(self, system, user, models=None):
        self.calls.append({"system": system, "user": user})
        return self.canned_response


# --- numeric grounding (deterministic, no LLM) ---

def test_numeric_grounding_passes_when_numbers_match_known_scores():
    country = _country()
    section = NarrativeSection(
        heading="Japan (JPN)",
        text="Japan shows 40.88% composite exposure, driven mainly by a 100.0 alliance score.",
        tag="data-derived",
    )
    verdict = check_numeric_grounding(section, country)
    assert verdict.passed


def test_numeric_grounding_fails_on_invented_number():
    country = _country()
    section = NarrativeSection(
        heading="Japan (JPN)",
        text="Japan's exposure jumped 75% after recent tariff changes.",
        tag="data-derived",
    )
    verdict = check_numeric_grounding(section, country)
    assert not verdict.passed
    assert "75" in verdict.reason


def test_numeric_grounding_allows_year_references():
    country = _country()
    section = NarrativeSection(
        heading="Japan (JPN)",
        text="As of 2023, Japan shows a 100.0 alliance score.",
        tag="data-derived",
    )
    verdict = check_numeric_grounding(section, country)
    assert verdict.passed  # 2023 is a year, not treated as a fabricated stat


def test_numeric_grounding_allows_rounding_tolerance():
    country = _country(trade=35.33)
    section = NarrativeSection(
        heading="Japan (JPN)", text="Trade exposure is around 35%.", tag="data-derived"
    )
    verdict = check_numeric_grounding(section, country)
    assert verdict.passed  # 35 vs 35.33 within tolerance


# --- semantic grounding (LLM-based) ---

def test_semantic_grounding_pass():
    llm = FakeLLMClient("PASS")
    section = NarrativeSection(heading="Japan (JPN)", text="Some grounded text.", tag="data-derived")
    verdict = check_semantic_grounding(section, "source data here", llm)
    assert verdict.passed


def test_semantic_grounding_fail():
    llm = FakeLLMClient("FAIL: mentions a trade deal not present in source data")
    section = NarrativeSection(heading="Japan (JPN)", text="Some text.", tag="data-derived")
    verdict = check_semantic_grounding(section, "source data here", llm)
    assert not verdict.passed
    assert "trade deal" in verdict.reason


# --- full review pipeline ---

def test_review_narrative_drops_numerically_ungrounded_sections():
    llm = FakeLLMClient("PASS")  # would pass semantic check if reached
    countries = [_country()]
    sections = [
        NarrativeSection(
            heading="Japan (JPN)", text="Exposure spiked 999% overnight.", tag="data-derived"
        )
    ]
    accepted, rejected = review_narrative(sections, countries, "USA", "CHN", llm)
    assert accepted == []
    assert len(rejected) == 1
    assert "999" in rejected[0]["reason"]


def test_review_narrative_drops_semantically_ungrounded_sections():
    llm = FakeLLMClient("FAIL: invented an event")
    countries = [_country()]
    sections = [
        NarrativeSection(
            heading="Japan (JPN)", text="Japan shows a 100.0 alliance score.", tag="data-derived"
        )
    ]
    accepted, rejected = review_narrative(sections, countries, "USA", "CHN", llm)
    assert accepted == []
    assert len(rejected) == 1
    assert "invented an event" in rejected[0]["reason"]


def test_review_narrative_keeps_grounded_sections():
    llm = FakeLLMClient("PASS")
    countries = [_country()]
    sections = [
        NarrativeSection(
            heading="Japan (JPN)", text="Japan shows a 100.0 alliance score.", tag="data-derived"
        )
    ]
    accepted, rejected = review_narrative(sections, countries, "USA", "CHN", llm)
    assert len(accepted) == 1
    assert rejected == []
