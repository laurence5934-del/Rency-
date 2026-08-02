from decimal import Decimal

import pytest

from app.strategy.portfolio_risk.portfolio_risk_engine import (
    PortfolioRiskEngine,
)
from app.strategy.portfolio_risk.portfolio_risk_models import (
    ExposureType,
    PortfolioExposure,
    PortfolioRiskDecision,
    PortfolioRiskLimit,
    PortfolioRiskMetrics,
    PortfolioRiskStatus,
    RiskLimitSeverity,
    RiskLimitType,
)


def metrics(
    *,
    gross_exposure: str = "0.80",
    net_exposure: str = "0.70",
    leverage: str = "1.00",
    concentration: str = "0.25",
    diversification: str = "0.75",
    volatility: str = "0.15",
    drawdown: str = "0.10",
    value_at_risk: str = "0.03",
    expected_shortfall: str = "0.05",
    risk_budget: str = "0.40",
    liquidity: str = "0.90",
) -> PortfolioRiskMetrics:
    return PortfolioRiskMetrics(
        portfolio_value=Decimal("100000"),
        cash_value=Decimal("20000"),
        gross_exposure=Decimal(gross_exposure),
        net_exposure=Decimal(net_exposure),
        leverage_ratio=Decimal(leverage),
        concentration_score=Decimal(
            concentration
        ),
        diversification_score=Decimal(
            diversification
        ),
        volatility=Decimal(volatility),
        maximum_drawdown=Decimal(drawdown),
        value_at_risk=Decimal(value_at_risk),
        expected_shortfall=Decimal(
            expected_shortfall
        ),
        risk_budget_used=Decimal(risk_budget),
        liquidity_score=Decimal(liquidity),
    )


def exposure(
    exposure_id: str = "position-aapl",
    *,
    name: str = "Apple",
    exposure_type: ExposureType = (
        ExposureType.POSITION
    ),
    ratio: str = "0.20",
    market_value: str = "20000",
    liquid: bool = True,
    warnings=(),
) -> PortfolioExposure:
    return PortfolioExposure(
        exposure_id=exposure_id,
        name=name,
        exposure_type=exposure_type,
        market_value=Decimal(market_value),
        exposure_ratio=Decimal(ratio),
        risk_contribution=Decimal("0.15"),
        liquid=liquid,
        warnings=tuple(warnings),
    )


def limit(
    limit_id: str,
    limit_type: RiskLimitType,
    threshold: str,
    *,
    severity: RiskLimitSeverity = (
        RiskLimitSeverity.WARNING
    ),
    enabled: bool = True,
) -> PortfolioRiskLimit:
    return PortfolioRiskLimit(
        limit_id=limit_id,
        name=limit_id,
        limit_type=limit_type,
        threshold=Decimal(threshold),
        severity=severity,
        enabled=enabled,
    )


def assess(
    *,
    portfolio_metrics: PortfolioRiskMetrics | None = None,
    exposures=(),
    limits=(),
):
    return PortfolioRiskEngine().assess(
        metrics=portfolio_metrics or metrics(),
        exposures=exposures,
        limits=limits,
    )


def test_assessment_without_breaches_is_approved() -> None:
    report = assess(
        exposures=(exposure(),),
        limits=(
            limit(
                "position-limit",
                RiskLimitType.POSITION_EXPOSURE,
                "0.25",
            ),
            limit(
                "leverage-limit",
                RiskLimitType.LEVERAGE,
                "1.50",
                severity=RiskLimitSeverity.CRITICAL,
            ),
        ),
    )

    assert report.status is PortfolioRiskStatus.COMPLETED
    assert report.decision is PortfolioRiskDecision.APPROVE
    assert report.breaches == ()
    assert report.error is None


def test_warning_breach_requires_review() -> None:
    report = assess(
        portfolio_metrics=metrics(
            concentration="0.60"
        ),
        limits=(
            limit(
                "concentration-limit",
                RiskLimitType.CONCENTRATION,
                "0.50",
            ),
        ),
    )

    assert (
        report.decision
        is PortfolioRiskDecision.REVIEW_REQUIRED
    )
    assert len(report.breaches) == 1
    assert (
        report.breaches[0].exceeded_by
        == Decimal("0.10")
    )


def test_critical_breach_rejects_portfolio() -> None:
    report = assess(
        portfolio_metrics=metrics(
            leverage="2.00"
        ),
        limits=(
            limit(
                "leverage-limit",
                RiskLimitType.LEVERAGE,
                "1.50",
                severity=RiskLimitSeverity.CRITICAL,
            ),
        ),
    )

    assert report.decision is PortfolioRiskDecision.REJECT
    assert len(report.breaches) == 1


