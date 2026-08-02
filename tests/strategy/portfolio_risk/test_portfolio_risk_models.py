from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.portfolio_risk.portfolio_risk_models import (
    ExposureType,
    PortfolioExposure,
    PortfolioRiskDecision,
    PortfolioRiskLimit,
    PortfolioRiskMetrics,
    PortfolioRiskReport,
    PortfolioRiskStatus,
    RiskLimitBreach,
    RiskLimitSeverity,
    RiskLimitType,
)


def exposure() -> PortfolioExposure:
    return PortfolioExposure(
        exposure_id="position-aapl",
        name="Apple",
        exposure_type=ExposureType.POSITION,
        market_value=Decimal("20000"),
        exposure_ratio=Decimal("0.20"),
        risk_contribution=Decimal("0.15"),
    )


def warning_limit() -> PortfolioRiskLimit:
    return PortfolioRiskLimit(
        limit_id="position-limit",
        name="Maximum position exposure",
        limit_type=RiskLimitType.POSITION_EXPOSURE,
        threshold=Decimal("0.25"),
        severity=RiskLimitSeverity.WARNING,
    )


def critical_limit() -> PortfolioRiskLimit:
    return PortfolioRiskLimit(
        limit_id="leverage-limit",
        name="Maximum leverage",
        limit_type=RiskLimitType.LEVERAGE,
        threshold=Decimal("1.50"),
        severity=RiskLimitSeverity.CRITICAL,
    )


def metrics() -> PortfolioRiskMetrics:
    return PortfolioRiskMetrics(
        portfolio_value=Decimal("100000"),
        cash_value=Decimal("20000"),
        gross_exposure=Decimal("0.80"),
        net_exposure=Decimal("0.80"),
        leverage_ratio=Decimal("1.00"),
        concentration_score=Decimal("0.20"),
        diversification_score=Decimal("0.80"),
        volatility=Decimal("0.15"),
        maximum_drawdown=Decimal("0.10"),
        value_at_risk=Decimal("0.03"),
        expected_shortfall=Decimal("0.05"),
        risk_budget_used=Decimal("0.45"),
        liquidity_score=Decimal("0.90"),
    )


def approved_report() -> PortfolioRiskReport:
    return PortfolioRiskReport(
        status=PortfolioRiskStatus.COMPLETED,
        decision=PortfolioRiskDecision.APPROVE,
        metrics=metrics(),
        exposures=(exposure(),),
        limits=(
            warning_limit(),
            critical_limit(),
        ),
        recommendation=(
            "Portfolio risk remains within approved limits."
        ),
    )


def test_portfolio_exposure() -> None:
    value = exposure()

    assert value.exposure_id == "position-aapl"
    assert value.name == "Apple"
    assert value.market_value == Decimal("20000")


def test_exposure_text_is_normalized() -> None:
    value = PortfolioExposure(
        exposure_id="  position-aapl  ",
        name="  Apple  ",
        exposure_type=ExposureType.POSITION,
        market_value=Decimal("20000"),
        exposure_ratio=Decimal("0.20"),
    )

    assert value.exposure_id == "position-aapl"
    assert value.name == "Apple"


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        (
            "exposure_id",
            "exposure_id must not be empty",
        ),
        (
            "name",
            "name must not be empty",
        ),
    ],
)
def test_exposure_text_must_not_be_empty(
    field_name: str,
    message: str,
) -> None:
    arguments = {
        "exposure_id": "position-aapl",
        "name": "Apple",
        "exposure_type": ExposureType.POSITION,
        "market_value": Decimal("20000"),
        "exposure_ratio": Decimal("0.20"),
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=message,
    ):
        PortfolioExposure(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "exposure_ratio",
        "risk_contribution",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_exposure_ratios_must_be_valid(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "exposure_id": "position-aapl",
        "name": "Apple",
        "exposure_type": ExposureType.POSITION,
        "market_value": Decimal("20000"),
        "exposure_ratio": Decimal("0.20"),
        "risk_contribution": Decimal("0.15"),
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be between 0 and 1",
    ):
        PortfolioExposure(**arguments)


def test_market_value_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="market_value must not be negative",
    ):
        PortfolioExposure(
            exposure_id="position-aapl",
            name="Apple",
            exposure_type=ExposureType.POSITION,
            market_value=Decimal("-1"),
            exposure_ratio=Decimal("0"),
        )


def test_exposure_warnings_are_tuples() -> None:
    value = PortfolioExposure(
        exposure_id="position-aapl",
        name="Apple",
        exposure_type=ExposureType.POSITION,
        market_value=Decimal("20000"),
        exposure_ratio=Decimal("0.20"),
        warnings=["Exposure warning."],
    )

    assert value.warnings == (
        "Exposure warning.",
    )


