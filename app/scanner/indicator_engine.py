from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = {"high", "low", "close", "volume"}


@dataclass(frozen=True)
class IndicatorScores:
    """Individual scanner scores and explanatory reasons."""

    trend_score: float
    momentum_score: float
    volume_score: float
    breakout_score: float
    risk_score: float
    reasons: tuple[str, ...]

    @property
    def total_score(self) -> float:
        """Return the combined score, capped between 0 and 100."""

        total = (
            self.trend_score
            + self.momentum_score
            + self.volume_score
            + self.breakout_score
            + self.risk_score
        )
        return round(_clamp(total, 0.0, 100.0), 2)


def prepare_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and normalize historical OHLCV market data.

    Expected columns:
        high, low, close, volume

    Column names are treated case-insensitively. An ``open`` column is
    allowed but is not required by the current scoring model.
    """

    if not isinstance(data, pd.DataFrame):
        raise TypeError("Market data must be provided as a pandas DataFrame.")

    if data.empty:
        raise ValueError("Market data cannot be empty.")

    normalized = data.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]

    missing_columns = REQUIRED_COLUMNS.difference(normalized.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Market data is missing required columns: {missing}")

    numeric_columns = ["high", "low", "close", "volume"]

    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized = normalized.dropna(subset=numeric_columns).copy()

    if normalized.empty:
        raise ValueError("Market data does not contain valid numeric OHLCV rows.")

    if (normalized["close"] <= 0).any():
        raise ValueError("Closing prices must be greater than zero.")

    if (normalized["high"] <= 0).any() or (normalized["low"] <= 0).any():
        raise ValueError("High and low prices must be greater than zero.")

    if (normalized["volume"] < 0).any():
        raise ValueError("Volume cannot be negative.")

    invalid_price_rows = normalized["high"] < normalized["low"]
    if invalid_price_rows.any():
        raise ValueError("High price cannot be lower than low price.")

    return normalized.reset_index(drop=True)


def calculate_trend_score(
    data: pd.DataFrame,
    max_score: float = 30.0,
    short_period: int = 20,
    long_period: int = 50,
) -> tuple[float, list[str]]:
    """
    Score trend quality.

    Rules:
        - Price above short moving average: 10 points
        - Short moving average above long moving average: 10 points
        - Short moving average rising: 5 points
        - Price above long moving average: 5 points
    """

    frame = prepare_ohlcv(data)
    _validate_period(short_period, "short_period")
    _validate_period(long_period, "long_period")

    if short_period >= long_period:
        raise ValueError("short_period must be less than long_period.")

    if len(frame) < long_period + 1:
        return 0.0, ["Insufficient history for trend scoring."]

    close = frame["close"]
    short_average = close.rolling(short_period).mean()
    long_average = close.rolling(long_period).mean()

    current_price = float(close.iloc[-1])
    current_short = float(short_average.iloc[-1])
    previous_short = float(short_average.iloc[-2])
    current_long = float(long_average.iloc[-1])

    raw_score = 0.0
    reasons: list[str] = []

    if current_price > current_short:
        raw_score += 10.0
        reasons.append("Price is above the short-term moving average.")

    if current_short > current_long:
        raw_score += 10.0
        reasons.append("Short-term trend is above the long-term trend.")

    if current_short > previous_short:
        raw_score += 5.0
        reasons.append("Short-term moving average is rising.")

    if current_price > current_long:
        raw_score += 5.0
        reasons.append("Price is above the long-term moving average.")

    score = _scale_score(raw_score, raw_maximum=30.0, configured_maximum=max_score)
    return score, reasons


def calculate_momentum_score(
    data: pd.DataFrame,
    max_score: float = 25.0,
    return_period: int = 20,
    rsi_period: int = 14,
) -> tuple[float, list[str]]:
    """
    Score price momentum.

    Rules:
        - Positive return: up to 15 points
        - Healthy RSI between 50 and 70: 10 points
        - RSI between 40 and 50 or 70 and 75: 5 points
    """

    frame = prepare_ohlcv(data)
    _validate_period(return_period, "return_period")
    _validate_period(rsi_period, "rsi_period")

    minimum_rows = max(return_period + 1, rsi_period + 1)
    if len(frame) < minimum_rows:
        return 0.0, ["Insufficient history for momentum scoring."]

    close = frame["close"]
    current_price = float(close.iloc[-1])
    previous_price = float(close.iloc[-(return_period + 1)])

    period_return = (current_price / previous_price) - 1.0
    rsi = _calculate_rsi(close, rsi_period)

    raw_score = 0.0
    reasons: list[str] = []

    if period_return > 0:
        return_points = _clamp(period_return / 0.15, 0.0, 1.0) * 15.0
        raw_score += return_points
        reasons.append(
            f"{return_period}-period return is positive at "
            f"{period_return * 100:.2f}%."
        )

    if 50.0 <= rsi <= 70.0:
        raw_score += 10.0
        reasons.append(f"RSI shows healthy momentum at {rsi:.2f}.")
    elif 40.0 <= rsi < 50.0 or 70.0 < rsi <= 75.0:
        raw_score += 5.0
        reasons.append(f"RSI shows moderate momentum at {rsi:.2f}.")

    score = _scale_score(raw_score, raw_maximum=25.0, configured_maximum=max_score)
    return score, reasons


def calculate_volume_score(
    data: pd.DataFrame,
    max_score: float = 20.0,
    average_period: int = 20,
    relative_volume_threshold: float = 1.20,
) -> tuple[float, list[str]]:
    """
    Score current volume relative to its recent average.

    Relative-volume scoring:
        Below 1.00:       0 points
        1.00 to 1.20:    up to 8 points
        1.20 to 1.50:    8 to 14 points
        1.50 to 2.00+:  14 to 20 points
    """

    frame = prepare_ohlcv(data)
    _validate_period(average_period, "average_period")

    if relative_volume_threshold <= 0:
        raise ValueError("relative_volume_threshold must be greater than zero.")

    if len(frame) < average_period + 1:
        return 0.0, ["Insufficient history for volume scoring."]

    current_volume = float(frame["volume"].iloc[-1])
    average_volume = float(
        frame["volume"].iloc[-(average_period + 1) : -1].mean()
    )

    if average_volume <= 0:
        return 0.0, ["Average trading volume is unavailable or zero."]

    relative_volume = current_volume / average_volume
    raw_score = 0.0
    reasons: list[str] = []

    if relative_volume >= 2.0:
        raw_score = 20.0
    elif relative_volume >= 1.5:
        raw_score = 14.0 + ((relative_volume - 1.5) / 0.5) * 6.0
    elif relative_volume >= relative_volume_threshold:
        threshold_range = max(1.5 - relative_volume_threshold, 0.01)
        raw_score = 8.0 + (
            (relative_volume - relative_volume_threshold) / threshold_range
        ) * 6.0
    elif relative_volume >= 1.0:
        threshold_range = max(relative_volume_threshold - 1.0, 0.01)
        raw_score = ((relative_volume - 1.0) / threshold_range) * 8.0

    if relative_volume >= relative_volume_threshold:
        reasons.append(
            f"Relative volume is elevated at {relative_volume:.2f} times average."
        )
    elif relative_volume >= 1.0:
        reasons.append(
            f"Volume is slightly above average at {relative_volume:.2f} times."
        )

    score = _scale_score(raw_score, raw_maximum=20.0, configured_maximum=max_score)
    return score, reasons


def calculate_breakout_score(
    data: pd.DataFrame,
    max_score: float = 15.0,
    lookback_period: int = 20,
    near_breakout_percent: float = 2.0,
) -> tuple[float, list[str]]:
    """
    Score the latest close relative to the preceding lookback-period high.

    Rules:
        - Close above previous high: 15 points
        - Within configured percentage of previous high: up to 12 points
    """

    frame = prepare_ohlcv(data)
    _validate_period(lookback_period, "lookback_period")

    if near_breakout_percent <= 0:
        raise ValueError("near_breakout_percent must be greater than zero.")

    if len(frame) < lookback_period + 1:
        return 0.0, ["Insufficient history for breakout scoring."]

    current_close = float(frame["close"].iloc[-1])
    previous_high = float(
        frame["high"].iloc[-(lookback_period + 1) : -1].max()
    )

    if previous_high <= 0:
        return 0.0, ["Previous high is unavailable for breakout scoring."]

    distance_percent = ((current_close / previous_high) - 1.0) * 100.0
    raw_score = 0.0
    reasons: list[str] = []

    if current_close >= previous_high:
        raw_score = 15.0
        reasons.append(
            f"Price broke above the previous {lookback_period}-period high."
        )
    elif distance_percent >= -near_breakout_percent:
        proximity = 1.0 - (
            abs(distance_percent) / near_breakout_percent
        )
        raw_score = 6.0 + proximity * 6.0
        reasons.append(
            f"Price is {abs(distance_percent):.2f}% below the previous "
            f"{lookback_period}-period high."
        )

    score = _scale_score(raw_score, raw_maximum=15.0, configured_maximum=max_score)
    return score, reasons


def calculate_risk_score(
    data: pd.DataFrame,
    max_score: float = 10.0,
    atr_period: int = 14,
    atr_percent_limit: float = 6.0,
) -> tuple[float, list[str]]:
    """
    Score volatility quality using ATR as a percentage of price.

    Lower volatility earns more points. An ATR percentage at or above the
    configured limit earns zero points.
    """

    frame = prepare_ohlcv(data)
    _validate_period(atr_period, "atr_period")

    if atr_percent_limit <= 0:
        raise ValueError("atr_percent_limit must be greater than zero.")

    if len(frame) < atr_period + 1:
        return 0.0, ["Insufficient history for volatility-risk scoring."]

    atr = _calculate_atr(frame, atr_period)
    current_price = float(frame["close"].iloc[-1])

    atr_percent = (atr / current_price) * 100.0
    raw_score = _clamp(
        10.0 * (1.0 - atr_percent / atr_percent_limit),
        0.0,
        10.0,
    )

    reasons: list[str] = []

    if atr_percent < atr_percent_limit:
        reasons.append(
            f"ATR volatility is within the configured limit at "
            f"{atr_percent:.2f}%."
        )
    else:
        reasons.append(
            f"ATR volatility is elevated at {atr_percent:.2f}%."
        )

    score = _scale_score(raw_score, raw_maximum=10.0, configured_maximum=max_score)
    return score, reasons


def calculate_indicator_scores(
    data: pd.DataFrame,
    *,
    trend_max: float = 30.0,
    momentum_max: float = 25.0,
    volume_max: float = 20.0,
    breakout_max: float = 15.0,
    risk_max: float = 10.0,
    relative_volume_threshold: float = 1.20,
    atr_percent_limit: float = 6.0,
) -> IndicatorScores:
    """Calculate all deterministic indicator scores for one symbol."""

    trend_score, trend_reasons = calculate_trend_score(
        data,
        max_score=trend_max,
    )
    momentum_score, momentum_reasons = calculate_momentum_score(
        data,
        max_score=momentum_max,
    )
    volume_score, volume_reasons = calculate_volume_score(
        data,
        max_score=volume_max,
        relative_volume_threshold=relative_volume_threshold,
    )
    breakout_score, breakout_reasons = calculate_breakout_score(
        data,
        max_score=breakout_max,
    )
    risk_score, risk_reasons = calculate_risk_score(
        data,
        max_score=risk_max,
        atr_percent_limit=atr_percent_limit,
    )

    reasons = _deduplicate_reasons(
        trend_reasons
        + momentum_reasons
        + volume_reasons
        + breakout_reasons
        + risk_reasons
    )

    return IndicatorScores(
        trend_score=trend_score,
        momentum_score=momentum_score,
        volume_score=volume_score,
        breakout_score=breakout_score,
        risk_score=risk_score,
        reasons=tuple(reasons),
    )


def _calculate_rsi(close: pd.Series, period: int) -> float:
    """Calculate Wilder-style RSI."""

    changes = close.diff()
    gains = changes.clip(lower=0.0)
    losses = -changes.clip(upper=0.0)

    average_gain = gains.ewm(
        alpha=1.0 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    average_loss = losses.ewm(
        alpha=1.0 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    latest_gain = float(average_gain.iloc[-1])
    latest_loss = float(average_loss.iloc[-1])

    if latest_loss == 0:
        return 100.0 if latest_gain > 0 else 50.0

    relative_strength = latest_gain / latest_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _calculate_atr(data: pd.DataFrame, period: int) -> float:
    """Calculate average true range."""

    previous_close = data["close"].shift(1)

    true_range = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - previous_close).abs(),
            (data["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = true_range.rolling(period).mean().iloc[-1]

    if pd.isna(atr):
        raise ValueError("ATR could not be calculated from the supplied data.")

    return float(atr)


def _scale_score(
    raw_score: float,
    raw_maximum: float,
    configured_maximum: float,
) -> float:
    """Scale a raw score to the configured maximum."""

    if configured_maximum < 0:
        raise ValueError("Configured maximum score cannot be negative.")

    if raw_maximum <= 0:
        raise ValueError("Raw maximum score must be greater than zero.")

    scaled = (raw_score / raw_maximum) * configured_maximum
    return round(_clamp(scaled, 0.0, configured_maximum), 2)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Restrict a numeric value to an inclusive range."""

    numeric_value = float(value)

    if not isfinite(numeric_value):
        raise ValueError("Score values must be finite numbers.")

    return max(minimum, min(numeric_value, maximum))


def _validate_period(period: int, name: str) -> None:
    if not isinstance(period, int) or isinstance(period, bool):
        raise TypeError(f"{name} must be an integer.")

    if period <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _deduplicate_reasons(reasons: Iterable[str]) -> list[str]:
    """Remove duplicate explanations while preserving their order."""

    return list(dict.fromkeys(reason for reason in reasons if reason))