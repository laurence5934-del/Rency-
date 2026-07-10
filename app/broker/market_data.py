"""
Live Market Data Module
AI Trading Platform V4 Professional
"""

import threading
import time

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

from app.utils.config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID


class MarketDataApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

        self.next_order_id = None
        self.market_data = {
            "symbol": "",
            "bid": None,
            "ask": None,
            "last": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
            "spread": None,
        }

    def nextValidId(self, orderId):
        self.next_order_id = orderId

    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 1:
            self.market_data["bid"] = price
        elif tickType == 2:
            self.market_data["ask"] = price
        elif tickType == 4:
            self.market_data["last"] = price
        elif tickType == 6:
            self.market_data["high"] = price
        elif tickType == 7:
            self.market_data["low"] = price
        elif tickType == 9:
            self.market_data["close"] = price

    def tickSize(self, reqId, tickType, size):
        if tickType == 8:
            self.market_data["volume"] = size


def make_stock_contract(symbol: str) -> Contract:
    contract = Contract()
    contract.symbol = symbol.upper()
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract


def connect_market_data(timeout: int = 10) -> MarketDataApp:
    app = MarketDataApp()
    app.connect(IBKR_HOST, IBKR_PORT, clientId=IBKR_CLIENT_ID + 100)

    thread = threading.Thread(target=app.run, daemon=True)
    thread.start()

    start = time.time()
    while app.next_order_id is None and time.time() - start < timeout:
        time.sleep(0.1)

    if app.next_order_id is None:
        app.disconnect()
        raise TimeoutError("No nextValidId received from TWS for market data.")

    return app


def get_market_data(symbol: str) -> dict:
    app = connect_market_data()

    try:
        contract = make_stock_contract(symbol)
        app.market_data["symbol"] = symbol.upper()
        app.reqMarketDataType(3)
        app.reqMktData(1001, contract, "", False, False, [])

        time.sleep(5)

        app.cancelMktData(1001)

        bid = app.market_data.get("bid")
        ask = app.market_data.get("ask")

        if bid is not None and ask is not None:
            app.market_data["spread"] = round(ask - bid, 4)

        return {
            "connected": app.isConnected(),
            "data": app.market_data,
        }

    except Exception as exc:
        return {
            "connected": False,
            "status": "ERROR",
            "message": str(exc),
            "data": app.market_data,
        }

    finally:
        app.disconnect()