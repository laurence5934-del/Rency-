from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from ..broker_interface import BrokerInterface
from ..broker_models import (
    BrokerCapabilities,
    BrokerEnvironment,
    BrokerFill,
    BrokerHealthSnapshot,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerOrderStatus,
    BrokerOrderType,
    BrokerStatus,
)


class SimulatedBroker(BrokerInterface):
    def __init__(self, default_price: float = 100.0, fill_ratio: float = 1.0) -> None:
        if default_price <= 0 or not 0 < fill_ratio <= 1:
            raise ValueError("invalid simulated broker configuration")
        self._default_price = default_price
        self._fill_ratio = fill_ratio
        self._cancelled: set[str] = set()

    @property
    def name(self) -> str:
        return "SIMULATED"

    @property
    def environment(self) -> BrokerEnvironment:
        return BrokerEnvironment.SIMULATED

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(fractional_shares=True, short_sales=True)

    def health(self) -> BrokerHealthSnapshot:
        start = perf_counter()
        latency = (perf_counter() - start) * 1000
        return BrokerHealthSnapshot(self.name, BrokerStatus.HEALTHY, self.environment, latency)

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        quantity = min(request.quantity, request.quantity * self._fill_ratio)
        price = request.limit_price if request.order_type in {BrokerOrderType.LIMIT, BrokerOrderType.STOP_LIMIT} and request.limit_price else self._default_price
        fill = BrokerFill.create(quantity, price)
        status = BrokerOrderStatus.FILLED if quantity == request.quantity else BrokerOrderStatus.PARTIALLY_FILLED
        return BrokerOrderResult(
            broker_name=self.name,
            broker_order_id=f"SIM-{uuid4().hex[:16].upper()}",
            status=status,
            requested_quantity=request.quantity,
            filled_quantity=quantity,
            average_fill_price=price,
            fills=(fill,),
            message="Simulated execution completed",
        )

    def cancel_order(self, broker_order_id: str) -> bool:
        self._cancelled.add(broker_order_id)
        return True