def test_critical_breach_precedes_warning() -> None:
    report = assess(
        portfolio_metrics=metrics(
            leverage="2.00",
            concentration="0.60",
        ),
        limits=(
            limit(
                "concentration-limit",
                RiskLimitType.CONCENTRATION,
                "0.50",
            ),
            limit(
                "leverage-limit",
                RiskLimitType.LEVERAGE,
                "1.50",
                severity=RiskLimitSeverity.CRITICAL,
            ),
        ),
    )

    assert report.decision is PortfolioRiskDecision.REJECT
    assert len(report.breaches) == 2


def test_value_equal_to_threshold_does_not_breach() -> None:
    report = assess(
        portfolio_metrics=metrics(
            leverage="1.50"
        ),
        limits=(
            limit(
                "leverage-limit",
                RiskLimitType.LEVERAGE,
                "1.50",
                severity=RiskLimitSeverity.CRITICAL,
            ),
        ),
    )

    assert report.decision is PortfolioRiskDecision.APPROVE


@pytest.mark.parametrize(
    ("limit_type", "metric_overrides"),
    [
        (
            RiskLimitType.GROSS_EXPOSURE,
            {"gross_exposure": "1.20"},
        ),
        (
            RiskLimitType.NET_EXPOSURE,
            {"net_exposure": "1.10"},
        ),
        (
            RiskLimitType.LEVERAGE,
            {"leverage": "1.80"},
        ),
        (
            RiskLimitType.CONCENTRATION,
            {"concentration": "0.70"},
        ),
        (
            RiskLimitType.VOLATILITY,
            {"volatility": "0.40"},
        ),
        (
            RiskLimitType.DRAWDOWN,
            {"drawdown": "0.35"},
        ),
        (
            RiskLimitType.VALUE_AT_RISK,
            {
                "value_at_risk": "0.10",
                "expected_shortfall": "0.12",
            },
        ),
        (
            RiskLimitType.EXPECTED_SHORTFALL,
            {
                "value_at_risk": "0.05",
                "expected_shortfall": "0.12",
            },
        ),
        (
            RiskLimitType.RISK_BUDGET,
            {"risk_budget": "0.90"},
        ),
    ],
)
def test_metric_limits_are_evaluated(
    limit_type,
    metric_overrides,
) -> None:
    report = assess(
        portfolio_metrics=metrics(
            **metric_overrides
        ),
        limits=(
            limit(
                "metric-limit",
                limit_type,
                "0.08",
            ),
        ),
    )

    assert (
        report.decision
        is PortfolioRiskDecision.REVIEW_REQUIRED
    )
    assert len(report.breaches) == 1


def test_position_limit_evaluates_each_position() -> None:
    report = assess(
        exposures=(
            exposure(
                "position-aapl",
                ratio="0.20",
            ),
            exposure(
                "position-nvda",
                name="NVIDIA",
                ratio="0.35",
            ),
        ),
        limits=(
            limit(
                "position-limit",
                RiskLimitType.POSITION_EXPOSURE,
                "0.25",
            ),
        ),
    )

    assert len(report.breaches) == 1
    assert "NVIDIA" in report.breaches[0].message


def test_multiple_positions_can_breach_same_limit() -> None:
    report = assess(
        exposures=(
            exposure(
                "position-aapl",
                ratio="0.30",
            ),
            exposure(
                "position-nvda",
                name="NVIDIA",
                ratio="0.35",
            ),
        ),
        limits=(
            limit(
                "position-limit",
                RiskLimitType.POSITION_EXPOSURE,
                "0.25",
            ),
        ),
    )

    assert len(report.breaches) == 2


def test_sector_limit_only_evaluates_sector_exposures() -> None:
    report = assess(
        exposures=(
            exposure(
                "position-aapl",
                ratio="0.50",
            ),
            exposure(
                "sector-tech",
                name="Technology",
                exposure_type=ExposureType.SECTOR,
                ratio="0.45",
                market_value="45000",
            ),
        ),
        limits=(
            limit(
                "sector-limit",
                RiskLimitType.SECTOR_EXPOSURE,
                "0.40",
            ),
        ),
    )

    assert len(report.breaches) == 1
    assert "Technology" in report.breaches[0].message


def test_disabled_limit_is_ignored() -> None:
    report = assess(
        portfolio_metrics=metrics(
            leverage="3.00"
        ),
        limits=(
            limit(
                "leverage-limit",
                RiskLimitType.LEVERAGE,
                "1.50",
                severity=RiskLimitSeverity.CRITICAL,
                enabled=False,
            ),
        ),
    )

    assert report.decision is PortfolioRiskDecision.APPROVE
    assert report.breaches == ()


def test_custom_limit_is_not_automatically_evaluated() -> None:
    report = assess(
        limits=(
            limit(
                "custom-limit",
                RiskLimitType.CUSTOM,
                "0",
            ),
        ),
    )

    assert report.decision is PortfolioRiskDecision.APPROVE


