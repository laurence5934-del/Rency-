"""
Official Interactive Brokers API layer.
Uses ibapi directly.
Paper trading first.
"""

import threading
import time

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

from app.utils.config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, PAPER_TRADING_ONLY


class IBKRApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id = None
        self.accounts = []
        self.order_statuses = []
        self.errors = []
        self.fills = []
        self.account_summary = []
        self.positions = []
        self.positions_received = False

    def nextValidId(self, orderId: int):
        self.next_order_id = orderId

    def managedAccounts(self, accountsList: str):
        self.accounts = accountsList.split(",") if accountsList else []

    def accountSummary(self, reqId, account, tag, value, currency):
        self.account_summary.append({
            "account": account,
            "tag": tag,
            "value": value,
            "currency": currency,
        })

    def position(self, account, contract, position, avgCost):
        self.positions.append({
            "account": account,
            "symbol": contract.symbol,
            "secType": contract.secType,
            "currency": contract.currency,
            "exchange": contract.exchange,
            "position": position,
            "avgCost": avgCost,
        })

    def positionEnd(self):
        self.positions_received = True

    def orderStatus(
        self, orderId, status, filled, remaining, avgFillPrice,
        permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice
    ):
        self.order_statuses.append({
            "orderId": orderId,
            "status": status,
            "filled": filled,
            "remaining": remaining,
            "avgFillPrice": avgFillPrice,
            "lastFillPrice": lastFillPrice,
        })

    def execDetails(self, reqId, contract, execution):
        self.fills.append({
            "symbol": contract.symbol,
            "shares": execution.shares,
            "price": execution.price,
            "time": execution.time,
            "side": execution.side,
        })

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        self.errors.append({
            "reqId": reqId,
            "code": errorCode,
            "message": errorString,
        })


def make_stock_contract(symbol: str) -> Contract:
    contract = Contract()
    contract.symbol = symbol.upper()
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract


def make_limit_order(action: str, quantity: int, limit_price: float) -> Order:
    order = Order()
    order.action = action.upper()
    order.orderType = "LMT"
    order.totalQuantity = quantity
    order.lmtPrice = limit_price
    order.tif = "DAY"
    order.eTradeOnly = False
    order.firmQuoteOnly = False
    return order


def connect_ibkr(timeout: int = 10) -> IBKRApp:
    app = IBKRApp()
    app.connect(IBKR_HOST, IBKR_PORT, clientId=IBKR_CLIENT_ID)

    thread = threading.Thread(target=app.run, daemon=True)
    thread.start()

    start = time.time()
    while app.next_order_id is None and time.time() - start < timeout:
        time.sleep(0.1)

    if app.next_order_id is None:
        app.disconnect()
        raise TimeoutError("No nextValidId received from TWS.")

    return app


def test_connection() -> dict:
    app = connect_ibkr()
    time.sleep(1)

    result = {
        "connected": app.isConnected(),
        "next_order_id": app.next_order_id,
        "accounts": app.accounts,
        "errors": app.errors[-10:],
    }

    app.disconnect()
    return result


def get_account_summary() -> dict:
    app = connect_ibkr()

    try:
        app.reqAccountSummary(
            9001,
            "All",
            "NetLiquidation,TotalCashValue,BuyingPower,AvailableFunds,"
            "GrossPositionValue,UnrealizedPnL,RealizedPnL"
        )
        time.sleep(5)
        app.cancelAccountSummary(9001)

        return {
            "connected": app.isConnected(),
            "accounts": app.accounts,
            "summary": app.account_summary,
            "errors": app.errors[-10:],
        }

    except Exception as exc:
        return {
            "connected": False,
            "status": "ERROR",
            "message": str(exc),
            "errors": app.errors[-10:],
        }

    finally:
        app.disconnect()


def get_positions() -> dict:
    app = connect_ibkr()

    try:
        app.positions = []
        app.positions_received = False

        app.reqPositions()

        start = time.time()
        while not app.positions_received and time.time() - start < 10:
            time.sleep(0.1)

        app.cancelPositions()

        return {
            "connected": app.isConnected(),
            "accounts": app.accounts,
            "positions": app.positions,
            "errors": app.errors[-10:],
        }

    except Exception as exc:
        return {
            "connected": False,
            "status": "ERROR",
            "message": str(exc),
            "errors": app.errors[-10:],
        }

    finally:
        app.disconnect()


def place_paper_buy(symbol: str, quantity: int) -> dict:
    if not PAPER_TRADING_ONLY:
        return {"submitted": False, "status": "LIVE_TRADING_BLOCKED_BY_V4"}

    if quantity <= 0:
        return {"submitted": False, "status": "INVALID_QUANTITY"}

    app = connect_ibkr()

    try:
        order_id = app.next_order_id
        contract = make_stock_contract(symbol)
        order = make_limit_order("BUY", quantity, 100.00)

        app.placeOrder(order_id, contract, order)
        time.sleep(10)

        latest_status = app.order_statuses[-1]["status"] if app.order_statuses else "UNKNOWN"

        return {
            "submitted": True,
            "status": latest_status,
            "symbol": symbol.upper(),
            "quantity": quantity,
            "order_id": order_id,
            "statuses": app.order_statuses,
            "fills": app.fills,
            "errors": app.errors[-10:],
        }

    except Exception as exc:
        return {
            "submitted": False,
            "status": "ERROR",
            "message": str(exc),
            "errors": app.errors[-10:],
        }

    finally:
        app.disconnect()


def cancel_order(order_id: int) -> dict:
    app = connect_ibkr()

    try:
        app.cancelOrder(order_id)
        time.sleep(5)

        latest_status = app.order_statuses[-1]["status"] if app.order_statuses else "UNKNOWN"

        return {
            "cancel_requested": True,
            "order_id": order_id,
            "status": latest_status,
            "statuses": app.order_statuses,
            "errors": app.errors[-10:],
        }

    except Exception as exc:
        return {
            "cancel_requested": False,
            "order_id": order_id,
            "status": "ERROR",
            "message": str(exc),
            "errors": app.errors[-10:],
        }
    

    finally:
        app.disconnect()
    
    