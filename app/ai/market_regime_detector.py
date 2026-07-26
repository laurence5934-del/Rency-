from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from numbers import Real
from typing import Any, Mapping


class TrendState(str, Enum):
    STRONG_BULL = "STRONG_BULL"
    BULL = "BULL"
    SIDEWAYS = "SIDEWAYS"
    BEAR = "BEAR"
    STRONG_BEAR = "STRONG_BEAR"
    UNKNOWN = "UNKNOWN"


class VolatilityState(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"
    UNKNOWN = "UNKNOWN"


class RiskState(str, Enum):
    RISK_ON = "RISK_ON"
    NEUTRAL = "NEUTRAL"
    RISK_OFF = "RISK_OFF"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class MarketIndicators:
    price: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_21: float | None = None
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    adx: float | None = None
    atr: float | None = None
    volume: float | None = None
    average_volume: float | None = None
    vix: float | None = None

    def __post_init__(self) -> None:
        non_negative = {
            "price", "sma_20", "sma_50", "sma_200", "ema_21",
            "adx", "atr", "volume", "average_volume", "vix",
        }
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(f"{name} must be numeric or None")
            value = float(value)
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
            if name in non_negative and value < 0:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        if self.rsi is not None and not 0 <= self.rsi <= 100:
            raise ValueError("rsi must be between 0 and 100")
        if self.adx is not None and not 0 <= self.adx <= 100:
            raise ValueError("adx must be between 0 and 100")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MarketIndicators":
        if not isinstance(data, Mapping):
            raise TypeError("data must be a mapping")
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown indicator fields: {sorted(unknown)}")
        return cls(**dict(data))

    def available_count(self) -> int:
        return sum(getattr(self, name) is not None for name in self.__dataclass_fields__)

    def to_dict(self) -> dict[str, float | None]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class MarketRegime:
    trend: TrendState
    volatility: VolatilityState
    risk: RiskState
    confidence: float
    trend_score: float
    volatility_score: float
    reasons: tuple[str, ...]
    indicators_used: int

    @property
    def is_tradeable_trend(self) -> bool:
        return self.trend in {
            TrendState.STRONG_BULL, TrendState.BULL,
            TrendState.BEAR, TrendState.STRONG_BEAR,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "trend": self.trend.value,
            "volatility": self.volatility.value,
            "risk": self.risk.value,
            "confidence": self.confidence,
            "trend_score": self.trend_score,
            "volatility_score": self.volatility_score,
            "reasons": list(self.reasons),
            "indicators_used": self.indicators_used,
            "is_tradeable_trend": self.is_tradeable_trend,
        }


class MarketRegimeDetector:
    """Explainable rule-based detector for version 9.8.0.2."""

    def __init__(
        self,
        *,
        strong_trend_threshold: float = 0.65,
        trend_threshold: float = 0.25,
        low_volatility_atr_percent: float = 1.0,
        high_volatility_atr_percent: float = 3.0,
        extreme_volatility_atr_percent: float = 5.0,
        high_vix_threshold: float = 25.0,
        extreme_vix_threshold: float = 35.0,
        minimum_indicators: int = 3,
    ) -> None:
        if not 0 < trend_threshold < strong_trend_threshold <= 1:
            raise ValueError("trend thresholds are invalid")
        if not 0 <= low_volatility_atr_percent < high_volatility_atr_percent < extreme_volatility_atr_percent:
            raise ValueError("ATR volatility thresholds must be ascending")
        if not 0 < high_vix_threshold < extreme_vix_threshold:
            raise ValueError("VIX thresholds must be ascending")
        if not isinstance(minimum_indicators, int) or isinstance(minimum_indicators, bool):
            raise TypeError("minimum_indicators must be an integer")
        if minimum_indicators < 1:
            raise ValueError("minimum_indicators must be at least 1")

        self.strong_trend_threshold = float(strong_trend_threshold)
        self.trend_threshold = float(trend_threshold)
        self.low_volatility_atr_percent = float(low_volatility_atr_percent)
        self.high_volatility_atr_percent = float(high_volatility_atr_percent)
        self.extreme_volatility_atr_percent = float(extreme_volatility_atr_percent)
        self.high_vix_threshold = float(high_vix_threshold)
        self.extreme_vix_threshold = float(extreme_vix_threshold)
        self.minimum_indicators = minimum_indicators
        self._last_regime: MarketRegime | None = None

    @property
    def last_regime(self) -> MarketRegime | None:
        return self._last_regime

    @staticmethod
    def _clip(value: float, low: float, high: float) -> float:
        return min(high, max(low, value))

    def _trend_score(self, d: MarketIndicators) -> tuple[float, list[str]]:
        points = 0.0
        weight = 0.0
        reasons: list[str] = []

        def add(value: float, w: float, reason: str) -> None:
            nonlocal points, weight
            points += value * w
            weight += w
            reasons.append(reason)

        if d.price is not None and d.sma_200 is not None:
            add(1 if d.price > d.sma_200 else -1 if d.price < d.sma_200 else 0, 1.5,
                "Price is above SMA 200" if d.price > d.sma_200 else "Price is below SMA 200" if d.price < d.sma_200 else "Price equals SMA 200")
        if d.sma_50 is not None and d.sma_200 is not None:
            add(1 if d.sma_50 > d.sma_200 else -1 if d.sma_50 < d.sma_200 else 0, 1.5,
                "SMA 50 is above SMA 200" if d.sma_50 > d.sma_200 else "SMA 50 is below SMA 200" if d.sma_50 < d.sma_200 else "SMA 50 equals SMA 200")
        if d.sma_20 is not None and d.sma_50 is not None:
            add(0.8 if d.sma_20 > d.sma_50 else -0.8 if d.sma_20 < d.sma_50 else 0, 1.0,
                "SMA 20 is above SMA 50" if d.sma_20 > d.sma_50 else "SMA 20 is below SMA 50" if d.sma_20 < d.sma_50 else "SMA 20 equals SMA 50")
        if d.price is not None and d.ema_21 is not None:
            add(0.6 if d.price > d.ema_21 else -0.6 if d.price < d.ema_21 else 0, 0.75,
                "Price is above EMA 21" if d.price > d.ema_21 else "Price is below EMA 21" if d.price < d.ema_21 else "Price equals EMA 21")
        if d.macd is not None and d.macd_signal is not None:
            add(0.7 if d.macd > d.macd_signal else -0.7 if d.macd < d.macd_signal else 0, 1.0,
                "MACD is bullish" if d.macd > d.macd_signal else "MACD is bearish" if d.macd < d.macd_signal else "MACD is neutral")
        if d.rsi is not None:
            add(0.5 if d.rsi >= 60 else -0.5 if d.rsi <= 40 else 0, 0.75,
                f"RSI is {d.rsi:.1f}")

        score = points / weight if weight else 0.0
        if d.adx is not None:
            score *= min(1.25, d.adx / 25) if d.adx >= 25 else 0.75
            reasons.append(f"ADX is {d.adx:.1f}")
        return self._clip(score, -1.0, 1.0), reasons

    def _volatility(self, d: MarketIndicators) -> tuple[VolatilityState, float, list[str]]:
        scores: list[float] = []
        reasons: list[str] = []
        if d.atr is not None and d.price:
            pct = d.atr / d.price * 100
            if pct >= self.extreme_volatility_atr_percent:
                scores.append(1.0); reasons.append(f"ATR volatility is extreme at {pct:.2f}%")
            elif pct >= self.high_volatility_atr_percent:
                scores.append(0.75); reasons.append(f"ATR volatility is high at {pct:.2f}%")
            elif pct <= self.low_volatility_atr_percent:
                scores.append(0.2); reasons.append(f"ATR volatility is low at {pct:.2f}%")
            else:
                scores.append(0.45); reasons.append(f"ATR volatility is normal at {pct:.2f}%")
        if d.vix is not None:
            if d.vix >= self.extreme_vix_threshold:
                scores.append(1.0); reasons.append(f"VIX is extreme at {d.vix:.1f}")
            elif d.vix >= self.high_vix_threshold:
                scores.append(0.75); reasons.append(f"VIX is high at {d.vix:.1f}")
            elif d.vix <= 15:
                scores.append(0.2); reasons.append(f"VIX is low at {d.vix:.1f}")
            else:
                scores.append(0.45); reasons.append(f"VIX is normal at {d.vix:.1f}")
        if not scores:
            return VolatilityState.UNKNOWN, 0.0, reasons
        score = sum(scores) / len(scores)
        state = VolatilityState.EXTREME if score >= 0.9 else VolatilityState.HIGH if score >= 0.65 else VolatilityState.LOW if score <= 0.3 else VolatilityState.NORMAL
        return state, score, reasons

    def _classify_trend(self, score: float) -> TrendState:
        if score >= self.strong_trend_threshold:
            return TrendState.STRONG_BULL
        if score >= self.trend_threshold:
            return TrendState.BULL
        if score <= -self.strong_trend_threshold:
            return TrendState.STRONG_BEAR
        if score <= -self.trend_threshold:
            return TrendState.BEAR
        return TrendState.SIDEWAYS

    @staticmethod
    def _classify_risk(trend: TrendState, volatility: VolatilityState, vix: float | None) -> RiskState:
        if volatility is VolatilityState.EXTREME or (vix is not None and vix >= 30):
            return RiskState.RISK_OFF
        if trend in {TrendState.BEAR, TrendState.STRONG_BEAR}:
            return RiskState.RISK_OFF
        if trend in {TrendState.BULL, TrendState.STRONG_BULL} and volatility in {VolatilityState.LOW, VolatilityState.NORMAL}:
            return RiskState.RISK_ON
        return RiskState.NEUTRAL

    def detect(self, indicators: MarketIndicators | Mapping[str, Any]) -> MarketRegime:
        d = MarketIndicators.from_mapping(indicators) if isinstance(indicators, Mapping) else indicators
        if not isinstance(d, MarketIndicators):
            raise TypeError("indicators must be MarketIndicators or a mapping")
        available = d.available_count()
        if available < self.minimum_indicators:
            result = MarketRegime(
                TrendState.UNKNOWN, VolatilityState.UNKNOWN, RiskState.UNKNOWN,
                0.0, 0.0, 0.0,
                (f"Insufficient indicators: {available} available, {self.minimum_indicators} required",),
                available,
            )
            self._last_regime = result
            return result

        trend_score, trend_reasons = self._trend_score(d)
        volatility, volatility_score, volatility_reasons = self._volatility(d)
        trend = self._classify_trend(trend_score)
        risk = self._classify_risk(trend, volatility, d.vix)
        coverage = min(1.0, available / 10.0)
        confidence = self._clip(0.35 + 0.40 * abs(trend_score) + 0.25 * coverage, 0.0, 1.0)
        if trend is TrendState.SIDEWAYS:
            confidence = self._clip(0.45 + 0.25 * coverage, 0.0, 1.0)

        result = MarketRegime(
            trend, volatility, risk, confidence, trend_score,
            volatility_score, tuple(trend_reasons + volatility_reasons), available,
        )
        self._last_regime = result
        return result

    def regime_multipliers(self, regime: MarketRegime | None = None) -> dict[str, float]:
        r = regime or self._last_regime
        if r is None:
            raise ValueError("no market regime is available")
        m = {"BUY": 1.0, "SELL": 1.0, "HOLD": 1.0}
        if r.trend is TrendState.STRONG_BULL:
            m.update(BUY=1.30, SELL=0.70, HOLD=0.90)
        elif r.trend is TrendState.BULL:
            m.update(BUY=1.15, SELL=0.85, HOLD=0.95)
        elif r.trend is TrendState.STRONG_BEAR:
            m.update(BUY=0.65, SELL=1.35, HOLD=1.05)
        elif r.trend is TrendState.BEAR:
            m.update(BUY=0.80, SELL=1.20, HOLD=1.00)
        elif r.trend is TrendState.SIDEWAYS:
            m.update(BUY=0.90, SELL=0.90, HOLD=1.20)
        if r.volatility is VolatilityState.HIGH:
            m["BUY"] *= 0.90; m["SELL"] *= 0.90; m["HOLD"] *= 1.10
        elif r.volatility is VolatilityState.EXTREME:
            m["BUY"] *= 0.70; m["SELL"] *= 0.70; m["HOLD"] *= 1.40
        if r.risk is RiskState.RISK_OFF:
            m["BUY"] *= 0.75; m["HOLD"] *= 1.15
        elif r.risk is RiskState.RISK_ON:
            m["BUY"] *= 1.10; m["HOLD"] *= 0.95
        return {key: round(value, 6) for key, value in m.items()}

    def reset(self) -> None:
        self._last_regime = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "strong_trend_threshold": self.strong_trend_threshold,
            "trend_threshold": self.trend_threshold,
            "low_volatility_atr_percent": self.low_volatility_atr_percent,
            "high_volatility_atr_percent": self.high_volatility_atr_percent,
            "extreme_volatility_atr_percent": self.extreme_volatility_atr_percent,
            "high_vix_threshold": self.high_vix_threshold,
            "extreme_vix_threshold": self.extreme_vix_threshold,
            "minimum_indicators": self.minimum_indicators,
            "last_regime": self._last_regime.to_dict() if self._last_regime else None,
        }

    def __repr__(self) -> str:
        return (
            f"MarketRegimeDetector(trend_threshold={self.trend_threshold}, "
            f"strong_trend_threshold={self.strong_trend_threshold}, "
            f"minimum_indicators={self.minimum_indicators})"
        )
