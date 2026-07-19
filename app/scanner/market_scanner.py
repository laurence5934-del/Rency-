from __future__ import annotations

from collections.abc import Callable, Iterable

import pandas as pd

from app.scanner.indicator_engine import calculate_indicator_scores
from app.scanner.scanner_config import ScannerConfig
from app.scanner.scanner_models import ScanResult, ScanSummary


MarketDataLoader = Callable[[str], pd.DataFrame]


class MarketScanner:
    """
    Read-only deterministic market scanner.

    The scanner:
        1. Loads historical OHLCV data.
        2. Calculates deterministic indicator scores.
        3. Builds ScanResult objects.
        4. Ranks results from highest to lowest score.

    It does not submit orders or communicate with a broker.
    """

    def __init__(
        self,
        data_loader: MarketDataLoader | None = None,
        config: ScannerConfig | None = None,
    ) -> None:
        self.data_loader = data_loader
        self.config = config or ScannerConfig()

    def scan(self, symbols: Iterable[str]) -> ScanSummary:
        """
        Scan symbols and return ranked results.

        Symbols that fail to load or calculate are included with a score of
        zero and an explanation in their reasons list.
        """

        if self.data_loader is None:
            raise RuntimeError(
                "MarketScanner requires a data_loader before scan() can run."
            )

        normalized_symbols = self._normalize_symbols(symbols)

        results = [
            self.scan_symbol(symbol)
            for symbol in normalized_symbols
        ]

        ranked_results = sorted(
            results,
            key=lambda result: (-result.total_score, result.symbol),
        )

        qualified_symbols = sum(
            1 for result in ranked_results if result.qualified
        )

        return ScanSummary(
            total_symbols=len(ranked_results),
            qualified_symbols=qualified_symbols,
            results=ranked_results,
        )

    def scan_symbol(self, symbol: str) -> ScanResult:
        """Load and score one symbol."""

        normalized_symbol = self._normalize_symbol(symbol)

        if self.data_loader is None:
            raise RuntimeError(
                "MarketScanner requires a data_loader before scanning."
            )

        try:
            market_data = self.data_loader(normalized_symbol)

            scores = calculate_indicator_scores(
                market_data,
                trend_max=self.config.trend_weight,
                momentum_max=self.config.momentum_weight,
                volume_max=self.config.volume_weight,
                breakout_max=self.config.breakout_weight,
                risk_max=self.config.risk_weight,
                relative_volume_threshold=(
                    self.config.relative_volume_threshold
                ),
                atr_percent_limit=self.config.atr_percent_limit,
            )

            last_price = self._extract_last_price(market_data)
            total_score = scores.total_score

            qualified = total_score >= self.config.min_total_score

            reasons = list(scores.reasons)

            if qualified:
                reasons.append(
                    f"Total score of {total_score:.2f} meets the "
                    f"{self.config.min_total_score:.2f} qualification threshold."
                )
            else:
                reasons.append(
                    f"Total score of {total_score:.2f} is below the "
                    f"{self.config.min_total_score:.2f} qualification threshold."
                )

            return ScanResult(
                symbol=normalized_symbol,
                last_price=last_price,
                trend_score=scores.trend_score,
                momentum_score=scores.momentum_score,
                volume_score=scores.volume_score,
                breakout_score=scores.breakout_score,
                risk_score=scores.risk_score,
                total_score=total_score,
                qualified=qualified,
                reasons=reasons,
            )

        except Exception as exc:
            return ScanResult(
                symbol=normalized_symbol,
                last_price=0.0,
                total_score=0.0,
                qualified=False,
                reasons=[
                    f"Unable to scan {normalized_symbol}: "
                    f"{type(exc).__name__}: {exc}"
                ],
            )

    @staticmethod
    def _extract_last_price(data: pd.DataFrame) -> float:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                "The market-data loader must return a pandas DataFrame."
            )

        if data.empty:
            raise ValueError("Market data cannot be empty.")

        normalized_columns = {
            str(column).strip().lower(): column
            for column in data.columns
        }

        close_column = normalized_columns.get("close")

        if close_column is None:
            raise ValueError(
                "Market data must include a close column."
            )

        close_values = pd.to_numeric(
            data[close_column],
            errors="coerce",
        ).dropna()

        if close_values.empty:
            raise ValueError(
                "Market data does not contain a valid closing price."
            )

        last_price = float(close_values.iloc[-1])

        if last_price <= 0:
            raise ValueError(
                "The latest closing price must be greater than zero."
            )

        return round(last_price, 4)

    @classmethod
    def _normalize_symbols(
        cls,
        symbols: Iterable[str],
    ) -> list[str]:
        if isinstance(symbols, str):
            symbols = [symbols]

        try:
            symbol_list = list(symbols)
        except TypeError as exc:
            raise TypeError(
                "symbols must be an iterable of ticker symbols."
            ) from exc

        normalized: list[str] = []
        seen: set[str] = set()

        for symbol in symbol_list:
            clean_symbol = cls._normalize_symbol(symbol)

            if clean_symbol not in seen:
                normalized.append(clean_symbol)
                seen.add(clean_symbol)

        return normalized

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        if not isinstance(symbol, str):
            raise TypeError("Each symbol must be a string.")

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Ticker symbols cannot be empty.")

        return normalized_symbol