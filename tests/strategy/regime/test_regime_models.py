from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.regime.regime_models import (
    MarketRegime,
    MarketRegimeReport,
    MarketRegimeSignal,
    RegimeConfidence,
    RegimeDetectionStatus,
)


def signal() -> MarketRegimeSignal:
    return MarketRegimeSignal(
        signal_id="market-001",
        trend_score=Decimal("0.85"),
        volatility_score=Decimal("0.25"),
        breadth_score=Decimal("0.80"),
        momentum_score=Decimal("0.82"),
        liquidity_score=Decimal("0.90"),
    )


def report() -> MarketRegimeReport:
    return MarketRegimeReport(
        status=RegimeDetectionStatus.COMPLETED,
        regime=MarketRegime.STRONG_BULL,
        confidence=RegimeConfidence.VERY_HIGH,
        overall_score=Decimal("0.84"),
        signal=signal(),
        recommendation=(
            "Favor trend-following and growth strategies."
        ),
    )


def test_market_regime_signal() -> None:
    value = signal()

    assert value.signal_id == "market-001"
    assert value.trend_score == Decimal("0.85")
    assert value.liquidity_score == Decimal("0.90")


def test_signal_id_is_normalized() -> None:
    value = MarketRegimeSignal(
        signal_id="  market-001  ",
        trend_score=Decimal("0.50"),
        volatility_score=Decimal("0.50"),
        breadth_score=Decimal("0.50"),
        momentum_score=Decimal("0.50"),
        liquidity_score=Decimal("0.50"),
    )

    assert value.signal_id == "market-001"


def test_signal_id_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="signal_id must not be empty",
    ):
        MarketRegimeSignal(
            signal_id="   ",
            trend_score=Decimal("0.50"),
            volatility_score=Decimal("0.50"),
            breadth_score=Decimal("0.50"),
            momentum_score=Decimal("0.50"),
            liquidity_score=Decimal("0.50"),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "trend_score",
        "volatility_score",
        "breadth_score",
        "momentum_score",
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
def test_signal_scores_must_be_between_zero_and_one(
    field_name: str,
    value: Decimal,
) -> None:
    arguments = {
        "signal_id": "market-001",
        "trend_score": Decimal("0.50"),
        "volatility_score": Decimal("0.50"),
        "breadth_score": Decimal("0.50"),
        "momentum_score": Decimal("0.50"),
        "liquidity_score": Decimal("0.50"),
    }

    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=(
            f"{field_name} must be between 0 and 1"
        ),
    ):
        MarketRegimeSignal(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "trend_score",
        "volatility_score",
        "breadth_score",
        "momentum_score",
        "liquidity_score",
    ],
)
def test_signal_scores_must_be_decimal(
    field_name: str,
) -> None:
    arguments = {
        "signal_id": "market-001",
        "trend_score": Decimal("0.50"),
        "volatility_score": Decimal("0.50"),
        "breadth_score": Decimal("0.50"),
        "momentum_score": Decimal("0.50"),
        "liquidity_score": Decimal("0.50"),
    }

    arguments[field_name] = 0.50

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        MarketRegimeSignal(**arguments)


def test_signal_warnings_are_converted_to_tuple() -> None:
    value = MarketRegimeSignal(
        signal_id="market-001",
        trend_score=Decimal("0.50"),
        volatility_score=Decimal("0.50"),
        breadth_score=Decimal("0.50"),
        momentum_score=Decimal("0.50"),
        liquidity_score=Decimal("0.50"),
        warnings=["Mixed breadth signal."],
    )

    assert value.warnings == (
        "Mixed breadth signal.",
    )


def test_market_regime_report() -> None:
    value = report()

    assert (
        value.status
        is RegimeDetectionStatus.COMPLETED
    )
    assert value.regime is MarketRegime.STRONG_BULL
    assert (
        value.confidence
        is RegimeConfidence.VERY_HIGH
    )
    assert value.overall_score == Decimal("0.84")
    assert value.signal == signal()


def test_recommendation_is_normalized() -> None:
    value = MarketRegimeReport(
        status=RegimeDetectionStatus.COMPLETED,
        regime=MarketRegime.BULL,
        confidence=RegimeConfidence.HIGH,
        overall_score=Decimal("0.75"),
        signal=signal(),
        recommendation="  Favor growth strategies.  ",
    )

    assert (
        value.recommendation
        == "Favor growth strategies."
    )


def test_recommendation_must_not_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="recommendation must not be empty",
    ):
        MarketRegimeReport(
            status=RegimeDetectionStatus.COMPLETED,
            regime=MarketRegime.UNKNOWN,
            confidence=RegimeConfidence.LOW,
            overall_score=Decimal("0.50"),
            signal=None,
            recommendation="   ",
        )


@pytest.mark.parametrize(
    "score",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_overall_score_must_be_valid(
    score: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="overall_score must be between 0 and 1",
    ):
        MarketRegimeReport(
            status=RegimeDetectionStatus.COMPLETED,
            regime=MarketRegime.UNKNOWN,
            confidence=RegimeConfidence.LOW,
            overall_score=score,
            signal=None,
            recommendation="Insufficient evidence.",
        )


def test_overall_score_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="overall_score must be a Decimal",
    ):
        MarketRegimeReport(
            status=RegimeDetectionStatus.COMPLETED,
            regime=MarketRegime.UNKNOWN,
            confidence=RegimeConfidence.LOW,
            overall_score=0.50,
            signal=None,
            recommendation="Insufficient evidence.",
        )


def test_signal_must_be_valid_type() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "signal must be a MarketRegimeSignal "
            "or None"
        ),
    ):
        MarketRegimeReport(
            status=RegimeDetectionStatus.COMPLETED,
            regime=MarketRegime.UNKNOWN,
            confidence=RegimeConfidence.LOW,
            overall_score=Decimal("0.50"),
            signal=object(),
            recommendation="Insufficient evidence.",
        )


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        MarketRegimeReport(
            status=RegimeDetectionStatus.FAILED,
            regime=MarketRegime.UNKNOWN,
            confidence=RegimeConfidence.LOW,
            overall_score=Decimal("0"),
            signal=None,
            recommendation="Detection failed.",
        )


def test_completed_report_cannot_include_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        MarketRegimeReport(
            status=RegimeDetectionStatus.COMPLETED,
            regime=MarketRegime.UNKNOWN,
            confidence=RegimeConfidence.LOW,
            overall_score=Decimal("0"),
            signal=None,
            recommendation="Detection completed.",
            error="Unexpected failure.",
        )


def test_failed_report_normalizes_error() -> None:
    value = MarketRegimeReport(
        status=RegimeDetectionStatus.FAILED,
        regime=MarketRegime.UNKNOWN,
        confidence=RegimeConfidence.LOW,
        overall_score=Decimal("0"),
        signal=None,
        recommendation="Detection failed.",
        error="  invalid signal  ",
    )

    assert value.error == "invalid signal"


def test_report_warnings_are_converted_to_tuple() -> None:
    value = MarketRegimeReport(
        status=RegimeDetectionStatus.COMPLETED,
        regime=MarketRegime.SIDEWAYS,
        confidence=RegimeConfidence.MEDIUM,
        overall_score=Decimal("0.50"),
        signal=signal(),
        recommendation="Use range-based strategies.",
        warnings=["Signals are mixed."],
    )

    assert value.warnings == (
        "Signals are mixed.",
    )


def test_models_are_immutable() -> None:
    value = signal()

    with pytest.raises(FrozenInstanceError):
        value.signal_id = "changed"