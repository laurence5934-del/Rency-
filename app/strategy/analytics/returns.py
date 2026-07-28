from __future__ import annotations

from decimal import Decimal
from math import isfinite
from typing import Iterable

from app.strategy.backtesting.models import (
    BacktestResult,
    PortfolioSnapshot,
)

from .models import ReturnMetrics


_ZERO = Decimal("0")
_DAYS_PER_YEAR = Decimal("365.2425")


class ReturnAnalyzer:
    """Calculate deterministic portfolio-return analytics."""

    def analyze(self, result: BacktestResult) -> ReturnMetrics:
        snapshots = self._ordered_snapshots(result.snapshots)
        warnings: list[str] = []

        initial_capital = result.config.initial_capital

        if snapshots:
            final_equity = snapshots[-1].equity
        else:
            final_equity = self._metric_decimal(
                result,
                "final_equity",
                default=initial_capital,
            )
            warnings.append(
                "Backtest result contains no portfolio snapshots."
            )

        net_profit = final_equity - initial_capital

        if initial_capital == _ZERO:
            total_return = _ZERO
            warnings.append(
                "Total return cannot be calculated from zero initial capital."
            )
        else:
            total_return = net_profit / initial_capital

        periodic_returns, periodic_warnings = self._periodic_returns(
            snapshots
        )
        warnings.extend(periodic_warnings)

        cagr = self._calculate_cagr(
            initial_capital=initial_capital,
            final_equity=final_equity,
            start_time=result.config.start_time,
            end_time=result.config.end_time,
            warnings=warnings,
        )

        return ReturnMetrics(
            initial_capital=initial_capital,
            final_equity=final_equity,
            net_profit=net_profit,
            total_return=total_return,
            annualized_return=cagr,
            cagr=cagr,
            periodic_returns=periodic_returns,
            warnings=warnings,
        )

    @staticmethod
    def _ordered_snapshots(
        snapshots: Iterable[PortfolioSnapshot],
    ) -> tuple[PortfolioSnapshot, ...]:
        return tuple(
            sorted(
                snapshots,
                key=lambda snapshot: snapshot.timestamp,
            )
        )

    @staticmethod
    def _periodic_returns(
        snapshots: tuple[PortfolioSnapshot, ...],
    ) -> tuple[tuple[Decimal, ...], tuple[str, ...]]:
        if len(snapshots) < 2:
            return (), ()

        returns: list[Decimal] = []
        warnings: list[str] = []

        for previous, current in zip(
            snapshots,
            snapshots[1:],
            strict=False,
        ):
            if previous.equity == _ZERO:
                warnings.append(
                    "A periodic return was skipped because the previous "
                    "snapshot equity was zero."
                )
                continue

            period_return = (
                current.equity - previous.equity
            ) / previous.equity

            returns.append(period_return)

        return tuple(returns), tuple(warnings)

    @staticmethod
    def _calculate_cagr(
        *,
        initial_capital: Decimal,
        final_equity: Decimal,
        start_time: object,
        end_time: object,
        warnings: list[str],
    ) -> Decimal:
        duration = end_time - start_time
        elapsed_days = Decimal(str(duration.total_seconds())) / Decimal(
            "86400"
        )

        if elapsed_days <= _ZERO:
            warnings.append(
                "CAGR cannot be calculated for a non-positive duration."
            )
            return _ZERO

        if initial_capital <= _ZERO:
            warnings.append(
                "CAGR requires positive initial capital."
            )
            return _ZERO

        if final_equity <= _ZERO:
            warnings.append(
                "CAGR requires positive final equity."
            )
            return _ZERO

        elapsed_years = elapsed_days / _DAYS_PER_YEAR

        growth_ratio = float(final_equity / initial_capital)
        years = float(elapsed_years)

        calculated = growth_ratio ** (1.0 / years) - 1.0

        if not isfinite(calculated):
            warnings.append(
                "CAGR calculation produced a non-finite result."
            )
            return _ZERO

        return Decimal(str(calculated))

    @staticmethod
    def _metric_decimal(
        result: BacktestResult,
        key: str,
        *,
        default: Decimal,
    ) -> Decimal:
        value = result.metrics.get(key)

        if value is None:
            return default

        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return default