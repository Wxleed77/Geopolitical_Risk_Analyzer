from app.schemas.analyze import RankedCountry, SectorBreakdown
from app.services.narrative_service import build_narrative_sections


class FakeLLMClient:
    """Stands in for LLMClient - no network call, records what it was asked."""

    def __init__(self, canned_response: str = "Fake narrative response."):
        self.canned_response = canned_response
        self.calls: list[dict] = []

    def complete(self, system: str, user: str, models=None) -> str:
        self.calls.append({"system": system, "user": user})
        return self.canned_response


def _make_country(iso, name, score) -> RankedCountry:
    return RankedCountry(
        iso_code=iso,
        name=name,
        exposure_score=score,
        breakdown=SectorBreakdown(trade_score=10.0, energy_score=5.0, alliance_score=100.0),
    )


def test_build_narrative_sections_tags_as_data_derived():
    fake = FakeLLMClient()
    ranked = [_make_country("JPN", "Japan", 40.0)]
    sections = build_narrative_sections(ranked, "USA", "CHN", fake)

    assert len(sections) == 1
    assert sections[0].tag == "data-derived"
    assert sections[0].heading == "Japan (JPN)"
    assert sections[0].text == "Fake narrative response."


def test_build_narrative_sections_limits_to_top_n():
    fake = FakeLLMClient()
    ranked = [_make_country(f"C{i}", f"Country{i}", 100 - i) for i in range(10)]
    sections = build_narrative_sections(ranked, "USA", "CHN", fake)

    assert len(sections) == 5  # TOP_N_TO_NARRATE
    assert len(fake.calls) == 5


def test_build_narrative_sections_prompt_includes_real_scores_not_invented_data():
    fake = FakeLLMClient()
    ranked = [_make_country("DEU", "Germany", 37.22)]
    build_narrative_sections(ranked, "USA", "CHN", fake)

    prompt = fake.calls[0]["user"]
    assert "Germany" in prompt
    assert "37.22" in prompt
    assert "USA" in prompt and "CHN" in prompt
    # system prompt must forbid inventing facts beyond the given numbers
    assert "Do not invent" in fake.calls[0]["system"]
