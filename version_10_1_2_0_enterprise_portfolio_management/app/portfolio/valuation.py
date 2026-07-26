from __future__ import annotations

from .models import AccountBalance, Position


class PortfolioValuationEngine:
    def calculate(self, balance: AccountBalance, positions: tuple[Position, ...]) -> dict[str, float]:
        gross_market_value = sum(abs(position.market_value) for position in positions)
        signed_market_value = sum(position.market_value for position in positions)
        realized_pnl = sum(position.realized_pnl for position in positions)
        unrealized_pnl = sum(position.unrealized_pnl for position in positions)
        dividends_received = sum(position.dividends_received for position in positions)
        net_liquidation_value = balance.cash + signed_market_value
        return {
            "gross_market_value": gross_market_value,
            "signed_market_value": signed_market_value,
            "net_liquidation_value": net_liquidation_value,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "dividends_received": dividends_received,
        }
