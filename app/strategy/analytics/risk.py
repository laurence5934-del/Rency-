from decimal import Decimal

from .risk_models import RiskMetrics


class RiskAnalyzer:
    """Calculates portfolio risk metrics."""

    def analyze(self, result) -> RiskMetrics:
        snapshots = sorted(result.snapshots, key=lambda s: s.timestamp)

        if not snapshots:
            return RiskMetrics(
                max_drawdown=Decimal("0"),
                drawdown_duration=0,
            )

        peak = snapshots[0].equity
        max_drawdown = Decimal("0")

        for snapshot in snapshots:
            if snapshot.equity > peak:
                peak = snapshot.equity

            if peak > 0:
                drawdown = (peak - snapshot.equity) / peak

                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        return RiskMetrics(
            max_drawdown=max_drawdown,
            drawdown_duration=0,
        )