def test_portfolio_risk_limit() -> None:
    value = warning_limit()

    assert value.limit_id == "position-limit"
    assert (
        value.limit_type
        is RiskLimitType.POSITION_EXPOSURE
    )
    assert value.threshold == Decimal("0.25")


def test_limit_text_is_normalized() -> None:
    value = PortfolioRiskLimit(
        limit_id="  leverage-limit  ",
        name="  Maximum leverage  ",
        limit_type=RiskLimitType.LEVERAGE,
        threshold=Decimal("1.50"),
        severity=RiskLimitSeverity.CRITICAL,
        description="  Portfolio leverage limit.  ",
    )

    assert value.limit_id == "leverage-limit"
    assert value.name == "Maximum leverage"
    assert value.description == "Portfolio leverage limit."


def test_limit_threshold_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="threshold must not be negative",
    ):
        PortfolioRiskLimit(
            limit_id="leverage-limit",
            name="Maximum leverage",
            limit_type=RiskLimitType.LEVERAGE,
            threshold=Decimal("-0.01"),
            severity=RiskLimitSeverity.CRITICAL,
        )


def test_risk_limit_breach() -> None:
    limit = critical_limit()

    value = RiskLimitBreach(
        limit=limit,
        observed_value=Decimal("1.80"),
        exceeded_by=Decimal("0.30"),
        message="Leverage exceeded.",
    )

    assert value.limit == limit
    assert value.observed_value == Decimal("1.80")
    assert value.exceeded_by == Decimal("0.30")


def test_breach_exceeded_by_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="exceeded_by must be greater than zero",
    ):
        RiskLimitBreach(
            limit=critical_limit(),
            observed_value=Decimal("1.50"),
            exceeded_by=Decimal("0"),
            message="Leverage exceeded.",
        )


def test_breach_amount_must_match_limit() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "exceeded_by must equal observed_value "
            "minus the limit threshold"
        ),
    ):
        RiskLimitBreach(
            limit=critical_limit(),
            observed_value=Decimal("1.80"),
            exceeded_by=Decimal("0.20"),
            message="Leverage exceeded.",
        )


def test_portfolio_risk_metrics() -> None:
    value = metrics()

    assert value.portfolio_value == Decimal("100000")
    assert value.leverage_ratio == Decimal("1.00")
    assert value.liquidity_score == Decimal("0.90")


def test_portfolio_value_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="portfolio_value must be greater than zero",
    ):
        PortfolioRiskMetrics(
            portfolio_value=Decimal("0"),
            cash_value=Decimal("0"),
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            leverage_ratio=Decimal("0"),
            concentration_score=Decimal("0"),
            diversification_score=Decimal("0"),
            volatility=Decimal("0"),
            maximum_drawdown=Decimal("0"),
            value_at_risk=Decimal("0"),
            expected_shortfall=Decimal("0"),
            risk_budget_used=Decimal("0"),
            liquidity_score=Decimal("0"),
        )


def test_cash_must_not_exceed_portfolio_value() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cash_value must not exceed portfolio_value"
        ),
    ):
        PortfolioRiskMetrics(
            portfolio_value=Decimal("100000"),
            cash_value=Decimal("100001"),
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            leverage_ratio=Decimal("0"),
            concentration_score=Decimal("0"),
            diversification_score=Decimal("1"),
            volatility=Decimal("0"),
            maximum_drawdown=Decimal("0"),
            value_at_risk=Decimal("0"),
            expected_shortfall=Decimal("0"),
            risk_budget_used=Decimal("0"),
            liquidity_score=Decimal("1"),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "concentration_score",
        "diversification_score",
        "risk_budget_used",
        "liquidity_score",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_normalized_metric_must_be_valid(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "portfolio_value": Decimal("100000"),
        "cash_value": Decimal("20000"),
        "gross_exposure": Decimal("0.80"),
        "net_exposure": Decimal("0.80"),
        "leverage_ratio": Decimal("1"),
        "concentration_score": Decimal("0.20"),
        "diversification_score": Decimal("0.80"),
        "volatility": Decimal("0.15"),
        "maximum_drawdown": Decimal("0.10"),
        "value_at_risk": Decimal("0.03"),
        "expected_shortfall": Decimal("0.05"),
        "risk_budget_used": Decimal("0.45"),
        "liquidity_score": Decimal("0.90"),
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be between 0 and 1",
    ):
        PortfolioRiskMetrics(**arguments)


def test_expected_shortfall_cannot_be_below_var() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expected_shortfall must not be less than "
            "value_at_risk"
        ),
    ):
        PortfolioRiskMetrics(
            portfolio_value=Decimal("100000"),
            cash_value=Decimal("20000"),
            gross_exposure=Decimal("0.80"),
            net_exposure=Decimal("0.80"),
            leverage_ratio=Decimal("1"),
            concentration_score=Decimal("0.20"),
            diversification_score=Decimal("0.80"),
            volatility=Decimal("0.15"),
            maximum_drawdown=Decimal("0.10"),
            value_at_risk=Decimal("0.05"),
            expected_shortfall=Decimal("0.03"),
            risk_budget_used=Decimal("0.45"),
            liquidity_score=Decimal("0.90"),
        )


