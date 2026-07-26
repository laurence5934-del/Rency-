from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping, Protocol, Sequence


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REPLACE_PENDING = "REPLACE_PENDING"
    REPLACED = "REPLACED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


class ExecutionEventType(str, Enum):
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_VALIDATED = "ORDER_VALIDATED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACKNOWLEDGED = "ORDER_ACKNOWLEDGED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCEL_REQUESTED = "ORDER_CANCEL_REQUESTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REPLACE_REQUESTED = "ORDER_REPLACE_REQUESTED"
    ORDER_REPLACED = "ORDER_REPLACED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    ORDER_ERROR = "ORDER_ERROR"


TERMINAL_STATUSES = {
    OrderStatus.REJECTED,
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.EXPIRED,
    OrderStatus.ERROR,
}


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.VALIDATED, OrderStatus.REJECTED, OrderStatus.ERROR},
    OrderStatus.VALIDATED: {OrderStatus.SUBMITTED, OrderStatus.REJECTED, OrderStatus.ERROR},
    OrderStatus.SUBMITTED: {
        OrderStatus.ACKNOWLEDGED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_PENDING,
        OrderStatus.REJECTED,
        OrderStatus.ERROR,
    },
    OrderStatus.ACKNOWLEDGED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_PENDING,
        OrderStatus.REPLACE_PENDING,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
        OrderStatus.ERROR,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_PENDING,
        OrderStatus.REPLACE_PENDING,
        OrderStatus.EXPIRED,
        OrderStatus.ERROR,
    },
    OrderStatus.CANCEL_PENDING: {OrderStatus.CANCELLED, OrderStatus.ERROR},
    OrderStatus.REPLACE_PENDING: {OrderStatus.REPLACED, OrderStatus.ERROR},
    OrderStatus.REPLACED: {
        OrderStatus.ACKNOWLEDGED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_PENDING,
        OrderStatus.REPLACE_PENDING,
        OrderStatus.ERROR,
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    trail_amount: Decimal | None = None
    trail_percent: Decimal | None = None
    strategy_id: str | None = None
    portfolio_id: str | None = None
    parent_order_id: str | None = None
    client_order_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol cannot be empty")
        quantity = _money(self.quantity)
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "quantity", quantity)

        if self.limit_price is not None:
            object.__setattr__(self, "limit_price", _money(self.limit_price))
        if self.stop_price is not None:
            object.__setattr__(self, "stop_price", _money(self.stop_price))
        if self.trail_amount is not None:
            object.__setattr__(self, "trail_amount", _money(self.trail_amount))
        if self.trail_percent is not None:
            object.__setattr__(self, "trail_percent", _money(self.trail_percent))

        self._validate_type_fields()

    def _validate_type_fields(self) -> None:
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise ValueError("LIMIT order requires limit_price")
        if self.order_type is OrderType.STOP and self.stop_price is None:
            raise ValueError("STOP order requires stop_price")
        if self.order_type is OrderType.STOP_LIMIT:
            if self.stop_price is None or self.limit_price is None:
                raise ValueError("STOP_LIMIT order requires stop_price and limit_price")
        if self.order_type is OrderType.TRAILING_STOP:
            provided = int(self.trail_amount is not None) + int(self.trail_percent is not None)
            if provided != 1:
                raise ValueError("TRAILING_STOP requires exactly one of trail_amount or trail_percent")
        for name in ("limit_price", "stop_price", "trail_amount", "trail_percent"):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class Fill:
    fill_id: str
    order_id: str
    quantity: Decimal
    price: Decimal
    commission: Decimal = Decimal("0")
    venue: str | None = None
    liquidity_flag: str | None = None
    timestamp_utc: str = field(default_factory=_utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        quantity = _money(self.quantity)
        price = _money(self.price)
        commission = _money(self.commission)
        if quantity <= 0 or price <= 0:
            raise ValueError("fill quantity and price must be positive")
        if commission < 0:
            raise ValueError("commission cannot be negative")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "commission", commission)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("quantity", "price", "commission"):
            data[key] = str(data[key])
        return data


