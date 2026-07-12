"""
IBKR Open Orders Reader
AI Trading Platform V4.6
"""

import threading
import time
from typing import Any

from ibapi.client import EClient
from ibapi.wrapper import EWrapper

from app.utils.config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID


class OpenOrdersApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

        self.connected_ready = False
        self.orders_received = False
        self.open_orders: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []

    def nextValidId(self, orderId: int):
        self.connected_ready = True

    def openOrder(self, orderId, contract, order, orderState):
        self.open_orders.append(
            {
                "order_id": orderId,
                "symbol": contract.symbol,
                "security_type": contract.secType,
                "exchange": contract.exchange,
                "currency": contract.currency,
                "action": order.action,
                "order_type": order.orderType,
                "quantity": float(order.totalQuantity),
                "limit_price": float(order.lmtPrice or 0),
                "time_in_force": order.tif,
                "status": orderState.status,
            }
        )

    def openOrderEnd(self):
        self.orders_received = True

    def error(
        self,
        reqId,
        errorCode,
        errorString,
        advancedOrderRejectJson="",
    ):
        self.errors.append(
            {
                "reqId": reqId,
                "code": errorCode,
                "message": errorString,
            }
        )


def connect_open_orders(timeout: int = 10) -> OpenOrdersApp:
    app = OpenOrdersApp()

    # Separate read-only client ID for the order display.
    app.connect(
        IBKR_HOST,
        IBKR_PORT,
        clientId=IBKR_CLIENT_ID + 200,
    )

    thread = threading.Thread(
        target=app.run,
        daemon=True,
    )
    thread.start()

    start = time.time()

    while (
        not app.connected_ready
        and time.time() - start < timeout
    ):
        time.sleep(0.1)

    if not app.connected_ready:
        app.disconnect()
        raise TimeoutError(
            "No nextValidId received from TWS for open-orders reader."
        )

    return app


def get_open_orders(timeout: int = 10) -> dict:
    app = connect_open_orders(timeout=timeout)

    try:
        app.reqAllOpenOrders()

        start = time.time()

        while (
            not app.orders_received
            and time.time() - start < timeout
        ):
            time.sleep(0.1)

        return {
            "connected": app.isConnected(),
            "orders": app.open_orders,
            "errors": app.errors[-10:],
        }

    except Exception as exc:
        return {
            "connected": False,
            "status": "ERROR",
            "message": str(exc),
            "orders": app.open_orders,
            "errors": app.errors[-10:],
        }

    finally:
        app.disconnect()