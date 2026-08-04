"""
Deterministic exposure scoring engine.

Design constraint (blueprint 5.1 / 8.2): zero LLM calls, zero network I/O.
Every function here is pure — same inputs always produce the same output —
so it's fully unit-testable against fixtures and auditable in an interview.

Weighting (documented per 5.4 "document your formula's assumptions"):
    composite = 0.45 * trade_score + 0.40 * energy_score + 0.15 * alliance_score
Revised from an earlier 0.40/0.35/0.25 split: alliance_score is a coarse,
near-binary signal (100 at 1 hop, 50 at 2 hops) that was letting bare
treaty membership alone push a country's composite as high as countries
with real, measured trade+energy exposure - e.g. any NATO member with
zero trade/energy data against a non-NATO conflict still scored 25.0
composite under the old weights, on alliance alone. Alliance is now a
smaller share so it can nudge a ranking but not dominate it when trade/
energy data is thin or missing. Override via `weights=` param.
"""

from dataclasses import dataclass

import networkx as nx

DEFAULT_WEIGHTS = {"trade": 0.45, "energy": 0.40, "alliance": 0.15}

# Per FR2 edge case: countries with no data must show "insufficient data",
# never a silent 0 (a silent 0 misleadingly implies "confirmed no exposure").
INSUFFICIENT_DATA = None


@dataclass
class TradeExposureInput:
    """Third-party country C's trade tied to conflict parties A/B."""

    country_iso: str
    trade_value_with_a_usd: float | None
    trade_value_with_b_usd: float | None
    country_total_trade_usd: float | None


@dataclass
class EnergyExposureInput:
    """Third-party country C's energy import dependency on A/B."""

    country_iso: str
    import_share_from_a_pct: float | None  # 0-100, % of C's energy imports sourced from A
    import_share_from_b_pct: float | None


@dataclass
class ScoreResult:
    value: float | None  # None means insufficient_data
    insufficient_data: bool
    detail: str


def trade_score(inp: TradeExposureInput) -> ScoreResult:
    """
    % of country C's total trade tied to either conflict party, scaled 0-100.
    Capped at 100 (a country doing >100% notional trade with A+B combined
    relative to its reported total is a data-quality artifact, not a real score).
    """
    if (
        inp.trade_value_with_a_usd is None
        and inp.trade_value_with_b_usd is None
    ) or not inp.country_total_trade_usd:
        return ScoreResult(INSUFFICIENT_DATA, True, "no trade data reported for this country")

    a = inp.trade_value_with_a_usd or 0.0
    b = inp.trade_value_with_b_usd or 0.0
    pct = ((a + b) / inp.country_total_trade_usd) * 100
    return ScoreResult(round(min(pct, 100.0), 2), False, f"{a+b:,.0f} USD tied to conflict parties")


def energy_score(inp: EnergyExposureInput) -> ScoreResult:
    """
    Energy exposure = larger of the two import-share percentages (worst case
    dependency, not averaged — a 40% dependency on A isn't softened by 0%
    dependency on B).
    """
    if inp.import_share_from_a_pct is None and inp.import_share_from_b_pct is None:
        return ScoreResult(INSUFFICIENT_DATA, True, "no energy dependency data reported")

    share = max(inp.import_share_from_a_pct or 0.0, inp.import_share_from_b_pct or 0.0)
    return ScoreResult(round(min(share, 100.0), 2), False, f"{share:.1f}% import dependency")


def alliance_score(
    alliance_graph: nx.Graph, country_iso: str, party_a_iso: str, party_b_iso: str
) -> ScoreResult:
    """
    Graph-distance-based proximity (blueprint 3.1: "simple graph distance,
    not full game-theoretic modeling"). Shortest path in the alliance graph
    from C to the nearer of A/B; distance 1 (direct treaty) -> 100,
    decaying with each additional hop. Unreachable -> 0 (not insufficient
    data — "no alliance path found" is itself a real, computed answer).
    """
    if country_iso not in alliance_graph:
        return ScoreResult(INSUFFICIENT_DATA, True, "country not present in alliance graph")

    distances = []
    for party in (party_a_iso, party_b_iso):
        if party not in alliance_graph:
            continue
        try:
            d = nx.shortest_path_length(alliance_graph, country_iso, party)
            distances.append(d)
        except nx.NetworkXNoPath:
            continue

    if not distances:
        return ScoreResult(0.0, False, "no alliance path to either conflict party")

    min_dist = min(distances)
    if min_dist == 0:
        # country_iso is one of the conflict parties itself
        score = 100.0
    else:
        score = 100.0 / min_dist
    return ScoreResult(round(score, 2), False, f"{min_dist} hop(s) from nearest conflict party")


def composite_score(
    trade: ScoreResult,
    energy: ScoreResult,
    alliance: ScoreResult,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> ScoreResult:
    """
    Weighted composite with a confidence penalty for missing sub-scores.

    Naive renormalization (average only over available sub-scores) is
    WRONG here: a country with only alliance data (e.g. NATO member,
    score 100) would renormalize to composite=100 - outranking a
    country with real trade+energy+alliance data averaging to 40. That
    rewards having LESS data, which is backwards.

    Fix: composite = (weighted average of available sub-scores) *
    (fraction of total weight actually covered). A country missing
    2 of 3 dimensions gets scaled down accordingly - incomplete data
    can never outrank complete data on this metric alone. If ALL
    three are missing, the composite itself is insufficient_data.
    """
    parts = [
        (trade, weights["trade"]),
        (energy, weights["energy"]),
        (alliance, weights["alliance"]),
    ]
    available = [(s.value, w) for s, w in parts if not s.insufficient_data and s.value is not None]

    if not available:
        return ScoreResult(INSUFFICIENT_DATA, True, "no sub-scores available")

    total_weight = sum(w for _, w in available)
    weighted_sum = sum(v * w for v, w in available)
    raw_average = weighted_sum / total_weight
    confidence = total_weight  # weights sum to 1.0 by design, so this is a 0-1 coverage fraction
    composite = raw_average * confidence

    missing = [name for (s, _), name in zip(parts, ("trade", "energy", "alliance")) if s.insufficient_data]
    detail = (
        "all sub-scores available"
        if not missing
        else f"missing: {', '.join(missing)} (confidence-penalized, {confidence:.0%} data coverage)"
    )
    return ScoreResult(round(composite, 2), False, detail)
