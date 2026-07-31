from decimal import Decimal, localcontext

from app.strategy.analytics.strategy_quality import (
    StrategyQualityAnalyzer,
)


def test_system_quality_number():
    analyzer = StrategyQualityAnalyzer()

    result = analyzer.system_quality_number(
        [
            Decimal("100"),
            Decimal("-50"),
            Decimal("200"),
            Decimal("-25"),
        ]
    )

    # Mean = 56.25
    # Sample standard deviation ≈ 113.651
    # SQN = sqrt(4) * 56.25 / stddev
    with localcontext() as context:
        context.prec = 28

    sample_variance = (
        Decimal("40468.75")
        / Decimal("3")
    )

    expected = (
        Decimal("4").sqrt()
        * Decimal("56.25")
        / sample_variance.sqrt()
    )

    assert result == expected


def test_system_quality_number_returns_zero_without_variation():
    analyzer = StrategyQualityAnalyzer()

    result = analyzer.system_quality_number(
        [
            Decimal("100"),
            Decimal("100"),
        ]
    )

    assert result == Decimal("0")


def test_kelly_criterion():
    analyzer = StrategyQualityAnalyzer()

    result = analyzer.kelly_criterion(
        win_rate=Decimal("0.60"),
        payoff_ratio=Decimal("2"),
    )

    assert result == Decimal("0.40")


def test_kelly_criterion_returns_zero_for_zero_payoff_ratio():
    analyzer = StrategyQualityAnalyzer()

    result = analyzer.kelly_criterion(
        win_rate=Decimal("0.60"),
        payoff_ratio=Decimal("0"),
    )

    assert result == Decimal("0")


def test_gain_to_pain_ratio():
    analyzer = StrategyQualityAnalyzer()

    result = analyzer.gain_to_pain_ratio(
        [
            Decimal("0.10"),
            Decimal("-0.04"),
            Decimal("0.05"),
            Decimal("-0.01"),
        ]
    )

    assert result == Decimal("3")


def test_gain_to_pain_ratio_returns_zero_without_losses():
    analyzer = StrategyQualityAnalyzer()

    result = analyzer.gain_to_pain_ratio(
        [
            Decimal("0.10"),
            Decimal("0.05"),
        ]
    )

    assert result == Decimal("0")


def test_ulcer_index():
    analyzer = StrategyQualityAnalyzer()

    result = analyzer.ulcer_index(
        [
            Decimal("100"),
            Decimal("90"),
            Decimal("80"),
            Decimal("120"),
        ]
    )

    # Drawdowns: 0%, 10%, 20%, 0%
    # UI = sqrt((0² + .10² + .20² + 0²) / 4)
    with localcontext() as context:
        context.prec = 28
        expected = (
            Decimal("0.0125").sqrt()
        )

    assert result == expected


def test_ulcer_index_returns_zero_without_equity_values():
    analyzer = StrategyQualityAnalyzer()

    assert analyzer.ulcer_index([]) == Decimal("0")