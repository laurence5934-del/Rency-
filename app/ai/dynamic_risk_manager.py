from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite, sqrt
from numbers import Real
from typing import Any, Mapping, Sequence


class RiskDecision(str, Enum):
    REJECT = "REJECT"
    REDUCE = "REDUCE"
    APPROVE = "APPROVE"
    HALT = "HALT"


class RiskMode(str, Enum):
    NORMAL = "NORMAL"
    CAUTIOUS = "CAUTIOUS"
    DEFENSIVE = "DEFENSIVE"
    CAPITAL_PRESERVATION = "CAPITAL_PRESERVATION"


@dataclass(frozen=True, slots=True)
class PortfolioRiskState:
    equity: float
    cash: float
    gross_exposure: float
    sector_exposure: float
    correlated_exposure: float
    daily_pnl: float
    weekly_pnl: float
    current_drawdown: float
    consecutive_losses: int
    open_positions: int

    def __post_init__(self) -> None:
        for name in (
            "equity",
            "cash",
            "gross_exposure",
            "sector_exposure",
            "correlated_exposure",
            "daily_pnl",
            "weekly_pnl",
            "current_drawdown",
        ):
            value = getattr(self, name)
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")
            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(f"{name} must be finite")
            object.__setattr__(self, name, numeric)

        if self.equity <= 0:
            raise ValueError("equity must be greater than zero")
        if self.cash < 0:
            raise ValueError("cash cannot be negative")
        if not 0.0 <= self.gross_exposure <= 1.0:
            raise ValueError("gross_exposure must be between 0 and 1")
        if not 0.0 <= self.sector_exposure <= 1.0:
            raise ValueError("sector_exposure must be between 0 and 1")
        if not 0.0 <= self.correlated_exposure <= 1.0:
            raise ValueError("correlated_exposure must be between 0 and 1")
        if not 0.0 <= self.current_drawdown <= 1.0:
            raise ValueError("current_drawdown must be between 0 and 1")

        for name in ("consecutive_losses", "open_positions"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} cannot be negative")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PortfolioRiskState":
        if not isinstance(data, Mapping):
            raise TypeError("data must be a mapping")
        return cls(**dict(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "equity": self.equity,
            "cash": self.cash,
            "gross_exposure": self.gross_exposure,
            "sector_exposure": self.sector_exposure,
            "correlated_exposure": self.correlated_exposure,
            "daily_pnl": self.daily_pnl,
            "weekly_pnl": self.weekly_pnl,
            "current_drawdown": self.current_drawdown,
            "consecutive_losses": self.consecutive_losses,
            "open_positions": self.open_positions,
        }


@dataclass(frozen=True, slots=True)
class TradeRiskRequest:
    symbol: str
    price: float
    atr: float
    confidence: float
    expected_reward_risk: float
    sector_weight_after_trade: float
    correlation_score: float
    requested_position_value: float
    stop_atr_multiple: float = 2.0
    use_kelly: bool = False
    win_probability: float | None = None
    payoff_ratio: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError("symbol must be a string")
        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol cannot be empty")
        object.__setattr__(self, "symbol", symbol)

        for name in (
            "price",
            "atr",
            "confidence",
            "expected_reward_risk",
            "sector_weight_after_trade",
            "correlation_score",
            "requested_position_value",
            "stop_atr_multiple",
        ):
            value = getattr(self, name)
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")
            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(f"{name} must be finite")
            object.__setattr__(self, name, numeric)

        if self.price <= 0:
            raise ValueError("price must be greater than zero")
        if self.atr <= 0:
            raise ValueError("atr must be greater than zero")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.expected_reward_risk <= 0:
            raise ValueError("expected_reward_risk must be positive")
        if not 0.0 <= self.sector_weight_after_trade <= 1.0:
            raise ValueError(
                "sector_weight_after_trade must be between 0 and 1"
            )
        if not 0.0 <= self.correlation_score <= 1.0:
            raise ValueError("correlation_score must be between 0 and 1")
        if self.requested_position_value <= 0:
            raise ValueError("requested_position_value must be positive")
        if self.stop_atr_multiple <= 0:
            raise ValueError("stop_atr_multiple must be positive")

        if not isinstance(self.use_kelly, bool):
            raise TypeError("use_kelly must be a boolean")

        if self.use_kelly:
            if self.win_probability is None or self.payoff_ratio is None:
                raise ValueError(
                    "win_probability and payoff_ratio are required "
                    "when use_kelly is True"
                )
            for name in ("win_probability", "payoff_ratio"):
                value = getattr(self, name)
                if not isinstance(value, Real) or isinstance(value, bool):
                    raise TypeError(f"{name} must be numeric")
                numeric = float(value)
                if not isfinite(numeric):
                    raise ValueError(f"{name} must be finite")
                object.__setattr__(self, name, numeric)

            if not 0.0 < self.win_probability < 1.0:
                raise ValueError(
                    "win_probability must be between 0 and 1"
                )
            if self.payoff_ratio <= 0:
                raise ValueError("payoff_ratio must be positive")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TradeRiskRequest":
        if not isinstance(data, Mapping):
            raise TypeError("data must be a mapping")
        return cls(**dict(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "atr": self.atr,
            "confidence": self.confidence,
            "expected_reward_risk": self.expected_reward_risk,
            "sector_weight_after_trade": self.sector_weight_after_trade,
            "correlation_score": self.correlation_score,
            "requested_position_value": self.requested_position_value,
            "stop_atr_multiple": self.stop_atr_multiple,
            "use_kelly": self.use_kelly,
            "win_probability": self.win_probability,
            "payoff_ratio": self.payoff_ratio,
        }


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    decision: RiskDecision
    mode: RiskMode
    approved_position_value: float
    approved_shares: int
    stop_price: float
    dollar_risk: float
    portfolio_heat_after_trade: float
    risk_score: float
    position_multiplier: float
    kill_switch: bool
    reasons: tuple[str, ...]

    @property
    def approved(self) -> bool:
        return self.decision in {
            RiskDecision.APPROVE,
            RiskDecision.REDUCE,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "mode": self.mode.value,
            "approved": self.approved,
            "approved_position_value": self.approved_position_value,
            "approved_shares": self.approved_shares,
            "stop_price": self.stop_price,
            "dollar_risk": self.dollar_risk,
            "portfolio_heat_after_trade": self.portfolio_heat_after_trade,
            "risk_score": self.risk_score,
            "position_multiplier": self.position_multiplier,
            "kill_switch": self.kill_switch,
            "reasons": list(self.reasons),
        }


class DynamicRiskManager:
    """
    Version 9.8.0.5 Dynamic Risk Manager.

    Protects capital by combining:
    - fixed fractional risk
    - ATR-based stop sizing
    - confidence scaling
    - volatility scaling
    - drawdown protection
    - daily and weekly loss limits
    - exposure limits
    - sector and correlation checks
    - consecutive-loss protection
    - optional fractional Kelly sizing
    - emergency kill-switch logic
    """

    def __init__(
        self,
        *,
        risk_per_trade: float = 0.01,
        max_position_weight: float = 0.10,
        max_gross_exposure: float = 0.80,
        max_sector_exposure: float = 0.30,
        max_correlated_exposure: float = 0.35,
        max_daily_loss: float = 0.03,
        max_weekly_loss: float = 0.06,
        max_drawdown: float = 0.15,
        caution_drawdown: float = 0.07,
        defensive_drawdown: float = 0.10,
        max_consecutive_losses: int = 5,
        max_open_positions: int = 12,
        minimum_reward_risk: float = 1.5,
        maximum_portfolio_heat: float = 0.08,
        kelly_fraction: float = 0.25,
    ) -> None:
        for name in (
            "risk_per_trade",
            "max_position_weight",
            "max_gross_exposure",
            "max_sector_exposure",
            "max_correlated_exposure",
            "max_daily_loss",
            "max_weekly_loss",
            "max_drawdown",
            "caution_drawdown",
            "defensive_drawdown",
            "maximum_portfolio_heat",
            "kelly_fraction",
        ):
            value = locals()[name]
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric")
            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(f"{name} must be finite")
            if not 0.0 < numeric <= 1.0:
                raise ValueError(f"{name} must be in (0, 1]")
            setattr(self, name, numeric)

        if not (
            self.caution_drawdown
            < self.defensive_drawdown
            < self.max_drawdown
        ):
            raise ValueError(
                "drawdown thresholds must satisfy "
                "caution < defensive < maximum"
            )

        for name in ("max_consecutive_losses", "max_open_positions"):
            value = locals()[name]
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")
            if value < 1:
                raise ValueError(f"{name} must be at least 1")
            setattr(self, name, value)

        if (
            not isinstance(minimum_reward_risk, Real)
            or isinstance(minimum_reward_risk, bool)
        ):
            raise TypeError("minimum_reward_risk must be numeric")
        self.minimum_reward_risk = float(minimum_reward_risk)
        if not isfinite(self.minimum_reward_risk):
            raise ValueError("minimum_reward_risk must be finite")
        if self.minimum_reward_risk <= 0:
            raise ValueError("minimum_reward_risk must be positive")

        self._last_assessment: RiskAssessment | None = None

    @property
    def last_assessment(self) -> RiskAssessment | None:
        return self._last_assessment

    def _risk_mode(self, state: PortfolioRiskState) -> RiskMode:
        if state.current_drawdown >= self.max_drawdown:
            return RiskMode.CAPITAL_PRESERVATION
        if state.current_drawdown >= self.defensive_drawdown:
            return RiskMode.DEFENSIVE
        if state.current_drawdown >= self.caution_drawdown:
            return RiskMode.CAUTIOUS
        return RiskMode.NORMAL

    def _kill_switch_reasons(
        self,
        state: PortfolioRiskState,
    ) -> list[str]:
        reasons: list[str] = []

        if state.daily_pnl <= -(state.equity * self.max_daily_loss):
            reasons.append("Maximum daily loss reached")
        if state.weekly_pnl <= -(state.equity * self.max_weekly_loss):
            reasons.append("Maximum weekly loss reached")
        if state.current_drawdown >= self.max_drawdown:
            reasons.append("Maximum portfolio drawdown reached")
        if state.consecutive_losses >= self.max_consecutive_losses:
            reasons.append("Maximum consecutive losses reached")

        return reasons

    @staticmethod
    def _kelly_fraction(
        win_probability: float,
        payoff_ratio: float,
    ) -> float:
        loss_probability = 1.0 - win_probability
        raw = (
            win_probability
            - (loss_probability / payoff_ratio)
        )
        return max(0.0, raw)

    def assess(
        self,
        state: PortfolioRiskState | Mapping[str, Any],
        request: TradeRiskRequest | Mapping[str, Any],
        *,
        current_portfolio_heat: float = 0.0,
    ) -> RiskAssessment:
        if isinstance(state, Mapping):
            state = PortfolioRiskState.from_mapping(state)
        if isinstance(request, Mapping):
            request = TradeRiskRequest.from_mapping(request)

        if not isinstance(state, PortfolioRiskState):
            raise TypeError(
                "state must be PortfolioRiskState or mapping"
            )
        if not isinstance(request, TradeRiskRequest):
            raise TypeError(
                "request must be TradeRiskRequest or mapping"
            )

        if (
            not isinstance(current_portfolio_heat, Real)
            or isinstance(current_portfolio_heat, bool)
        ):
            raise TypeError("current_portfolio_heat must be numeric")
        current_portfolio_heat = float(current_portfolio_heat)
        if not isfinite(current_portfolio_heat):
            raise ValueError("current_portfolio_heat must be finite")
        if not 0.0 <= current_portfolio_heat <= 1.0:
            raise ValueError(
                "current_portfolio_heat must be between 0 and 1"
            )

        reasons: list[str] = []
        mode = self._risk_mode(state)
        kill_reasons = self._kill_switch_reasons(state)

        if kill_reasons:
            assessment = RiskAssessment(
                decision=RiskDecision.HALT,
                mode=RiskMode.CAPITAL_PRESERVATION,
                approved_position_value=0.0,
                approved_shares=0,
                stop_price=round(
                    max(
                        0.0,
                        request.price
                        - request.atr * request.stop_atr_multiple,
                    ),
                    8,
                ),
                dollar_risk=0.0,
                portfolio_heat_after_trade=current_portfolio_heat,
                risk_score=0.0,
                position_multiplier=0.0,
                kill_switch=True,
                reasons=tuple(kill_reasons),
            )
            self._last_assessment = assessment
            return assessment

        if request.expected_reward_risk < self.minimum_reward_risk:
            reasons.append(
                "Expected reward-to-risk is below the minimum"
            )

        if state.open_positions >= self.max_open_positions:
            reasons.append("Maximum open positions reached")

        if state.gross_exposure >= self.max_gross_exposure:
            reasons.append("Maximum gross exposure reached")

        if (
            request.sector_weight_after_trade
            > self.max_sector_exposure
        ):
            reasons.append("Sector exposure limit would be exceeded")

        if request.correlation_score > self.max_correlated_exposure:
            reasons.append(
                "Correlation exposure limit would be exceeded"
            )

        hard_reject = bool(reasons)

        stop_distance = request.atr * request.stop_atr_multiple
        stop_price = max(0.0, request.price - stop_distance)

        base_risk_budget = state.equity * self.risk_per_trade

        mode_multiplier = {
            RiskMode.NORMAL: 1.00,
            RiskMode.CAUTIOUS: 0.70,
            RiskMode.DEFENSIVE: 0.40,
            RiskMode.CAPITAL_PRESERVATION: 0.00,
        }[mode]

        confidence_multiplier = 0.25 + 0.75 * request.confidence
        volatility_ratio = request.atr / request.price
        volatility_multiplier = 1.0 / (1.0 + 8.0 * volatility_ratio)
        volatility_multiplier = max(0.25, min(1.0, volatility_multiplier))

        position_multiplier = (
            mode_multiplier
            * confidence_multiplier
            * volatility_multiplier
        )

        if state.consecutive_losses > 0:
            streak_multiplier = max(
                0.35,
                1.0 - 0.10 * state.consecutive_losses,
            )
            position_multiplier *= streak_multiplier
            reasons.append(
                "Position reduced due to consecutive losses"
            )

        if request.use_kelly:
            kelly = self._kelly_fraction(
                request.win_probability,
                request.payoff_ratio,
            )
            kelly_multiplier = min(
                1.0,
                kelly * self.kelly_fraction
                / max(self.risk_per_trade, 1e-12),
            )
            position_multiplier *= kelly_multiplier
            reasons.append(
                f"Fractional Kelly multiplier applied: "
                f"{kelly_multiplier:.3f}"
            )

        adjusted_risk_budget = base_risk_budget * position_multiplier
        atr_sized_value = (
            adjusted_risk_budget
            / stop_distance
            * request.price
        )

        max_position_value = state.equity * self.max_position_weight
        exposure_capacity = max(
            0.0,
            state.equity
            * (self.max_gross_exposure - state.gross_exposure),
        )

        approved_value = min(
            request.requested_position_value,
            atr_sized_value,
            max_position_value,
            exposure_capacity,
            state.cash,
        )

        dollar_risk = (
            approved_value / request.price * stop_distance
            if approved_value > 0
            else 0.0
        )
        heat_after = current_portfolio_heat + (
            dollar_risk / state.equity
        )

        if heat_after > self.maximum_portfolio_heat:
            available_heat = max(
                0.0,
                self.maximum_portfolio_heat - current_portfolio_heat,
            )
            heat_limited_risk = state.equity * available_heat
            heat_limited_value = (
                heat_limited_risk / stop_distance * request.price
                if stop_distance > 0
                else 0.0
            )
            approved_value = min(approved_value, heat_limited_value)
            dollar_risk = (
                approved_value / request.price * stop_distance
                if approved_value > 0
                else 0.0
            )
            heat_after = current_portfolio_heat + (
                dollar_risk / state.equity
            )
            reasons.append("Portfolio heat limit reduced position size")

        if hard_reject or approved_value <= 0.0:
            decision = RiskDecision.REJECT
            approved_value = 0.0
            dollar_risk = 0.0
            heat_after = current_portfolio_heat
            position_multiplier = 0.0
        elif approved_value < request.requested_position_value * 0.999:
            decision = RiskDecision.REDUCE
            reasons.append(
                "Requested position reduced to satisfy risk limits"
            )
        else:
            decision = RiskDecision.APPROVE
            reasons.append("Trade satisfies configured risk limits")

        approved_shares = int(approved_value // request.price)

        risk_score = 100.0
        risk_score -= state.current_drawdown * 250.0
        risk_score -= state.gross_exposure * 25.0
        risk_score -= request.correlation_score * 20.0
        risk_score -= request.sector_weight_after_trade * 15.0
        risk_score += request.confidence * 15.0
        risk_score += min(request.expected_reward_risk, 3.0) * 5.0
        risk_score = max(0.0, min(100.0, risk_score))

        assessment = RiskAssessment(
            decision=decision,
            mode=mode,
            approved_position_value=round(approved_value, 8),
            approved_shares=approved_shares,
            stop_price=round(stop_price, 8),
            dollar_risk=round(dollar_risk, 8),
            portfolio_heat_after_trade=round(heat_after, 12),
            risk_score=round(risk_score, 6),
            position_multiplier=round(position_multiplier, 12),
            kill_switch=False,
            reasons=tuple(reasons),
        )

        self._last_assessment = assessment
        return assessment

    def scale_out_targets(
        self,
        *,
        entry_price: Real,
        stop_price: Real,
        reward_multiples: Sequence[Real] = (1.0, 2.0, 3.0),
    ) -> tuple[float, ...]:
        entry = float(entry_price)
        stop = float(stop_price)

        if not isfinite(entry) or not isfinite(stop):
            raise ValueError("entry_price and stop_price must be finite")
        if entry <= 0 or stop < 0 or stop >= entry:
            raise ValueError(
                "require entry_price > stop_price >= 0"
            )

        risk_per_share = entry - stop
        targets: list[float] = []

        for multiple in reward_multiples:
            if not isinstance(multiple, Real) or isinstance(multiple, bool):
                raise TypeError("reward multiples must be numeric")
            value = float(multiple)
            if not isfinite(value) or value <= 0:
                raise ValueError(
                    "reward multiples must be finite and positive"
                )
            targets.append(round(entry + risk_per_share * value, 8))

        return tuple(targets)

    def trailing_stop(
        self,
        *,
        highest_price: Real,
        atr: Real,
        atr_multiple: Real = 2.0,
    ) -> float:
        highest = float(highest_price)
        atr_value = float(atr)
        multiple = float(atr_multiple)

        if not all(isfinite(v) for v in (highest, atr_value, multiple)):
            raise ValueError("trailing stop inputs must be finite")
        if highest <= 0 or atr_value <= 0 or multiple <= 0:
            raise ValueError(
                "trailing stop inputs must be positive"
            )

        return round(max(0.0, highest - atr_value * multiple), 8)

    def reset(self) -> None:
        self._last_assessment = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_per_trade": self.risk_per_trade,
            "max_position_weight": self.max_position_weight,
            "max_gross_exposure": self.max_gross_exposure,
            "max_sector_exposure": self.max_sector_exposure,
            "max_correlated_exposure": self.max_correlated_exposure,
            "max_daily_loss": self.max_daily_loss,
            "max_weekly_loss": self.max_weekly_loss,
            "max_drawdown": self.max_drawdown,
            "caution_drawdown": self.caution_drawdown,
            "defensive_drawdown": self.defensive_drawdown,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_open_positions": self.max_open_positions,
            "minimum_reward_risk": self.minimum_reward_risk,
            "maximum_portfolio_heat": self.maximum_portfolio_heat,
            "kelly_fraction": self.kelly_fraction,
            "last_assessment": (
                self._last_assessment.to_dict()
                if self._last_assessment is not None
                else None
            ),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"risk_per_trade={self.risk_per_trade}, "
            f"max_position_weight={self.max_position_weight}, "
            f"max_gross_exposure={self.max_gross_exposure})"
        )
