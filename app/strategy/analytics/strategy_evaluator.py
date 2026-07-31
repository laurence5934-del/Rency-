from __future__ import annotations

from decimal import Decimal

from .models import AnalyticsReport
from .strategy_evaluation_models import StrategyEvaluation


_ZERO = Decimal("0")

_SHARPE_TARGET = Decimal("1.5")
_SORTINO_TARGET = Decimal("2")
_PROFIT_FACTOR_TARGET = Decimal("1.5")
_MAX_DRAWDOWN_TARGET = Decimal("0.10")
_SQN_TARGET = Decimal("2")
_RECOVERY_FACTOR_TARGET = Decimal("3")
_MAX_KELLY_TARGET = Decimal("0.25")


class StrategyEvaluator:
    """Interprets an analytics report and evaluates strategy quality."""

    def evaluate(
        self,
        report: AnalyticsReport,
    ) -> StrategyEvaluation:
        """Return a structured evaluation of a trading strategy."""

        score = self._compute_score(report)
        grade = self._grade(score)

        return StrategyEvaluation(
            score=score,
            grade=grade,
            recommendation=self._recommendation(grade),
            strengths=self._strengths(report),
            concerns=self._concerns(report),
        )

    def _compute_score(
        self,
        report: AnalyticsReport,
    ) -> int:
        score = 0

        if (
            report.performance.sharpe_ratio
            >= _SHARPE_TARGET
        ):
            score += 20

        if (
            report.performance.sortino_ratio
            >= _SORTINO_TARGET
        ):
            score += 15

        if (
            report.performance.profit_factor
            >= _PROFIT_FACTOR_TARGET
        ):
            score += 15

        if (
            _ZERO
            <= report.risk.max_drawdown
            <= _MAX_DRAWDOWN_TARGET
        ):
            score += 15

        if (
            report.strategy_quality.system_quality_number
            >= _SQN_TARGET
        ):
            score += 15

        if (
            report.expectancy.recovery_factor
            >= _RECOVERY_FACTOR_TARGET
        ):
            score += 10

        kelly_criterion = (
            report.strategy_quality.kelly_criterion
        )

        if (
            _ZERO
            <= kelly_criterion
            <= _MAX_KELLY_TARGET
        ):
            score += 10

        return min(max(score, 0), 100)

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "A"

        if score >= 80:
            return "B"

        if score >= 70:
            return "C"

        if score >= 60:
            return "D"

        return "F"

    @staticmethod
    def _recommendation(grade: str) -> str:
        recommendations = {
            "A": "READY_FOR_LIVE_TRADING",
            "B": "READY_FOR_PAPER_TRADING",
            "C": "NEEDS_OPTIMIZATION",
            "D": "DO_NOT_DEPLOY",
            "F": "DO_NOT_DEPLOY",
        }

        return recommendations[grade]

    def _strengths(
        self,
        report: AnalyticsReport,
    ) -> tuple[str, ...]:
        strengths: list[str] = []

        if (
            report.performance.sharpe_ratio
            >= _SHARPE_TARGET
        ):
            strengths.append(
                "Sharpe ratio meets or exceeds target"
            )

        if (
            report.performance.sortino_ratio
            >= _SORTINO_TARGET
        ):
            strengths.append(
                "Sortino ratio meets or exceeds target"
            )

        if (
            report.performance.profit_factor
            >= _PROFIT_FACTOR_TARGET
        ):
            strengths.append(
                "Profit factor indicates favorable trade efficiency"
            )

        if (
            _ZERO
            <= report.risk.max_drawdown
            <= _MAX_DRAWDOWN_TARGET
        ):
            strengths.append(
                "Maximum drawdown is within tolerance"
            )

        if (
            report.strategy_quality.system_quality_number
            >= _SQN_TARGET
        ):
            strengths.append(
                "System Quality Number indicates a strong strategy"
            )

        if (
            report.expectancy.recovery_factor
            >= _RECOVERY_FACTOR_TARGET
        ):
            strengths.append(
                "Recovery factor meets or exceeds target"
            )

        kelly_criterion = (
            report.strategy_quality.kelly_criterion
        )

        if (
            _ZERO
            <= kelly_criterion
            <= _MAX_KELLY_TARGET
        ):
            strengths.append(
                "Kelly criterion is within conservative limits"
            )

        return tuple(strengths)

    def _concerns(
        self,
        report: AnalyticsReport,
    ) -> tuple[str, ...]:
        concerns: list[str] = []

        if (
            report.performance.sharpe_ratio
            < _SHARPE_TARGET
        ):
            concerns.append(
                "Sharpe ratio is below target"
            )

        if (
            report.performance.sortino_ratio
            < _SORTINO_TARGET
        ):
            concerns.append(
                "Sortino ratio is below target"
            )

        if (
            report.performance.profit_factor
            < _PROFIT_FACTOR_TARGET
        ):
            concerns.append(
                "Profit factor is below target"
            )

        if (
            report.risk.max_drawdown
            > _MAX_DRAWDOWN_TARGET
        ):
            concerns.append(
                "Maximum drawdown exceeds tolerance"
            )

        if report.risk.max_drawdown < _ZERO:
            concerns.append(
                "Maximum drawdown cannot be negative"
            )

        if (
            report.strategy_quality.system_quality_number
            < _SQN_TARGET
        ):
            concerns.append(
                "System Quality Number is below target"
            )

        if (
            report.expectancy.recovery_factor
            < _RECOVERY_FACTOR_TARGET
        ):
            concerns.append(
                "Recovery factor is below target"
            )

        kelly_criterion = (
            report.strategy_quality.kelly_criterion
        )

        if kelly_criterion > _MAX_KELLY_TARGET:
            concerns.append(
                "Kelly criterion indicates aggressive position sizing"
            )

        if kelly_criterion < _ZERO:
            concerns.append(
                "Kelly criterion is negative"
            )

        if report.expectancy.expectancy <= _ZERO:
            concerns.append(
                "Trade expectancy is not positive"
            )

        return tuple(concerns)