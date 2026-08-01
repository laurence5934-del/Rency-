from decimal import Decimal

import pytest

from app.strategy.monte_carlo.monte_carlo_engine import (
    MonteCarloEngine,
)
from app.strategy.monte_carlo.monte_carlo_models import (
    MonteCarloStatus,
)


RETURNS = (
    Decimal("0.10"),
    Decimal("-0.05"),
    Decimal("0.08"),
    Decimal("-0.03"),
    Decimal("0.04"),
)


def test_run_completes_requested_simulations() -> None:
    report = MonteCarloEngine().run(
        trade_returns=RETURNS,
        initial_capital=Decimal("100000"),
        simulations=100,
        seed=42,
    )

    assert report.status is MonteCarloStatus.COMPLETED
    assert len(report.paths) == 100
    assert report.error is None


def test_path_ids_are_sequential() -> None:
    report = MonteCarloEngine().run(
        trade_returns=RETURNS,
        initial_capital=Decimal("100000"),
        simulations=3,
        seed=42,
    )

    assert tuple(
        path.path_id
        for path in report.paths
    ) == (
        1,
        2,
        3,
    )


def test_same_seed_produces_identical_results() -> None:
    engine = MonteCarloEngine()

    first = engine.run(
        trade_returns=RETURNS,
        initial_capital=Decimal("100000"),
        simulations=100,
        seed=42,
    )
    second = engine.run(
        trade_returns=RETURNS,
        initial_capital=Decimal("100000"),
        simulations=100,
        seed=42,
    )

    assert first == second


def test_different_seeds_produce_different_paths() -> None:
    engine = MonteCarloEngine()

    first = engine.run(
        trade_returns=RETURNS,
        initial_capital=Decimal("100000"),
        simulations=25,
        seed=1,
    )
    second = engine.run(
        trade_returns=RETURNS,
        initial_capital=Decimal("100000"),
        simulations=25,
        seed=2,
    )

    assert first.paths != second.paths


def test_positive_returns_increase_equity() -> None:
    report = MonteCarloEngine().run(
        trade_returns=(
            Decimal("0.10"),
        ),
        initial_capital=Decimal("100000"),
        simulations=1,
        seed=42,
    )

    path = report.paths[0]

    assert path.final_equity == Decimal("110000.00")
    assert path.total_return == Decimal("0.10")
    assert path.max_drawdown == Decimal("0")
    assert path.ruined is False


def test_total_loss_reaches_zero_equity() -> None:
    report = MonteCarloEngine().run(
        trade_returns=(
            Decimal("-1"),
        ),
        initial_capital=Decimal("100000"),
        simulations=1,
        seed=42,
    )

    path = report.paths[0]

    assert path.final_equity == Decimal("0")
    assert path.total_return == Decimal("-1")
    assert path.max_drawdown == Decimal("1")
    assert path.ruined is True


def test_ruin_probability_is_calculated() -> None:
    report = MonteCarloEngine().run(
        trade_returns=(
            Decimal("-1"),
        ),
        initial_capital=Decimal("100000"),
        simulations=10,
        seed=42,
    )

    assert report.ruin_probability == Decimal("1")
    assert report.warnings == (
        "One or more simulation paths reached the ruin threshold.",
    )


def test_no_ruined_paths_have_zero_probability() -> None:
    report = MonteCarloEngine().run(
        trade_returns=(
            Decimal("0.01"),
        ),
        initial_capital=Decimal("100000"),
        simulations=10,
        seed=42,
    )

    assert report.ruin_probability == Decimal("0")
    assert report.warnings == ()


def test_report_percentiles_are_ordered() -> None:
    report = MonteCarloEngine().run(
        trade_returns=RETURNS,
        initial_capital=Decimal("100000"),
        simulations=500,
        seed=42,
    )

    assert (
        report.percentile_05_final_equity
        <= report.median_final_equity
        <= report.percentile_95_final_equity
    )


def test_median_drawdown_is_valid() -> None:
    report = MonteCarloEngine().run(
        trade_returns=RETURNS,
        initial_capital=Decimal("100000"),
        simulations=100,
        seed=42,
    )

    assert (
        Decimal("0")
        <= report.median_max_drawdown
        <= Decimal("1")
    )


