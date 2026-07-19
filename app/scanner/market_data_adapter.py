from __future__ import annotations

import pandas as pd


class MarketDataAdapter:
    """Convert provider dictionaries into OHLCV DataFrames."""

    @staticmethod
    def to_dataframe(data: dict) -> pd.DataFrame:
        required = (
            "highs",
            "lows",
            "closes",
        )

        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        closes = data["closes"]
        highs = data["highs"]
        lows = data["lows"]

        volume = data.get(
            "current_volume",
            1_000_000,
        )

        rows = len(closes)

        if not (len(highs) == len(lows) == rows):
            raise ValueError(
                "High, low and close arrays must have equal length."
            )

        return pd.DataFrame(
            {
                "open": closes,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": [volume] * rows,
            }
        )