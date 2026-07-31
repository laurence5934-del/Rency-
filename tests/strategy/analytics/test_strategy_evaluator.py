from decimal import Decimal

import pytest

from app.strategy.analytics.expectancy_models import (
    ExpectancyMetrics,
)
from app.strategy.analytics.models import (
    AnalyticsReport,
    ReturnMetrics,
)
from app.strategy.analytics.performance_models import (
    PerformanceMetrics,
)
from app.strategy.analytics.risk_models import (
    RiskMetrics,
)
from app.strategy.analytics.strategy_evaluation_models import (
    StrategyEvaluation,
)
from app.strategy.analytics.strategy_evaluator import (
    StrategyEvaluator,
)
from app.strategy.analytics.strategy_quality_models import (
    StrategyQualityMetrics,
)


def build_report(
    *,
    sharpe_ratio: Decimal = Decimal("1.5"),
    sortino_ratio: Decimal = Decimal("2"),
    profit_factor: Decimal = Decimal("1.5"),
    max_drawdown: Decimal = Decimal("0.10"),
    system_quality_number: Decimal = Decimal("2"),
    recovery_factor: Decimal = Decimal("3"),
    kelly_criterion: Decimal = Decimal("0.25"),
    expectancy: Decimal = Decimal("100"),
) -> AnalyticsReport:
    return AnalyticsReport(
        returns=ReturnMetrics(
            initial_capital=Decimal("10000"),
            final_equity=Decimal("11000"),
            net_profit=Decimal("1000"),
            total_return=Decimal("0.10"),
            annualized_return=Decimal("0.10"),
            cagr=Decimal("0.10"),
        ),
        performance=PerformanceMetrics(
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=Decimal("1.25"),
            profit_factor=profit_factor,
            win_rate=Decimal("60"),
        ),
        risk=RiskMetrics(
            max_drawdown=max_drawdown,
            drawdown_duration=3,
            volatility=Decimal("0.12"),
        ),
        expectancy=ExpectancyMetrics(
            average_win=Decimal("200"),
            average_loss=Decimal("100"),
            payoff_ratio=Decimal("2"),
            expectancy=expectancy,
            expectancy_percent=Decimal("1"),
            recovery_factor=recovery_factor,
        ),
        strategy_quality=StrategyQualityMetrics(
            system_quality_number=(
                system_quality_number
            ),
            kelly_criterion=kelly_criterion,
            gain_to_pain_ratio=Decimal("3"),
            ulcer_index=Decimal("0.05"),
        ),
    )


def test_evaluate_returns_strategy_evaluation():
    result = StrategyEvaluator().evaluate(
        build_report()
    )

    assert isinstance(result, StrategyEvaluation)


def test_excellent_strategy_scores_one_hundred():
    result = StrategyEvaluator().evaluate(
        build_report()
    )

    assert result.score == 100
    assert result.grade == "A"
    assert (
        result.recommendation
        == "READY_FOR_LIVE_TRADING"
    )


def test_poor_strategy_scores_zero():
    report = build_report(
        sharpe_ratio=Decimal("0.5"),
        sortino_ratio=Decimal("0.7"),
        profit_factor=Decimal("0.8"),
        max_drawdown=Decimal("0.30"),
        system_quality_number=Decimal("0.5"),
        recovery_factor=Decimal("0.8"),
        kelly_criterion=Decimal("0.50"),
        expectancy=Decimal("-20"),
    )

    result = StrategyEvaluator().evaluate(report)

    assert result.score == 0
    assert result.grade == "F"
    assert result.recommendation == "DO_NOT_DEPLOY"


@pytest.mark.parametrize(
    ("score", "expected_grade"),
    [
        (100, "A"),
        (90, "A"),
        (89, "B"),
        (80, "B"),
        (79, "C"),
        (70, "C"),
        (69, "D"),
        (60, "D"),
        (59, "F"),
        (0, "F"),
    ],
)
def test_grade_boundaries(
    score: int,
    expected_grade: str,
):
    assert (
        StrategyEvaluator._grade(score)
        == expected_grade
    )


@pytest.mark.parametrize(
    ("grade", "expected_recommendation"),
    [
        ("A", "READY_FOR_LIVE_TRADING"),
        ("B", "READY_FOR_PAPER_TRADING"),
        ("C", "NEEDS_OPTIMIZATION"),
        ("D", "DO_NOT_DEPLOY"),
        ("F", "DO_NOT_DEPLOY"),
    ],
)
def test_recommendation_mapping(
    grade: str,
    expected_recommendation: str,
):
    assert (
        StrategyEvaluator._recommendation(grade)
        == expected_recommendation
    )


def test_strengths_are_recorded_for_metrics_at_threshold():
    result = StrategyEvaluator().evaluate(
        build_report()
    )

    assert result.strengths == (
        "Sharpe ratio meets or exceeds target",
        "Sortino ratio meets or exceeds target",
        "Profit factor indicates favorable trade efficiency",
        "Maximum drawdown is within tolerance",
        "System Quality Number indicates a strong strategy",
        "Recovery factor meets or exceeds target",
        "Kelly criterion is within conservative limits",
    )


def test_concerns_are_recorded_for_weak_metrics():
    report = build_report(
        sharpe_ratio=Decimal("1"),
        sortino_ratio=Decimal("1"),
        profit_factor=Decimal("1"),
        max_drawdown=Decimal("0.20"),
        system_quality_number=Decimal("1"),
        recovery_factor=Decimal("1"),
        kelly_criterion=Decimal("0.40"),
        expectancy=Decimal("0"),
    )

    result = StrategyEvaluator().evaluate(report)

    assert result.concerns == (
        "Sharpe ratio is below target",
        "Sortino ratio is below target",
        "Profit factor is below target",
        "Maximum drawdown exceeds tolerance",
        "System Quality Number is below target",
        "Recovery factor is below target",
        "Kelly criterion indicates aggressive position sizing",
        "Trade expectancy is not positive",
    )


def test_negative_kelly_criterion_is_a_concern():
    result = StrategyEvaluator().evaluate(
        build_report(
            kelly_criterion=Decimal("-0.10"),
        )
    )

    assert (
        "Kelly criterion is negative"
        in result.concerns
    )
    assert (
        "Kelly criterion is within conservative limits"
        not in result.strengths
    )


def test_negative_drawdown_is_not_awarded_points():
    result = StrategyEvaluator().evaluate(
        build_report(
            max_drawdown=Decimal("-0.10"),
        )
    )

    assert result.score == 85
    assert (
        "Maximum drawdown cannot be negative"
        in result.concerns
    )


def test_non_positive_expectancy_is_a_concern():
    result = StrategyEvaluator().evaluate(
        build_report(
            expectancy=Decimal("0"),
        )
    )

    assert (
        "Trade expectancy is not positive"
        in result.concerns
    )


def test_evaluation_model_is_immutable():
    result = StrategyEvaluator().evaluate(
        build_report()
    )

    with pytest.raises(
        (AttributeError, TypeError),
    ):
        result.score = 50