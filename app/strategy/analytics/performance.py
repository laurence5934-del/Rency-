from decimal import Decimal, localcontext

from .performance_models import PerformanceMetrics
from .returns import ReturnAnalyzer
from .risk import RiskAnalyzer


class PerformanceAnalyzer:
    """Calculates risk-adjusted portfolio performance."""

    @staticmethod
    def _calculate_realized_pnl_changes(
        snapshots,
    ) -> list[Decimal]:
        ordered = sorted(
            snapshots,
            key=lambda snapshot: snapshot.timestamp,
        )

        return [
            current.realized_pnl - previous.realized_pnl
            for previous, current in zip(ordered, ordered[1:])
        ]

    @staticmethod
    def _calculate_profit_factor(
        pnl_changes: list[Decimal],
    ) -> Decimal:
        gross_profit = sum(
            (
                pnl
                for pnl in pnl_changes
                if pnl > 0
            ),
            Decimal("0"),
        )

        gross_loss = abs(
            sum(
                (
                    pnl
                    for pnl in pnl_changes
                    if pnl < 0
                ),
                Decimal("0"),
            )
        )

        if gross_loss == 0:
            return Decimal("0")

        return gross_profit / gross_loss

    @staticmethod
    def _calculate_win_rate(
        pnl_changes: list[Decimal],
    ) -> Decimal:
        winning_periods = sum(
            1
            for pnl in pnl_changes
            if pnl > 0
        )

        losing_periods = sum(
            1
            for pnl in pnl_changes
            if pnl < 0
        )

        closed_periods = winning_periods + losing_periods

        if closed_periods == 0:
            return Decimal("0")

        return (
            Decimal(winning_periods)
            / Decimal(closed_periods)
            * Decimal("100")
        )

    @staticmethod
    def _calculate_calmar_ratio(
        cagr: Decimal,
        maximum_drawdown: Decimal,
    ) -> Decimal:
        if maximum_drawdown == 0:
            return Decimal("0")

        return cagr / abs(maximum_drawdown)

    @staticmethod
    def _calculate_returns(
        snapshots,
    ) -> list[Decimal]:
        ordered = sorted(
            snapshots,
            key=lambda snapshot: snapshot.timestamp,
        )

        returns: list[Decimal] = []

        for previous, current in zip(ordered, ordered[1:]):
            if previous.equity == 0:
                continue

            period_return = (
                current.equity - previous.equity
            ) / previous.equity

            returns.append(period_return)

        return returns

    @staticmethod
    def _calculate_sample_volatility(
        returns: list[Decimal],
    ) -> Decimal:
        if len(returns) < 2:
            return Decimal("0")

        mean_return = (
            sum(returns, Decimal("0"))
            / Decimal(len(returns))
        )

        squared_deviations = [
            (period_return - mean_return) ** 2
            for period_return in returns
        ]

        sample_variance = (
            sum(squared_deviations, Decimal("0"))
            / Decimal(len(returns) - 1)
        )

        with localcontext() as context:
            context.prec = 28
            return sample_variance.sqrt()

    @staticmethod
    def _calculate_downside_deviation(
        returns: list[Decimal],
    ) -> Decimal:
        downside_returns = [
            period_return
            for period_return in returns
            if period_return < 0
        ]

        if len(downside_returns) < 2:
            return Decimal("0")

        mean_downside_return = (
            sum(downside_returns, Decimal("0"))
            / Decimal(len(downside_returns))
        )

        squared_deviations = [
            (period_return - mean_downside_return) ** 2
            for period_return in downside_returns
        ]

        sample_variance = (
            sum(squared_deviations, Decimal("0"))
            / Decimal(len(downside_returns) - 1)
        )

        with localcontext() as context:
            context.prec = 28
            return sample_variance.sqrt()

    def analyze(self, result) -> PerformanceMetrics:
        returns = self._calculate_returns(result.snapshots)

        return_metrics = ReturnAnalyzer().analyze(result)
        risk_metrics = RiskAnalyzer().analyze(result)

        calmar_ratio = self._calculate_calmar_ratio(
            return_metrics.cagr,
            risk_metrics.max_drawdown,
        )

        pnl_changes = self._calculate_realized_pnl_changes(
            result.snapshots
        )

        profit_factor = self._calculate_profit_factor(
            pnl_changes
        )

        win_rate = self._calculate_win_rate(
            pnl_changes
        )

        if len(returns) < 2:
            return PerformanceMetrics(
                sharpe_ratio=Decimal("0"),
                sortino_ratio=Decimal("0"),
                calmar_ratio=calmar_ratio,
                profit_factor=profit_factor,
                win_rate=win_rate,
            )

        mean_return = (
            sum(returns, Decimal("0"))
            / Decimal(len(returns))
        )

        volatility = self._calculate_sample_volatility(
            returns
        )

        if volatility == 0:
            sharpe_ratio = Decimal("0")
        else:
            sharpe_ratio = mean_return / volatility

        downside_deviation = self._calculate_downside_deviation(
            returns
        )

        if downside_deviation == 0:
            sortino_ratio = Decimal("0")
        else:
            sortino_ratio = mean_return / downside_deviation

        return PerformanceMetrics(
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            profit_factor=profit_factor,
            win_rate=win_rate,
        )