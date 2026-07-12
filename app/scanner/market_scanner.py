"""
AI Market Scanner
Version 6.0
"""

from app.ai.scanner_ai import score_symbol


WATCHLIST = [
    "NVDA",
    "AMD",
    "AVGO",
    "MSFT",
    "META",
    "AAPL",
    "AMZN",
    "GOOGL",
    "TSLA",
    "SMCI",
    "PLTR",
    "NFLX",
    "QQQ",
    "SPY",
    "SMH",
]


def get_watchlist() -> list[str]:
    return WATCHLIST.copy()


def scan_market() -> list[dict]:
    results = [
        score_symbol(symbol)
        for symbol in get_watchlist()
    ]

    return sorted(
        results,
        key=lambda item: item["score"],
        reverse=True,
    )