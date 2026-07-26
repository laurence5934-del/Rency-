from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from numbers import Real
from typing import Any, Iterable, Mapping


class DecisionAction(str, Enum):
    """Supported AI decision actions."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class StrategyVote:
    """One strategy vote supplied to the AI decision engine."""

    strategy_name: str
    action: DecisionAction | str
    confidence: float
    weight: float = 1.0
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.strategy_name, str):
            raise TypeError("strategy_name must be a string")

        strategy_name = self.strategy_name.strip()
        if not strategy_name:
            raise ValueError("strategy_name cannot be empty")

        action = self.action
        if isinstance(action, str):
            try:
                action = DecisionAction(action.strip().upper())
            except ValueError as exc:
                raise ValueError(
                    "action must be BUY, SELL, or HOLD"
                ) from exc
        elif not isinstance(action, DecisionAction):
            raise TypeError(
                "action must be a DecisionAction or string"
            )

        for name, value in (
            ("confidence", self.confidence),
            ("weight", self.weight),
        ):
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if float(self.weight) <= 0.0:
            raise ValueError("weight must be greater than zero")

        if not isinstance(self.reason, str):
            raise TypeError("reason must be a string")

        object.__setattr__(self, "strategy_name", strategy_name)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "weight", float(self.weight))
        object.__setattr__(self, "reason", self.reason.strip())

    @property
    def weighted_confidence(self) -> float:
        return self.confidence * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "action": self.action.value,
            "confidence": self.confidence,
            "weight": self.weight,
            "weighted_confidence": self.weighted_confidence,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AIDecision:
    """Final decision produced from a collection of strategy votes."""

    symbol: str
    action: DecisionAction
    confidence: float
    buy_score: float
    sell_score: float
    hold_score: float
    vote_count: int
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError("symbol must be a string")

        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol cannot be empty")

        if not isinstance(self.action, DecisionAction):
            raise TypeError("action must be a DecisionAction")

        for name, value in (
            ("confidence", self.confidence),
            ("buy_score", self.buy_score),
            ("sell_score", self.sell_score),
            ("hold_score", self.hold_score),
        ):
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if not isinstance(self.vote_count, int) or isinstance(
            self.vote_count,
            bool,
        ):
            raise TypeError("vote_count must be an integer")

        if self.vote_count < 0:
            raise ValueError("vote_count cannot be negative")

        if not isinstance(self.explanation, str):
            raise TypeError("explanation must be a string")

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "buy_score", float(self.buy_score))
        object.__setattr__(self, "sell_score", float(self.sell_score))
        object.__setattr__(self, "hold_score", float(self.hold_score))
        object.__setattr__(self, "explanation", self.explanation.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "confidence": self.confidence,
            "buy_score": self.buy_score,
            "sell_score": self.sell_score,
            "hold_score": self.hold_score,
            "vote_count": self.vote_count,
            "explanation": self.explanation,
        }


class AIDecisionEngine:
    """
    Combine weighted strategy votes into one BUY, SELL, or HOLD decision.

    Version 9.8.0 provides the AI decision foundation:
    - weighted strategy voting
    - confidence thresholds
    - minimum vote requirements
    - directional margin protection
    - optional market-regime multipliers
    - detailed decision explanations
    """

    def __init__(
        self,
        *,
        minimum_confidence: float = 0.55,
        minimum_votes: int = 1,
        directional_margin: float = 0.05,
        hold_bias: float = 1.0,
    ) -> None:
        for name, value in (
            ("minimum_confidence", minimum_confidence),
            ("directional_margin", directional_margin),
            ("hold_bias", hold_bias),
        ):
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")

        if not 0.0 <= float(minimum_confidence) <= 1.0:
            raise ValueError(
                "minimum_confidence must be between 0 and 1"
            )

        if not isinstance(minimum_votes, int) or isinstance(
            minimum_votes,
            bool,
        ):
            raise TypeError("minimum_votes must be an integer")

        if minimum_votes < 0:
            raise ValueError("minimum_votes cannot be negative")

        if not 0.0 <= float(directional_margin) <= 1.0:
            raise ValueError(
                "directional_margin must be between 0 and 1"
            )

        if float(hold_bias) <= 0.0:
            raise ValueError("hold_bias must be greater than zero")

        self._minimum_confidence = float(minimum_confidence)
        self._minimum_votes = minimum_votes
        self._directional_margin = float(directional_margin)
        self._hold_bias = float(hold_bias)
        self._last_decision: AIDecision | None = None

    @property
    def minimum_confidence(self) -> float:
        return self._minimum_confidence

    @property
    def minimum_votes(self) -> int:
        return self._minimum_votes

    @property
    def directional_margin(self) -> float:
        return self._directional_margin

    @property
    def hold_bias(self) -> float:
        return self._hold_bias

    @property
    def last_decision(self) -> AIDecision | None:
        return self._last_decision

    @staticmethod
    def _normalize_regime_multipliers(
        multipliers: Mapping[str | DecisionAction, Real] | None,
    ) -> dict[DecisionAction, float]:
        normalized = {
            DecisionAction.BUY: 1.0,
            DecisionAction.SELL: 1.0,
            DecisionAction.HOLD: 1.0,
        }

        if multipliers is None:
            return normalized

        if not isinstance(multipliers, Mapping):
            raise TypeError("regime_multipliers must be a mapping")

        for raw_action, raw_value in multipliers.items():
            if isinstance(raw_action, DecisionAction):
                action = raw_action
            elif isinstance(raw_action, str):
                try:
                    action = DecisionAction(raw_action.strip().upper())
                except ValueError as exc:
                    raise ValueError(
                        f"unknown regime action: {raw_action}"
                    ) from exc
            else:
                raise TypeError(
                    "regime multiplier keys must be strings "
                    "or DecisionAction values"
                )

            if not isinstance(raw_value, Real) or isinstance(
                raw_value,
                bool,
            ):
                raise TypeError(
                    "regime multiplier values must be numeric"
                )

            value = float(raw_value)
            if value < 0.0:
                raise ValueError(
                    "regime multiplier values cannot be negative"
                )

            normalized[action] = value

        return normalized

    def _score_votes(
        self,
        votes: Iterable[StrategyVote],
        multipliers: Mapping[DecisionAction, float],
    ) -> dict[DecisionAction, float]:
        scores = {
            DecisionAction.BUY: 0.0,
            DecisionAction.SELL: 0.0,
            DecisionAction.HOLD: 0.0,
        }

        for vote in votes:
            score = vote.weighted_confidence
            score *= multipliers[vote.action]

            if vote.action is DecisionAction.HOLD:
                score *= self._hold_bias

            scores[vote.action] += score

        return scores

    @staticmethod
    def _normalized_confidence(
        selected_score: float,
        total_score: float,
    ) -> float:
        if total_score <= 0.0:
            return 0.0

        return min(1.0, max(0.0, selected_score / total_score))

    def decide(
        self,
        symbol: str,
        votes: Iterable[StrategyVote],
        *,
        regime_multipliers: Mapping[
            str | DecisionAction,
            Real,
        ]
        | None = None,
    ) -> AIDecision:
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a string")

        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol cannot be empty")

        if isinstance(votes, (str, bytes)):
            raise TypeError(
                "votes must be an iterable of StrategyVote"
            )

        vote_list = list(votes)

        if any(not isinstance(vote, StrategyVote) for vote in vote_list):
            raise TypeError(
                "all votes must be StrategyVote instances"
            )

        multipliers = self._normalize_regime_multipliers(
            regime_multipliers
        )
        scores = self._score_votes(vote_list, multipliers)

        buy_score = scores[DecisionAction.BUY]
        sell_score = scores[DecisionAction.SELL]
        hold_score = scores[DecisionAction.HOLD]
        total_score = buy_score + sell_score + hold_score

        action = DecisionAction.HOLD
        selected_score = hold_score
        explanation = "No actionable directional consensus."

        if len(vote_list) < self._minimum_votes:
            explanation = (
                f"Insufficient votes: {len(vote_list)} received, "
                f"{self._minimum_votes} required."
            )
        else:
            directional_action = (
                DecisionAction.BUY
                if buy_score > sell_score
                else DecisionAction.SELL
            )
            directional_score = max(buy_score, sell_score)
            opposite_score = min(buy_score, sell_score)

            directional_confidence = self._normalized_confidence(
                directional_score,
                total_score,
            )
            directional_difference = (
                directional_score - opposite_score
            )
            directional_margin = (
                directional_difference / total_score
                if total_score > 0.0
                else 0.0
            )

            if hold_score >= directional_score:
                explanation = (
                    "HOLD score is greater than or equal to "
                    "the strongest directional score."
                )
            elif directional_confidence < self._minimum_confidence:
                explanation = (
                    f"Directional confidence "
                    f"{directional_confidence:.4f} is below "
                    f"the required threshold "
                    f"{self._minimum_confidence:.4f}."
                )
            elif directional_margin < self._directional_margin:
                explanation = (
                    f"Directional margin {directional_margin:.4f} "
                    f"is below the required margin "
                    f"{self._directional_margin:.4f}."
                )
            else:
                action = directional_action
                selected_score = directional_score
                explanation = (
                    f"{action.value} selected from weighted "
                    f"strategy consensus."
                )

        confidence = self._normalized_confidence(
            selected_score,
            total_score,
        )

        decision = AIDecision(
            symbol=normalized_symbol,
            action=action,
            confidence=confidence,
            buy_score=buy_score,
            sell_score=sell_score,
            hold_score=hold_score,
            vote_count=len(vote_list),
            explanation=explanation,
        )

        self._last_decision = decision
        return decision

    def decide_from_mappings(
        self,
        symbol: str,
        vote_data: Iterable[Mapping[str, Any]],
        *,
        regime_multipliers: Mapping[
            str | DecisionAction,
            Real,
        ]
        | None = None,
    ) -> AIDecision:
        if isinstance(vote_data, (str, bytes)):
            raise TypeError(
                "vote_data must be an iterable of mappings"
            )

        votes: list[StrategyVote] = []

        for item in vote_data:
            if not isinstance(item, Mapping):
                raise TypeError(
                    "all vote_data items must be mappings"
                )

            votes.append(
                StrategyVote(
                    strategy_name=item["strategy_name"],
                    action=item["action"],
                    confidence=item["confidence"],
                    weight=item.get("weight", 1.0),
                    reason=item.get("reason", ""),
                )
            )

        return self.decide(
            symbol,
            votes,
            regime_multipliers=regime_multipliers,
        )

    def reset(self) -> None:
        self._last_decision = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimum_confidence": self._minimum_confidence,
            "minimum_votes": self._minimum_votes,
            "directional_margin": self._directional_margin,
            "hold_bias": self._hold_bias,
            "last_decision": (
                self._last_decision.to_dict()
                if self._last_decision is not None
                else None
            ),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"minimum_confidence={self._minimum_confidence}, "
            f"minimum_votes={self._minimum_votes}, "
            f"directional_margin={self._directional_margin})"
        )
