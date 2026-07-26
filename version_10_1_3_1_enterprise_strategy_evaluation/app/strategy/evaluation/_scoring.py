from __future__ import annotations


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, float(value)))


def linear_score(value: float, bad: float, good: float) -> float:
    if good == bad:
        raise ValueError("good and bad thresholds must differ")
    return clamp((value - bad) * 100.0 / (good - bad))