def test_low_liquidity_breaches_illiquidity_limit() -> None:
    report = assess(
        portfolio_metrics=metrics(
            liquidity="0.30"
        ),
        limits=(
            limit(
                "illiquidity-limit",
                RiskLimitType.LIQUIDITY,
                "0.50",
            ),
        ),
    )

    assert (
        report.decision
        is PortfolioRiskDecision.REVIEW_REQUIRED
    )
    assert (
        report.breaches[0].observed_value
        == Decimal("0.70")
    )


def test_good_liquidity_does_not_breach() -> None:
    report = assess(
        portfolio_metrics=metrics(
            liquidity="0.90"
        ),
        limits=(
            limit(
                "illiquidity-limit",
                RiskLimitType.LIQUIDITY,
                "0.50",
            ),
        ),
    )

    assert report.decision is PortfolioRiskDecision.APPROVE


def test_exposure_warnings_are_aggregated() -> None:
    report = assess(
        exposures=(
            exposure(
                warnings=("Position warning.",)
            ),
        ),
    )

    assert "Position warning." in report.warnings


def test_breach_messages_are_added_to_warnings() -> None:
    report = assess(
        portfolio_metrics=metrics(
            leverage="2.00"
        ),
        limits=(
            limit(
                "leverage-limit",
                RiskLimitType.LEVERAGE,
                "1.50",
            ),
        ),
    )

    assert report.breaches[0].message in report.warnings


def test_illiquid_exposure_adds_warning() -> None:
    report = assess(
        exposures=(
            exposure(
                liquid=False
            ),
        ),
    )

    assert (
        "1 portfolio exposures are marked illiquid."
        in report.warnings
    )


def test_low_liquidity_score_adds_warning() -> None:
    report = assess(
        portfolio_metrics=metrics(
            liquidity="0.30"
        ),
    )

    assert (
        "Portfolio liquidity is below the preferred level."
        in report.warnings
    )


def test_weak_diversification_adds_warning() -> None:
    report = assess(
        portfolio_metrics=metrics(
            diversification="0.30"
        ),
    )

    assert (
        "Portfolio diversification is weak."
        in report.warnings
    )


def test_approve_recommendation() -> None:
    report = assess()

    assert "may proceed" in report.recommendation


def test_review_recommendation() -> None:
    report = assess(
        portfolio_metrics=metrics(
            concentration="0.70"
        ),
        limits=(
            limit(
                "concentration-limit",
                RiskLimitType.CONCENTRATION,
                "0.50",
            ),
        ),
    )

    assert "Review warning-level" in report.recommendation


def test_reject_recommendation() -> None:
    report = assess(
        portfolio_metrics=metrics(
            leverage="2.00"
        ),
        limits=(
            limit(
                "leverage-limit",
                RiskLimitType.LEVERAGE,
                "1.50",
                severity=RiskLimitSeverity.CRITICAL,
            ),
        ),
    )

    assert "Reject new exposure" in report.recommendation


def test_duplicate_exposure_ids_return_failed_report() -> None:
    duplicate = exposure()

    report = assess(
        exposures=(
            duplicate,
            duplicate,
        ),
    )

    assert report.status is PortfolioRiskStatus.FAILED
    assert (
        report.error
        == "exposure_id values must be unique"
    )


def test_duplicate_limit_ids_return_failed_report() -> None:
    duplicate = limit(
        "duplicate-limit",
        RiskLimitType.LEVERAGE,
        "1.50",
    )

    report = assess(
        limits=(
            duplicate,
            duplicate,
        ),
    )

    assert report.status is PortfolioRiskStatus.FAILED
    assert report.error == "limit_id values must be unique"


def test_invalid_exposure_returns_failed_report() -> None:
    report = assess(
        exposures=(object(),),
    )

    assert report.status is PortfolioRiskStatus.FAILED
    assert (
        report.error
        == "every exposure must be a PortfolioExposure"
    )


def test_invalid_limit_returns_failed_report() -> None:
    report = assess(
        limits=(object(),),
    )

    assert report.status is PortfolioRiskStatus.FAILED
    assert (
        report.error
        == "every limit must be a PortfolioRiskLimit"
    )


def test_non_iterable_exposures_raise_type_error() -> None:
    with pytest.raises(
        TypeError,
        match="exposures must be iterable",
    ):
        PortfolioRiskEngine().assess(
            metrics=metrics(),
            exposures=None,
            limits=(),
        )


def test_non_iterable_limits_raise_type_error() -> None:
    with pytest.raises(
        TypeError,
        match="limits must be iterable",
    ):
        PortfolioRiskEngine().assess(
            metrics=metrics(),
            exposures=(),
            limits=None,
        )


def test_metrics_type_is_validated() -> None:
    with pytest.raises(
        TypeError,
        match="metrics must be PortfolioRiskMetrics",
    ):
        PortfolioRiskEngine().assess(
            metrics=object(),
            exposures=(),
            limits=(),
        )