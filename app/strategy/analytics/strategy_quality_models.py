from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class StrategyQualityMetrics:
    """Advanced measurements of strategy quality and consistency."""

    system_quality_number: Decimal = Decimal("0")
    kelly_criterion: Decimal = Decimal("0")
    gain_to_pain_ratio: Decimal = Decimal("0")
    ulcer_index: Decimal = Decimal("0")