@dataclass(frozen=True, slots=True)
class OrderSnapshot:
    order_id: str
    client_order_id: str
    request: OrderRequest
    status: OrderStatus
    created_at_utc: str
    updated_at_utc: str
    broker_order_id: str | None = None
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal | None = None
    commission_total: Decimal = Decimal("0")
    last_error: str | None = None
    version: int = 1
    fills: tuple[Fill, ...] = ()

    @property
    def remaining_quantity(self) -> Decimal:
        remaining = self.request.quantity - self.filled_quantity
        return remaining if remaining > 0 else Decimal("0")

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def to_dict(self) -> dict[str, Any]:
        request_data = asdict(self.request)
        for key in ("quantity", "limit_price", "stop_price", "trail_amount", "trail_percent"):
            if request_data[key] is not None:
                request_data[key] = str(request_data[key])
        request_data["side"] = self.request.side.value
        request_data["order_type"] = self.request.order_type.value
        request_data["time_in_force"] = self.request.time_in_force.value
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "request": request_data,
            "status": self.status.value,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "broker_order_id": self.broker_order_id,
            "filled_quantity": str(self.filled_quantity),
            "remaining_quantity": str(self.remaining_quantity),
            "average_fill_price": None if self.average_fill_price is None else str(self.average_fill_price),
            "commission_total": str(self.commission_total),
            "last_error": self.last_error,
            "version": self.version,
            "fills": [fill.to_dict() for fill in self.fills],
        }


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    event_id: str
    event_type: ExecutionEventType
    order_id: str
    timestamp_utc: str
    status: OrderStatus
    message: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class BrokerSubmissionResult:
    accepted: bool
    broker_order_id: str | None = None
    message: str | None = None
    acknowledged: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BrokerActionResult:
    accepted: bool
    message: str | None = None
    broker_order_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BrokerExecutionPort(Protocol):
    def submit_order(self, order: OrderSnapshot) -> BrokerSubmissionResult: ...

    def cancel_order(self, order: OrderSnapshot) -> BrokerActionResult: ...

    def replace_order(
        self,
        order: OrderSnapshot,
        new_request: OrderRequest,
    ) -> BrokerActionResult: ...


class RiskValidationPort(Protocol):
    def validate_order(self, order: OrderSnapshot) -> tuple[bool, str | None]: ...


class EventPublisher(Protocol):
    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        **kwargs: Any,
    ) -> Any: ...


@dataclass(slots=True)
class EMSConfig:
    auto_submit_after_validation: bool = False
    publish_events: bool = True
    reject_duplicate_client_order_ids: bool = True
    maximum_order_quantity: Decimal | None = None
    history_capacity: int = 100_000

    def __post_init__(self) -> None:
        if self.maximum_order_quantity is not None:
            self.maximum_order_quantity = _money(self.maximum_order_quantity)
            if self.maximum_order_quantity <= 0:
                raise ValueError("maximum_order_quantity must be positive")
        if self.history_capacity < 1:
            raise ValueError("history_capacity must be positive")


@dataclass(frozen=True, slots=True)
class EMSMetrics:
    orders_created: int
    orders_validated: int
    orders_rejected: int
    orders_submitted: int
    orders_filled: int
    orders_cancelled: int
    orders_replaced: int
    fill_count: int
    filled_notional: Decimal
    commissions: Decimal

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["filled_notional"] = str(self.filled_notional)
        data["commissions"] = str(self.commissions)
        return data


