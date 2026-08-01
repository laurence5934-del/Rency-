from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.strategy.monte_carlo.monte_carlo_models import (
    MonteCarloPathResult,
    MonteCarloReport,
    MonteCarloStatus,
)


def path_result() -> MonteCarloPathResult:
    return MonteCarloPathResult(
        path_id=1,
        final_equity=Decimal("120000"),
        total_return=Decimal("0.20"),
        max_drawdown=Decimal("0.10"),
        ruined=False,
    )


def test_path_result() -> None:
    result = path_result()

    assert result.path_id == 1
    assert result.final_equity == Decimal("120000")
    assert result.ruined is False


def test_path_id_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="path_id must be greater than zero",
    ):
        MonteCarloPathResult(
            path_id=0,
            final_equity=Decimal("100000"),
            total_return=Decimal("0"),
            max_drawdown=Decimal("0"),
        )


@pytest.mark.parametrize(
    "drawdown",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_path_drawdown_must_be_between_zero_and_one(
    drawdown: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_drawdown must be between 0 and 1",
    ):
        MonteCarloPathResult(
            path_id=1,
            final_equity=Decimal("100000"),
            total_return=Decimal("0"),
            max_drawdown=drawdown,
        )


def test_report_normalizes_collections() -> None:
    report = MonteCarloReport(
        status=MonteCarloStatus.COMPLETED,
        paths=[path_result()],
        ruin_probability=Decimal("0.05"),
        median_final_equity=Decimal("120000"),
        percentile_05_final_equity=Decimal("90000"),
        percentile_95_final_equity=Decimal("150000"),
        median_max_drawdown=Decimal("0.12"),
        warnings=["Low tail equity."],
    )

    assert report.paths == (path_result(),)
    assert report.warnings == ("Low tail equity.",)


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        MonteCarloReport(
            status=MonteCarloStatus.FAILED,
        )


def test_completed_report_cannot_have_error() -> None:
    with pytest.raises(
        ValueError,
        match="only failed reports may include an error",
    ):
        MonteCarloReport(
            status=MonteCarloStatus.COMPLETED,
            error="Unexpected failure.",
        )


@pytest.mark.parametrize(
    "probability",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_ruin_probability_must_be_valid(
    probability: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="ruin_probability must be between 0 and 1",
    ):
        MonteCarloReport(
            status=MonteCarloStatus.COMPLETED,
            ruin_probability=probability,
        )


def test_report_is_immutable() -> None:
    report = MonteCarloReport(
        status=MonteCarloStatus.COMPLETED,
    )

    with pytest.raises(FrozenInstanceError):
        report.ruin_probability = Decimal("0.50")