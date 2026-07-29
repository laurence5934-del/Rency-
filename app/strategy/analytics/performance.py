from decimal import Decimal, localcontext

from .performance_models import PerformanceMetrics


class PerformanceAnalyzer:
    """Calculates risk-adjusted portfolio performance."""

def analyze(self, result) -> PerformanceMetrics:
        return PerformanceMetrics(
            sharpe_ratio=Decimal("0")
        )

        from decimal import Decimal, localcontext

from .performance_models import PerformanceMetrics


class PerformanceAnalyzer:
    """Calculates risk-adjusted portfolio performance."""

    @staticmethod
    def _calculate_returns(snapshots) -> list[Decimal]:
        ordered = sorted(snapshots, key=lambda snapshot: snapshot.timestamp)

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

    def analyze(self, result) -> PerformanceMetrics:
        returns = self._calculate_returns(result.snapshots)

        if len(returns) < 2:
            return PerformanceMetrics(
                sharpe_ratio=Decimal("0"),
            )

        mean_return = (
            sum(returns, Decimal("0"))
            / Decimal(len(returns))
        )

        volatility = self._calculate_sample_volatility(returns)

        if volatility == 0:
            return PerformanceMetrics(
                sharpe_ratio=Decimal("0"),
            )

        sharpe_ratio = mean_return / volatility

        return PerformanceMetrics(
            sharpe_ratio=sharpe_ratio,
        )