def test_approved_portfolio_risk_report() -> None:
    value = approved_report()

    assert value.status is PortfolioRiskStatus.COMPLETED
    assert value.decision is PortfolioRiskDecision.APPROVE
    assert value.breaches == ()


def test_report_collections_are_tuples() -> None:
    value = PortfolioRiskReport(
        status=PortfolioRiskStatus.COMPLETED,
        decision=PortfolioRiskDecision.APPROVE,
        metrics=metrics(),
        exposures=[exposure()],
        limits=[
            warning_limit(),
            critical_limit(),
        ],
        recommendation="Portfolio approved.",
        warnings=["Portfolio warning."],
    )

    assert value.exposures == (exposure(),)
    assert isinstance(value.limits, tuple)
    assert value.warnings == (
        "Portfolio warning.",
    )


def test_exposure_ids_must_be_unique() -> None:
    duplicate = exposure()

    with pytest.raises(
        ValueError,
        match="exposure_id values must be unique",
    ):
        PortfolioRiskReport(
            status=PortfolioRiskStatus.COMPLETED,
            decision=PortfolioRiskDecision.APPROVE,
            metrics=metrics(),
            exposures=(duplicate, duplicate),
            recommendation="Portfolio approved.",
        )


def test_limit_ids_must_be_unique() -> None:
    duplicate = warning_limit()

    with pytest.raises(
        ValueError,
        match="limit_id values must be unique",
    ):
        PortfolioRiskReport(
            status=PortfolioRiskStatus.COMPLETED,
            decision=PortfolioRiskDecision.APPROVE,
            metrics=metrics(),
            limits=(duplicate, duplicate),
            recommendation="Portfolio approved.",
        )


def test_breach_must_reference_report_limit() -> None:
    breach = RiskLimitBreach(
        limit=critical_limit(),
        observed_value=Decimal("1.80"),
        exceeded_by=Decimal("0.30"),
        message="Leverage exceeded.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "every breach must reference a report limit"
        ),
    ):
        PortfolioRiskReport(
            status=PortfolioRiskStatus.COMPLETED,
            decision=(
                PortfolioRiskDecision.REVIEW_REQUIRED
            ),
            metrics=metrics(),
            limits=(warning_limit(),),
            breaches=(breach,),
            recommendation="Review portfolio.",
        )


def test_approved_report_cannot_include_breaches() -> None:
    limit = warning_limit()

    breach = RiskLimitBreach(
        limit=limit,
        observed_value=Decimal("0.30"),
        exceeded_by=Decimal("0.05"),
        message="Position exposure exceeded.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "approved reports must not include breaches"
        ),
    ):
        PortfolioRiskReport(
            status=PortfolioRiskStatus.COMPLETED,
            decision=PortfolioRiskDecision.APPROVE,
            metrics=metrics(),
            limits=(limit,),
            breaches=(breach,),
            recommendation="Portfolio approved.",
        )


def test_rejected_report_requires_critical_breach() -> None:
    limit = warning_limit()

    breach = RiskLimitBreach(
        limit=limit,
        observed_value=Decimal("0.30"),
        exceeded_by=Decimal("0.05"),
        message="Position exposure exceeded.",
    )

    with pytest.raises(
        ValueError,
        match=(
            "rejected reports must include a "
            "critical breach"
        ),
    ):
        PortfolioRiskReport(
            status=PortfolioRiskStatus.COMPLETED,
            decision=PortfolioRiskDecision.REJECT,
            metrics=metrics(),
            limits=(limit,),
            breaches=(breach,),
            recommendation="Portfolio rejected.",
        )


def test_completed_report_requires_recommendation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "completed reports must include a recommendation"
        ),
    ):
        PortfolioRiskReport(
            status=PortfolioRiskStatus.COMPLETED,
            decision=PortfolioRiskDecision.APPROVE,
            metrics=metrics(),
            recommendation="   ",
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        PortfolioRiskReport(
            status=PortfolioRiskStatus.FAILED,
            decision=PortfolioRiskDecision.REJECT,
            metrics=metrics(),
            recommendation="Risk assessment failed.",
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        PortfolioRiskReport(
            status=PortfolioRiskStatus.COMPLETED,
            decision=PortfolioRiskDecision.APPROVE,
            metrics=metrics(),
            recommendation="Portfolio approved.",
            error="Unexpected error.",
        )


def test_models_are_immutable() -> None:
    value = exposure()

    with pytest.raises(FrozenInstanceError):
        value.name = "Changed"