def test_empty_returns_produce_completed_report() -> None:
    report = MonteCarloEngine().run(
        trade_returns=(),
        initial_capital=Decimal("100000"),
        simulations=100,
        seed=42,
    )

    assert report.status is MonteCarloStatus.COMPLETED
    assert report.paths == ()
    assert report.ruin_probability == Decimal("0")
    assert report.median_final_equity == Decimal("100000")
    assert report.percentile_05_final_equity == Decimal(
        "100000"
    )
    assert report.percentile_95_final_equity == Decimal(
        "100000"
    )
    assert report.warnings == (
        "No trade returns were supplied.",
    )


def test_median_for_odd_number_of_values() -> None:
    result = MonteCarloEngine._median(
        (
            Decimal("3"),
            Decimal("1"),
            Decimal("2"),
        )
    )

    assert result == Decimal("2")


def test_median_for_even_number_of_values() -> None:
    result = MonteCarloEngine._median(
        (
            Decimal("4"),
            Decimal("1"),
            Decimal("3"),
            Decimal("2"),
        )
    )

    assert result == Decimal("2.5")


def test_percentile_with_one_value() -> None:
    result = MonteCarloEngine._percentile(
        (Decimal("100"),),
        Decimal("0.95"),
    )

    assert result == Decimal("100")


def test_percentile_uses_linear_interpolation() -> None:
    result = MonteCarloEngine._percentile(
        (
            Decimal("0"),
            Decimal("100"),
        ),
        Decimal("0.25"),
    )

    assert result == Decimal("25.00")


@pytest.mark.parametrize(
    "initial_capital",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_initial_capital_must_be_positive(
    initial_capital: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be greater than zero",
    ):
        MonteCarloEngine().run(
            trade_returns=RETURNS,
            initial_capital=initial_capital,
            simulations=10,
        )


def test_initial_capital_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="initial_capital must be a Decimal",
    ):
        MonteCarloEngine().run(
            trade_returns=RETURNS,
            initial_capital=100000,
            simulations=10,
        )


@pytest.mark.parametrize(
    "simulations",
    [
        0,
        -1,
    ],
)
def test_simulations_must_be_positive(
    simulations: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="simulations must be greater than zero",
    ):
        MonteCarloEngine().run(
            trade_returns=RETURNS,
            initial_capital=Decimal("100000"),
            simulations=simulations,
        )


def test_simulations_must_be_integer() -> None:
    with pytest.raises(
        TypeError,
        match="simulations must be an integer",
    ):
        MonteCarloEngine().run(
            trade_returns=RETURNS,
            initial_capital=Decimal("100000"),
            simulations=Decimal("10"),
        )


def test_seed_must_be_integer() -> None:
    with pytest.raises(
        TypeError,
        match="seed must be an integer",
    ):
        MonteCarloEngine().run(
            trade_returns=RETURNS,
            initial_capital=Decimal("100000"),
            simulations=10,
            seed="42",
        )


@pytest.mark.parametrize(
    "ruin_threshold",
    [
        Decimal("-0.01"),
        Decimal("1.01"),
    ],
)
def test_ruin_threshold_must_be_valid(
    ruin_threshold: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="ruin_threshold must be between 0 and 1",
    ):
        MonteCarloEngine().run(
            trade_returns=RETURNS,
            initial_capital=Decimal("100000"),
            simulations=10,
            ruin_threshold=ruin_threshold,
        )


def test_ruin_threshold_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="ruin_threshold must be a Decimal",
    ):
        MonteCarloEngine().run(
            trade_returns=RETURNS,
            initial_capital=Decimal("100000"),
            simulations=10,
            ruin_threshold=0.50,
        )


def test_trade_returns_must_be_decimal() -> None:
    with pytest.raises(
        TypeError,
        match="every trade return must be a Decimal",
    ):
        MonteCarloEngine().run(
            trade_returns=(
                Decimal("0.10"),
                -0.05,
            ),
            initial_capital=Decimal("100000"),
            simulations=10,
        )


def test_trade_return_cannot_be_less_than_negative_one() -> None:
    with pytest.raises(
        ValueError,
        match="must not be less than -1",
    ):
        MonteCarloEngine().run(
            trade_returns=(
                Decimal("-1.01"),
            ),
            initial_capital=Decimal("100000"),
            simulations=10,
        )