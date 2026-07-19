from dataclasses import dataclass, field
from typing import List


@dataclass
class ScanResult:
    symbol: str
    last_price: float

    trend_score: float = 0.0
    momentum_score: float = 0.0
    volume_score: float = 0.0
    breakout_score: float = 0.0
    risk_score: float = 0.0

    total_score: float = 0.0

    qualified: bool = False

    reasons: List[str] = field(default_factory=list)


@dataclass
class ScanSummary:
    total_symbols: int
    qualified_symbols: int
    results: List[ScanResult]