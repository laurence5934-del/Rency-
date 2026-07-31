from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StrategyEvaluation:
    """High-level assessment of a trading strategy."""

    score: int
    grade: str
    recommendation: str
    strengths: tuple[str, ...]
    concerns: tuple[str, ...]