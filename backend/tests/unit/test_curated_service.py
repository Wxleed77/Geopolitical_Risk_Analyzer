from datetime import date

from app.services.curated_service import TIER_SCORE_ANCHOR


def test_tier_anchors_are_ordered_correctly():
    assert TIER_SCORE_ANCHOR["high"] > TIER_SCORE_ANCHOR["medium"] > TIER_SCORE_ANCHOR["low"]


def test_tier_anchors_are_in_valid_range():
    for value in TIER_SCORE_ANCHOR.values():
        assert 0 <= value <= 100
