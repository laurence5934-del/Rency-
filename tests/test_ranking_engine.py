from __future__ import annotations

import pytest

from app.ai.ranking_engine import RankingEngine
from app.ai.recommendation_models import Recommendation
from app.watchlist.watchlist_models import WatchlistEntry


def make_entry(
    *,
    symbol: str = "AAPL",
    trend: float = 80,
    momentum: float = 75,
    volume: float = 70,
    breakout: float = 65,
    risk: float = 90,
) -> WatchlistEntry:
    return WatchlistEntry(
        rank=1,
        symbol=symbol,
        last_price=100.0,
        total_score=0.0,
        qualified=True,
        trend_score=trend,
        momentum_score=momentum,
        volume_score=volume,
        breakout_score=breakout,
        risk_score=risk,
        reasons=(),
    )


def test_rank_entry_returns_result() -> None:
    engine = RankingEngine()

    result = engine.rank_entry(make_entry())

    assert result.symbol == "AAPL"
    assert result.overall_score > 0
    assert 0 <= result.confidence <= 100


def test_rank_entries_orders_results() -> None:
    engine = RankingEngine()

    entries = [
        make_entry(symbol="LOW", trend=40),
        make_entry(symbol="HIGH", trend=95),
    ]

    summary = engine.rank_entries(entries)

    assert summary.results[0].symbol == "HIGH"
    assert summary.results[1].symbol == "LOW"


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (90, Recommendation.STRONG_BUY),
        (75, Recommendation.BUY),
        (60, Recommendation.WATCH),
        (45, Recommendation.HOLD),
        (20, Recommendation.SELL),
    ],
)
def test_recommendation_thresholds(
    score,
    expected,
) -> None:
    engine = RankingEngine()

    entry = make_entry(
        trend=score,
        momentum=score,
        volume=score,
        breakout=score,
        risk=score,
    )

    result = engine.rank_entry(entry)

    assert result.recommendation == expected


def test_confidence_is_bounded() -> None:
    engine = RankingEngine()

    result = engine.rank_entry(make_entry())

    assert 0 <= result.confidence <= 100


def test_balanced_profile_generates_default_reason() -> None:
    engine = RankingEngine()

    result = engine.rank_entry(
        make_entry(
            trend=60,
            momentum=60,
            volume=60,
            breakout=60,
            risk=60,
        )
    )

    assert result.explanations == (
        "Balanced factor profile",
    )


def test_high_scores_generate_positive_reasons() -> None:
    engine = RankingEngine()

    result = engine.rank_entry(
        make_entry(
            trend=90,
            momentum=90,
            volume=90,
            breakout=90,
            risk=90,
        )
    )

    assert "Strong trend" in result.explanations
    assert "Strong momentum" in result.explanations


def test_low_scores_generate_negative_reasons() -> None:
    engine = RankingEngine()

    result = engine.rank_entry(
        make_entry(
            trend=20,
            momentum=20,
            volume=20,
            breakout=20,
            risk=20,
        )
    )

    assert "Weak trend" in result.explanations
    assert "Weak momentum" in result.explanations


def test_invalid_factor_score_raises() -> None:
    engine = RankingEngine()

    with pytest.raises(ValueError):
        engine.rank_entry(
            make_entry(trend=120)
        )


def test_rank_entry_requires_watchlist_entry() -> None:
    engine = RankingEngine()

    with pytest.raises(TypeError):
        engine.rank_entry(None)  # type: ignore[arg-type]


def test_rank_entries_requires_iterable() -> None:
    engine = RankingEngine()

    with pytest.raises(TypeError):
        engine.rank_entries(None)  # type: ignore[arg-type]


def test_summary_strongest() -> None:
    engine = RankingEngine()

    summary = engine.rank_entries(
        [
            make_entry(symbol="A", trend=60),
            make_entry(symbol="B", trend=95),
        ]
    )

    assert summary.strongest is not None
    assert summary.strongest.symbol == "B"


def test_summary_average_score() -> None:
    engine = RankingEngine()

    summary = engine.rank_entries(
        [
            make_entry(symbol="A"),
            make_entry(symbol="B"),
        ]
    )

    assert summary.average_score > 0