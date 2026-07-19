from dataclasses import dataclass


@dataclass
class ScannerConfig:

    min_total_score: float = 70.0

    trend_weight: float = 30.0
    momentum_weight: float = 25.0
    volume_weight: float = 20.0
    breakout_weight: float = 15.0
    risk_weight: float = 10.0

    relative_volume_threshold: float = 1.20

    atr_percent_limit: float = 6.0