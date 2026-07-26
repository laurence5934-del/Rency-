from __future__ import annotations

from dataclasses import dataclass, field, asdict
from statistics import mean
from typing import Any


@dataclass(slots=True)
class TradeOutcome:
    strategy: str
    market_regime: str
    symbol: str
    confidence: float
    expected_return: float
    actual_return: float
    risk_score: float
    won: bool

    @property
    def prediction_error(self) -> float:
        return self.actual_return - self.expected_return


@dataclass(slots=True)
class StrategyMetrics:
    trades: int = 0
    wins: int = 0
    total_return: float = 0.0
    confidence: list[float] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades if self.trades else 0.0

    @property
    def average_return(self) -> float:
        return self.total_return / self.trades if self.trades else 0.0

    @property
    def average_confidence(self) -> float:
        return mean(self.confidence) if self.confidence else 0.0


class LearningFramework:
    """
    Version 9.8.0.9

    Continuous self-evaluation framework.
    """

    def __init__(self) -> None:
        self._history: list[TradeOutcome] = []
        self._strategies: dict[str, StrategyMetrics] = {}
        self._regimes: dict[str, StrategyMetrics] = {}

    def record(self, outcome: TradeOutcome) -> None:
        self._history.append(outcome)

        sm = self._strategies.setdefault(
            outcome.strategy,
            StrategyMetrics(),
        )
        sm.trades += 1
        sm.total_return += outcome.actual_return
        sm.confidence.append(outcome.confidence)
        if outcome.won:
            sm.wins += 1

        key = f"{outcome.market_regime}:{outcome.strategy}"
        rm = self._regimes.setdefault(key, StrategyMetrics())
        rm.trades += 1
        rm.total_return += outcome.actual_return
        rm.confidence.append(outcome.confidence)
        if outcome.won:
            rm.wins += 1

    def confidence_bias(self) -> float:
        if not self._history:
            return 0.0
        predicted = mean(x.confidence for x in self._history)
        actual = mean(1.0 if x.won else 0.0 for x in self._history)
        return round(predicted - actual, 6)

    def calibration_recommendation(self) -> str:
        bias = self.confidence_bias()
        if abs(bias) < 0.03:
            return "Confidence is well calibrated."
        if bias > 0:
            return (
                f"Reduce confidence estimates by about {bias:.1%}."
            )
        return (
            f"Increase confidence estimates by about {abs(bias):.1%}."
        )

    def strategy_rankings(self) -> list[dict[str, Any]]:
        rows = []
        for name, m in self._strategies.items():
            score = (
                m.win_rate * 0.5 +
                m.average_return * 0.3 +
                m.average_confidence * 0.2
            )
            rows.append({
                "strategy": name,
                "score": round(score, 6),
                "win_rate": round(m.win_rate, 6),
                "average_return": round(m.average_return, 6),
                "average_confidence": round(m.average_confidence, 6),
                "trades": m.trades,
            })
        rows.sort(key=lambda x: x["score"], reverse=True)
        return rows

    def regime_rankings(self) -> list[dict[str, Any]]:
        rows = []
        for key, m in self._regimes.items():
            rows.append({
                "regime_strategy": key,
                "win_rate": round(m.win_rate, 6),
                "average_return": round(m.average_return, 6),
                "trades": m.trades,
            })
        rows.sort(key=lambda x: x["win_rate"], reverse=True)
        return rows

    def recommendations(self) -> list[str]:
        rec = [self.calibration_recommendation()]
        ranking = self.strategy_rankings()
        if ranking:
            rec.append(
                f"Highest ranked strategy: {ranking[0]['strategy']}."
            )
            rec.append(
                f"Lowest ranked strategy: {ranking[-1]['strategy']}."
            )
        if self._history:
            avg_error = mean(
                t.prediction_error for t in self._history
            )
            if avg_error < -0.02:
                rec.append(
                    "Expected returns are consistently optimistic."
                )
            elif avg_error > 0.02:
                rec.append(
                    "Expected returns are consistently conservative."
                )
        return rec

    def summary(self) -> dict[str, Any]:
        return {
            "trades": len(self._history),
            "confidence_bias": self.confidence_bias(),
            "strategy_rankings": self.strategy_rankings(),
            "regime_rankings": self.regime_rankings(),
            "recommendations": self.recommendations(),
        }

    def reset(self) -> None:
        self._history.clear()
        self._strategies.clear()
        self._regimes.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "history": [asdict(h) for h in self._history],
            "summary": self.summary(),
        }
