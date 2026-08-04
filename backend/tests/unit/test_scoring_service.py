import networkx as nx
import pytest

from app.services.scoring_service import (
    EnergyExposureInput,
    TradeExposureInput,
    alliance_score,
    composite_score,
    energy_score,
    trade_score,
)


# --- trade_score ---

def test_trade_score_basic():
    inp = TradeExposureInput("DEU", trade_value_with_a_usd=10_000, trade_value_with_b_usd=5_000,
                              country_total_trade_usd=100_000)
    result = trade_score(inp)
    assert result.value == 15.0
    assert not result.insufficient_data


def test_trade_score_missing_data_returns_insufficient():
    inp = TradeExposureInput("TUV", None, None, None)
    result = trade_score(inp)
    assert result.value is None
    assert result.insufficient_data


def test_trade_score_caps_at_100():
    inp = TradeExposureInput("XXX", 90_000, 90_000, 100_000)
    result = trade_score(inp)
    assert result.value == 100.0


# --- energy_score ---

def test_energy_score_takes_max_not_average():
    inp = EnergyExposureInput("JPN", import_share_from_a_pct=40.0, import_share_from_b_pct=5.0)
    result = energy_score(inp)
    assert result.value == 40.0


def test_energy_score_insufficient_data():
    inp = EnergyExposureInput("XXX", None, None)
    result = energy_score(inp)
    assert result.insufficient_data


# --- alliance_score ---

@pytest.fixture
def graph():
    g = nx.Graph()
    g.add_edge("USA", "GBR")   # direct treaty
    g.add_edge("GBR", "FRA")
    g.add_edge("FRA", "DEU")   # DEU is 2 hops from USA
    g.add_node("PRK")         # isolated, no path to USA/IRN
    return g


def test_alliance_score_direct_treaty(graph):
    result = alliance_score(graph, "GBR", "USA", "IRN")
    assert result.value == 100.0  # 1 hop


def test_alliance_score_decays_with_distance(graph):
    result = alliance_score(graph, "FRA", "USA", "IRN")
    assert result.value == 50.0  # FRA-GBR-USA = 2 hops -> 100/2


def test_alliance_score_no_path_is_zero_not_insufficient(graph):
    result = alliance_score(graph, "PRK", "USA", "IRN")
    assert result.value == 0.0
    assert not result.insufficient_data


def test_alliance_score_country_not_in_graph_is_insufficient(graph):
    result = alliance_score(graph, "ZZZ", "USA", "IRN")
    assert result.insufficient_data


# --- composite_score ---

def test_composite_score_weighted_average():
    from app.services.scoring_service import ScoreResult
    t = ScoreResult(60.0, False, "")
    e = ScoreResult(40.0, False, "")
    a = ScoreResult(20.0, False, "")
    result = composite_score(t, e, a)
    # 0.45*60 + 0.40*40 + 0.15*20 = 27 + 16 + 3 = 46
    assert result.value == 46.0


def test_composite_score_renormalizes_on_missing_subscore():
    from app.services.scoring_service import ScoreResult
    t = ScoreResult(60.0, False, "")
    e = ScoreResult(None, True, "missing")
    a = ScoreResult(20.0, False, "")
    result = composite_score(t, e, a)
    # available weight = trade(0.45) + alliance(0.15) = 0.60
    # raw_average = (60*0.45 + 20*0.15) / 0.60 ; composite = raw_average * 0.60
    # (the 0.60 cancels the division - this is intentionally just the weighted_sum)
    expected = 60.0 * 0.45 + 20.0 * 0.15
    assert result.value == round(expected, 2)


def test_composite_score_sparse_data_cannot_outrank_complete_data():
    """The bug this test guards against: a country with ONLY alliance
    data (e.g. NATO membership, no trade/energy) must NOT outscore a
    country with real trade+energy+alliance data, even if that one
    alliance score is the max possible (100)."""
    from app.services.scoring_service import ScoreResult

    alliance_only = composite_score(
        ScoreResult(None, True, "missing"),
        ScoreResult(None, True, "missing"),
        ScoreResult(100.0, False, ""),
    )
    full_data_moderate = composite_score(
        ScoreResult(35.0, False, ""),
        ScoreResult(10.0, False, ""),
        ScoreResult(50.0, False, ""),
    )
    assert alliance_only.value == 15.0  # 100 * 0.15 weight, confidence-penalized
    assert full_data_moderate.value < 50  # moderate but complete
    assert alliance_only.value < full_data_moderate.value


def test_composite_score_all_missing_is_insufficient():
    from app.services.scoring_service import ScoreResult
    missing = ScoreResult(None, True, "missing")
    result = composite_score(missing, missing, missing)
    assert result.insufficient_data