class ExecutionManagementSystem:
    """Version 10.0.4 - broker-neutral order lifecycle and execution control."""

    def __init__(
        self,
        broker: BrokerExecutionPort,
        *,
        risk_validator: RiskValidationPort | None = None,
        event_publisher: EventPublisher | None = None,
        config: EMSConfig | None = None,
    ) -> None:
        self.broker = broker
        self.risk_validator = risk_validator
        self.event_publisher = event_publisher
        self.config = config or EMSConfig()
        self._lock = RLock()
        self._orders: dict[str, OrderSnapshot] = {}
        self._client_order_ids: dict[str, str] = {}
        self._events: list[ExecutionEvent] = []
        self._metrics: dict[str, Any] = {
            "orders_created": 0,
            "orders_validated": 0,
            "orders_rejected": 0,
            "orders_submitted": 0,
            "orders_filled": 0,
            "orders_cancelled": 0,
            "orders_replaced": 0,
            "fill_count": 0,
            "filled_notional": Decimal("0"),
            "commissions": Decimal("0"),
        }

    def create_order(self, request: OrderRequest) -> OrderSnapshot:
        with self._lock:
            client_order_id = request.client_order_id or str(uuid.uuid4())
            if (
                self.config.reject_duplicate_client_order_ids
                and client_order_id in self._client_order_ids
            ):
                raise ValueError(f"duplicate client_order_id: {client_order_id}")
            if (
                self.config.maximum_order_quantity is not None
                and request.quantity > self.config.maximum_order_quantity
            ):
                raise ValueError("order quantity exceeds configured maximum")

            now = _utc_now()
            order = OrderSnapshot(
                order_id=str(uuid.uuid4()),
                client_order_id=client_order_id,
                request=replace(request, client_order_id=client_order_id),
                status=OrderStatus.CREATED,
                created_at_utc=now,
                updated_at_utc=now,
            )
            self._orders[order.order_id] = order
            self._client_order_ids[client_order_id] = order.order_id
            self._metrics["orders_created"] += 1
            self._record_event(order, ExecutionEventType.ORDER_CREATED)

        if self.config.auto_submit_after_validation:
            return self.submit_order(order.order_id)
        return order

    def validate_order(self, order_id: str) -> OrderSnapshot:
        with self._lock:
            order = self._require_order(order_id)
            if order.status is OrderStatus.VALIDATED:
                return order
            if order.status is not OrderStatus.CREATED:
                raise ValueError(f"cannot validate order in status {order.status.value}")

        approved, reason = (True, None)
        if self.risk_validator is not None:
            approved, reason = self.risk_validator.validate_order(order)

        with self._lock:
            if approved:
                updated = self._transition(order, OrderStatus.VALIDATED)
                self._metrics["orders_validated"] += 1
                self._record_event(updated, ExecutionEventType.ORDER_VALIDATED, reason)
            else:
                updated = self._transition(order, OrderStatus.REJECTED, last_error=reason)
                self._metrics["orders_rejected"] += 1
                self._record_event(updated, ExecutionEventType.ORDER_REJECTED, reason)
            return updated

    def submit_order(self, order_id: str) -> OrderSnapshot:
        order = self.get_order(order_id)
        if order.status is OrderStatus.CREATED:
            order = self.validate_order(order_id)
        if order.status is OrderStatus.REJECTED:
            return order
        if order.status is not OrderStatus.VALIDATED:
            raise ValueError(f"cannot submit order in status {order.status.value}")

        with self._lock:
            order = self._transition(order, OrderStatus.SUBMITTED)
            self._metrics["orders_submitted"] += 1
            self._record_event(order, ExecutionEventType.ORDER_SUBMITTED)

        started = time.perf_counter()
        try:
            result = self.broker.submit_order(order)
        except Exception as exc:
            return self.mark_error(order_id, f"broker submission failed: {exc}")

        latency_ms = (time.perf_counter() - started) * 1000
        with self._lock:
            current = self._require_order(order_id)
            if not result.accepted:
                rejected = self._transition(
                    current,
                    OrderStatus.REJECTED,
                    broker_order_id=result.broker_order_id,
                    last_error=result.message,
                )
                self._metrics["orders_rejected"] += 1
                self._record_event(
                    rejected,
                    ExecutionEventType.ORDER_REJECTED,
                    result.message,
                    {"latency_ms": latency_ms, **dict(result.metadata)},
                )
                return rejected

            acknowledged_status = (
                OrderStatus.ACKNOWLEDGED if result.acknowledged else OrderStatus.SUBMITTED
            )
            acknowledged = self._transition(
                current,
                acknowledged_status,
                broker_order_id=result.broker_order_id,
            ) if acknowledged_status is not current.status else replace(
                current,
                broker_order_id=result.broker_order_id,
                updated_at_utc=_utc_now(),
                version=current.version + 1,
            )
            self._orders[order_id] = acknowledged
            if result.acknowledged:
                self._record_event(
                    acknowledged,
                    ExecutionEventType.ORDER_ACKNOWLEDGED,
                    result.message,
                    {"latency_ms": latency_ms, **dict(result.metadata)},
                )
            return acknowledged

    def acknowledge_order(self, order_id: str, broker_order_id: str | None = None) -> OrderSnapshot:
        with self._lock:
            order = self._require_order(order_id)
            updated = self._transition(
                order,
                OrderStatus.ACKNOWLEDGED,
                broker_order_id=broker_order_id or order.broker_order_id,
            )
            self._record_event(updated, ExecutionEventType.ORDER_ACKNOWLEDGED)
            return updated

    def record_fill(self, order_id: str, fill: Fill) -> OrderSnapshot:
        with self._lock:
            order = self._require_order(order_id)
            if order.is_terminal:
                raise ValueError("cannot fill a terminal order")
            if fill.order_id != order_id:
                raise ValueError("fill order_id does not match target order")
            if any(existing.fill_id == fill.fill_id for existing in order.fills):
                raise ValueError(f"duplicate fill_id: {fill.fill_id}")
            if fill.quantity > order.remaining_quantity:
                raise ValueError("fill quantity exceeds remaining order quantity")

            previous_notional = (
                (order.average_fill_price or Decimal("0")) * order.filled_quantity
            )
            new_filled_quantity = order.filled_quantity + fill.quantity
            new_notional = previous_notional + fill.price * fill.quantity
            average_fill_price = _money(new_notional / new_filled_quantity)
            new_status = (
                OrderStatus.FILLED
                if new_filled_quantity == order.request.quantity
                else OrderStatus.PARTIALLY_FILLED
            )
            updated = self._transition(
                order,
                new_status,
                filled_quantity=new_filled_quantity,
                average_fill_price=average_fill_price,
                commission_total=order.commission_total + fill.commission,
                fills=order.fills + (fill,),
            )
            self._metrics["fill_count"] += 1
            self._metrics["filled_notional"] += fill.price * fill.quantity
            self._metrics["commissions"] += fill.commission
            event_type = (
                ExecutionEventType.ORDER_FILLED
                if new_status is OrderStatus.FILLED
                else ExecutionEventType.ORDER_PARTIALLY_FILLED
            )
            if new_status is OrderStatus.FILLED:
                self._metrics["orders_filled"] += 1
            self._record_event(updated, event_type, payload={"fill": fill.to_dict()})
            return updated

    def cancel_order(self, order_id: str) -> OrderSnapshot:
        with self._lock:
            order = self._require_order(order_id)
            if order.is_terminal:
                raise ValueError("cannot cancel a terminal order")
            pending = self._transition(order, OrderStatus.CANCEL_PENDING)
            self._record_event(pending, ExecutionEventType.ORDER_CANCEL_REQUESTED)

        try:
            result = self.broker.cancel_order(pending)
        except Exception as exc:
            return self.mark_error(order_id, f"broker cancellation failed: {exc}")

        with self._lock:
            current = self._require_order(order_id)
            if not result.accepted:
                return self.mark_error(order_id, result.message or "cancel rejected")
            cancelled = self._transition(current, OrderStatus.CANCELLED)
            self._metrics["orders_cancelled"] += 1
            self._record_event(
                cancelled,
                ExecutionEventType.ORDER_CANCELLED,
                result.message,
                dict(result.metadata),
            )
            return cancelled

    def replace_order(self, order_id: str, new_request: OrderRequest) -> OrderSnapshot:
        with self._lock:
            order = self._require_order(order_id)
            if order.is_terminal:
                raise ValueError("cannot replace a terminal order")
            if new_request.symbol != order.request.symbol or new_request.side != order.request.side:
                raise ValueError("replacement cannot change symbol or side")
            if new_request.quantity < order.filled_quantity:
                raise ValueError("replacement quantity cannot be below filled quantity")
            pending = self._transition(order, OrderStatus.REPLACE_PENDING)
            self._record_event(pending, ExecutionEventType.ORDER_REPLACE_REQUESTED)

        try:
            result = self.broker.replace_order(pending, new_request)
        except Exception as exc:
            return self.mark_error(order_id, f"broker replacement failed: {exc}")

        with self._lock:
            current = self._require_order(order_id)
            if not result.accepted:
                return self.mark_error(order_id, result.message or "replace rejected")
            replacement = replace(
                current,
                request=replace(new_request, client_order_id=current.client_order_id),
                broker_order_id=result.broker_order_id or current.broker_order_id,
            )
            replacement = self._transition(replacement, OrderStatus.REPLACED)
            self._metrics["orders_replaced"] += 1
            self._record_event(
                replacement,
                ExecutionEventType.ORDER_REPLACED,
                result.message,
                dict(result.metadata),
            )
            return replacement

    def expire_order(self, order_id: str, reason: str | None = None) -> OrderSnapshot:
        with self._lock:
            order = self._require_order(order_id)
            updated = self._transition(order, OrderStatus.EXPIRED, last_error=reason)
            self._record_event(updated, ExecutionEventType.ORDER_EXPIRED, reason)
            return updated

    def mark_error(self, order_id: str, message: str) -> OrderSnapshot:
        with self._lock:
            order = self._require_order(order_id)
            if order.status is OrderStatus.ERROR:
                return order
            updated = self._transition(order, OrderStatus.ERROR, last_error=message)
            self._record_event(updated, ExecutionEventType.ORDER_ERROR, message)
            return updated

    def get_order(self, order_id: str) -> OrderSnapshot:
        with self._lock:
            return self._require_order(order_id)

    def get_order_by_client_id(self, client_order_id: str) -> OrderSnapshot:
        with self._lock:
            order_id = self._client_order_ids.get(client_order_id)
            if order_id is None:
                raise KeyError(f"unknown client_order_id: {client_order_id}")
            return self._orders[order_id]

    def list_orders(
        self,
        *,
        statuses: Sequence[OrderStatus] | None = None,
        symbol: str | None = None,
        strategy_id: str | None = None,
        limit: int | None = None,
    ) -> tuple[OrderSnapshot, ...]:
        with self._lock:
            orders = list(self._orders.values())
        if statuses is not None:
            allowed = set(statuses)
            orders = [order for order in orders if order.status in allowed]
        if symbol is not None:
            normalized = symbol.strip().upper()
            orders = [order for order in orders if order.request.symbol == normalized]
        if strategy_id is not None:
            orders = [order for order in orders if order.request.strategy_id == strategy_id]
        orders.sort(key=lambda item: item.created_at_utc)
        if limit is not None:
            orders = orders[-limit:]
        return tuple(orders)

    def event_history(
        self,
        *,
        order_id: str | None = None,
        limit: int | None = None,
    ) -> tuple[ExecutionEvent, ...]:
        with self._lock:
            events = list(self._events)
        if order_id is not None:
            events = [event for event in events if event.order_id == order_id]
        if limit is not None:
            events = events[-limit:]
        return tuple(events)

    def metrics(self) -> EMSMetrics:
        with self._lock:
            return EMSMetrics(**self._metrics)

    def health_check(self) -> dict[str, Any]:
        with self._lock:
            active = sum(1 for order in self._orders.values() if not order.is_terminal)
            errors = sum(1 for order in self._orders.values() if order.status is OrderStatus.ERROR)
            return {
                "healthy": errors == 0,
                "total_orders": len(self._orders),
                "active_orders": active,
                "error_orders": errors,
                "event_count": len(self._events),
                "metrics": self.metrics().to_dict(),
            }

    def _transition(self, order: OrderSnapshot, new_status: OrderStatus, **changes: Any) -> OrderSnapshot:
        if order.status == new_status:
            updated = replace(
                order,
                updated_at_utc=_utc_now(),
                version=order.version + 1,
                **changes,
            )
            self._orders[order.order_id] = updated
            return updated
        allowed = ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"invalid order transition: {order.status.value} -> {new_status.value}"
            )
        updated = replace(
            order,
            status=new_status,
            updated_at_utc=_utc_now(),
            version=order.version + 1,
            **changes,
        )
        self._orders[order.order_id] = updated
        return updated

    def _record_event(
        self,
        order: OrderSnapshot,
        event_type: ExecutionEventType,
        message: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        event = ExecutionEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            order_id=order.order_id,
            timestamp_utc=_utc_now(),
            status=order.status,
            message=message,
            payload=payload or {},
        )
        self._events.append(event)
        if len(self._events) > self.config.history_capacity:
            del self._events[: len(self._events) - self.config.history_capacity]
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                f"execution.{event_type.value.lower()}",
                {"event": event.to_dict(), "order": order.to_dict()},
                source="execution_management_system",
            )

    def _require_order(self, order_id: str) -> OrderSnapshot:
        try:
            return self._orders[order_id]
        except KeyError as exc:
            raise KeyError(f"unknown order_id: {order_id}") from exc
