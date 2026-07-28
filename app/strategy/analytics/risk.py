from decimal import Decimal, localcontext

from .risk_models import RiskMetrics


class RiskAnalyzer:
    """Calculates portfolio risk metrics."""

    @staticmethod
    def _calculate_volatility(snapshots) -> Decimal:
        if len(snapshots) < 3:
            return Decimal("0")

        returns: list[Decimal] = []

        for previous, current in zip(snapshots, snapshots[1:]):
            if previous.equity == 0:
                continue

            period_return = (
                current.equity - previous.equity
            ) / previous.equity

            returns.append(period_return)

        if len(returns) < 2:
            return Decimal("0")

        mean_return = sum(returns, Decimal("0")) / Decimal(len(returns))

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

    def analyze(self, result) -> RiskMetrics:
        snapshots = sorted(result.snapshots, key=lambda s: s.timestamp)

        if not snapshots:
            return RiskMetrics(
                max_drawdown=Decimal("0"),
                drawdown_duration=0,
                volatility=Decimal("0"),
            )

        peak = snapshots[0].equity
        max_drawdown = Decimal("0")

        current_duration = 0
        max_duration = 0

        for snapshot in snapshots:
            if snapshot.equity >= peak:
                peak = snapshot.equity
                current_duration = 0
            else:
                current_duration += 1
                max_duration = max(max_duration, current_duration)

            if peak > 0:
                drawdown = (peak - snapshot.equity) / peak

                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        volatility = self._calculate_volatility(snapshots)

        return RiskMetrics(
            max_drawdown=max_drawdown,
            drawdown_duration=max_duration,
            volatility=volatility,
        )