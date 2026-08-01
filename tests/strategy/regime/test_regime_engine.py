from decimal import Decimal

import pytest

from app.strategy.regime.regime_engine import (
    MarketRegimeEngine,
)
from app.strategy.regime.regime_models import (
    MarketRegime,
    MarketRegimeSignal,
    RegimeConfidence,
    RegimeDetectionStatus,
)


def signal(
    *,
    trend: str = "0.50",
    volatility: str = "0.50",
    breadth: str = "0.50",
    momentum: str = "0.50",
    liquidity: str = "0.50",
    warnings=(),
) -> MarketRegimeSignal:
    return MarketRegimeSignal(
        signal_id="market-001",
        trend_score=Decimal(trend),
        volatility_score=Decimal(volatility),
        breadth_score=Decimal(breadth),
        momentum_score=Decimal(momentum),
        liquidity_score=Decimal(liquidity),
        warnings=tuple(warnings),
    )


def test_detect_returns_completed_report() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.80",
            volatility="0.25",
            breadth="0.75",
            momentum="0.78",
            liquidity="0.90",
        )
    )

    assert report.status is RegimeDetectionStatus.COMPLETED
    assert report.error is None
    assert report.signal is not None


def test_detects_strong_bull() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.90",
            volatility="0.20",
            breadth="0.85",
            momentum="0.88",
            liquidity="0.90",
        )
    )

    assert report.regime is MarketRegime.STRONG_BULL


def test_detects_bull() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.70",
            volatility="0.45",
            breadth="0.65",
            momentum="0.68",
            liquidity="0.80",
        )
    )

    assert report.regime is MarketRegime.BULL


def test_detects_sideways() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.50",
            volatility="0.50",
            breadth="0.50",
            momentum="0.50",
            liquidity="0.50",
        )
    )

    assert report.regime is MarketRegime.SIDEWAYS


def test_detects_correction() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.40",
            volatility="0.55",
            breadth="0.45",
            momentum="0.35",
            liquidity="0.65",
        )
    )

    assert report.regime is MarketRegime.CORRECTION


def test_detects_bear() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.25",
            volatility="0.65",
            breadth="0.30",
            momentum="0.25",
            liquidity="0.55",
        )
    )

    assert report.regime is MarketRegime.BEAR


def test_detects_strong_bear() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.10",
            volatility="0.75",
            breadth="0.15",
            momentum="0.10",
            liquidity="0.40",
        )
    )

    assert report.regime is MarketRegime.STRONG_BEAR


def test_detects_high_volatility() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.55",
            volatility="0.90",
            breadth="0.55",
            momentum="0.50",
            liquidity="0.70",
        )
    )

    assert report.regime is MarketRegime.HIGH_VOLATILITY


def test_detects_risk_off_before_other_regimes() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.15",
            volatility="0.95",
            breadth="0.15",
            momentum="0.10",
            liquidity="0.15",
        )
    )

    assert report.regime is MarketRegime.RISK_OFF


def test_detects_unknown() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.62",
            volatility="0.75",
            breadth="0.35",
            momentum="0.58",
            liquidity="0.10",
        )
    )

    assert report.regime is MarketRegime.UNKNOWN
    assert report.confidence is RegimeConfidence.LOW

    assert report.regime is MarketRegime.UNKNOWN
    assert report.confidence is RegimeConfidence.LOW


def test_overall_score_is_calculated() -> None:
    value = signal(
        trend="0.80",
        volatility="0.20",
        breadth="0.70",
        momentum="0.75",
        liquidity="0.85",
    )

    expected = (
        Decimal("0.80")
        + Decimal("0.80")
        + Decimal("0.70")
        + Decimal("0.75")
        + Decimal("0.85")
    ) / Decimal("5")

    report = MarketRegimeEngine().detect(value)

    assert report.overall_score == expected


@pytest.mark.parametrize(
    (
        "overall_score",
        "trend",
        "breadth",
        "momentum",
        "expected",
    ),
    [
        (
            "0.95",
            "0.90",
            "0.90",
            "0.90",
            RegimeConfidence.VERY_HIGH,
        ),
        (
            "0.80",
            "0.90",
            "0.90",
            "0.90",
            RegimeConfidence.HIGH,
        ),
        (
            "0.65",
            "0.90",
            "0.60",
            "0.60",
            RegimeConfidence.MEDIUM,
        ),
        (
            "0.50",
            "0.90",
            "0.10",
            "0.10",
            RegimeConfidence.LOW,
        ),
    ],
)
def test_confidence_boundaries(
    overall_score: str,
    trend: str,
    breadth: str,
    momentum: str,
    expected: RegimeConfidence,
) -> None:
    result = MarketRegimeEngine._confidence(
        signal=signal(
            trend=trend,
            breadth=breadth,
            momentum=momentum,
        ),
        regime=MarketRegime.BULL,
        overall_score=Decimal(overall_score),
    )

    assert result is expected


def test_elevated_volatility_adds_warning() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.55",
            volatility="0.90",
            breadth="0.55",
            momentum="0.50",
            liquidity="0.70",
        )
    )

    assert (
        "Market volatility is elevated."
        in report.warnings
    )


def test_weak_liquidity_adds_warning() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.50",
            volatility="0.50",
            breadth="0.50",
            momentum="0.50",
            liquidity="0.20",
        )
    )

    assert "Market liquidity is weak." in report.warnings


def test_divergent_signals_add_warning() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.90",
            volatility="0.50",
            breadth="0.50",
            momentum="0.20",
            liquidity="0.70",
        )
    )

    assert (
        "Trend and momentum signals are materially divergent."
        in report.warnings
    )


def test_input_warnings_are_preserved() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            warnings=("Breadth data is incomplete.",),
        )
    )

    assert (
        "Breadth data is incomplete."
        in report.warnings
    )


def test_unknown_regime_adds_warning() -> None:
    report = MarketRegimeEngine().detect(
        signal(
            trend="0.62",
            volatility="0.75",
            breadth="0.35",
            momentum="0.58",
            liquidity="0.10",
        )
    )

    assert (
        "Available signals do not support a clear regime."
        in report.warnings
    )


@pytest.mark.parametrize(
    "regime",
    list(MarketRegime),
)
def test_every_regime_has_recommendation(
    regime: MarketRegime,
) -> None:
    recommendation = (
        MarketRegimeEngine._recommendation(regime)
    )

    assert recommendation.strip()


def test_signal_must_be_market_regime_signal() -> None:
    with pytest.raises(
        TypeError,
        match="signal must be a MarketRegimeSignal",
    ):
        MarketRegimeEngine().detect(object())