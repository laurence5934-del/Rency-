from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Mapping, Protocol, Sequence


class BrokerStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"


class AssetClass(str, Enum):
    EQUITY = "EQUITY"
    OPTION = "OPTION"
    FUTURE = "FUTURE"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"


class BrokerOrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"


class BrokerOrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class BrokerTimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class BrokerOrderStatus(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class BrokerCapabilities:
    asset_classes: frozenset[AssetClass]
    order_types: frozenset[BrokerOrderType]
    time_in_force: frozenset[BrokerTimeInForce]
    supports_fractional_shares: bool = False
    supports_extended_hours: bool = False
    supports_bracket_orders: bool = False
    supports_trailing_stops: bool = False
    supports_short_selling: bool = False
    supports_order_replace: bool = True

    def supports_order(self, request: "BrokerOrderRequest") -> bool:
        if request.asset_class not in self.asset_classes:
            return False
        if request.order_type not in self.order_types:
            return False
        if request.time_in_force not in self.time_in_force:
            return False
        if request.extended_hours and not self.supports_extended_hours:
            return False
        if request.side == BrokerOrderSide.SELL_SHORT and not self.supports_short_selling:
            return False
        if request.order_type == BrokerOrderType.TRAILING_STOP and not self.supports_trailing_stops:
            return False
        if not self.supports_fractional_shares and request.quantity != int(request.quantity):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_classes": sorted(item.value for item in self.asset_classes),
            "order_types": sorted(item.value for item in self.order_types),
            "time_in_force": sorted(item.value for item in self.time_in_force),
            "supports_fractional_shares": self.supports_fractional_shares,
            "supports_extended_hours": self.supports_extended_hours,
            "supports_bracket_orders": self.supports_bracket_orders,
            "supports_trailing_stops": self.supports_trailing_stops,
            "supports_short_selling": self.supports_short_selling,
            "supports_order_replace": self.supports_order_replace,
        }


@dataclass(frozen=True, slots=True)
class BrokerAccount:
    broker: str
    account_id: str
    currency: str
    cash: float
    buying_power: float
    equity: float
    maintenance_margin: float = 0.0
    initial_margin: float = 0.0
    day_trade_buying_power: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.broker.strip() or not self.account_id.strip():
            raise ValueError("broker and account_id cannot be empty")
        if not self.currency.strip():
            raise ValueError("currency cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BrokerPosition:
    broker: str
    account_id: str
    symbol: str
    asset_class: AssetClass
    quantity: float
    average_price: float
    market_price: float | None = None
    unrealized_pnl: float | None = None
    realized_pnl: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.average_price < 0:
            raise ValueError("average_price cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["asset_class"] = self.asset_class.value
        return data


@dataclass(frozen=True, slots=True)
class BrokerOrderRequest:
    client_order_id: str
    symbol: str
    asset_class: AssetClass
    side: BrokerOrderSide
    order_type: BrokerOrderType
    quantity: float
    time_in_force: BrokerTimeInForce = BrokerTimeInForce.DAY
    limit_price: float | None = None
    stop_price: float | None = None
    trail_amount: float | None = None
    extended_hours: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.client_order_id.strip():
            raise ValueError("client_order_id cannot be empty")
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type in {BrokerOrderType.LIMIT, BrokerOrderType.STOP_LIMIT}:
            if self.limit_price is None or self.limit_price <= 0:
                raise ValueError("positive limit_price is required")
        if self.order_type in {BrokerOrderType.STOP, BrokerOrderType.STOP_LIMIT}:
            if self.stop_price is None or self.stop_price <= 0:
                raise ValueError("positive stop_price is required")
        if self.order_type == BrokerOrderType.TRAILING_STOP:
            if self.trail_amount is None or self.trail_amount <= 0:
                raise ValueError("positive trail_amount is required")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["asset_class"] = self.asset_class.value
        data["side"] = self.side.value
        data["order_type"] = self.order_type.value
        data["time_in_force"] = self.time_in_force.value
        return data


@dataclass(frozen=True, slots=True)
class BrokerOrder:
    broker: str
    account_id: str
    broker_order_id: str
    client_order_id: str
    symbol: str
    side: BrokerOrderSide
    order_type: BrokerOrderType
    quantity: float
    filled_quantity: float
    status: BrokerOrderStatus
    submitted_at_utc: str
    updated_at_utc: str
    average_fill_price: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None
    commission: float = 0.0
    reject_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if not 0 <= self.filled_quantity <= self.quantity:
            raise ValueError("filled_quantity is outside valid range")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["side"] = self.side.value
        data["order_type"] = self.order_type.value
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class BrokerExecution:
    broker: str
    account_id: str
    broker_order_id: str
    execution_id: str
    symbol: str
    quantity: float
    price: float
    commission: float
    timestamp_utc: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.price <= 0:
            raise ValueError("execution quantity and price must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BrokerAdapter(Protocol):
    name: str

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    def health_check(self) -> Mapping[str, Any]: ...
    def capabilities(self) -> BrokerCapabilities: ...
    def get_account(self, account_id: str | None = None) -> BrokerAccount: ...
    def get_positions(self, account_id: str | None = None) -> Sequence[BrokerPosition]: ...
    def submit_order(
        self,
        request: BrokerOrderRequest,
        account_id: str | None = None,
    ) -> BrokerOrder: ...
    def cancel_order(
        self,
        broker_order_id: str,
        account_id: str | None = None,
    ) -> BrokerOrder: ...
    def replace_order(
        self,
        broker_order_id: str,
        request: BrokerOrderRequest,
        account_id: str | None = None,
    ) -> BrokerOrder: ...
    def get_order(
        self,
        broker_order_id: str,
        account_id: str | None = None,
    ) -> BrokerOrder: ...
    def list_open_orders(self, account_id: str | None = None) -> Sequence[BrokerOrder]: ...
    def list_executions(
        self,
        account_id: str | None = None,
        since_utc: str | None = None,
    ) -> Sequence[BrokerExecution]: ...


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
class BrokerRuntime:
    name: str
    enabled: bool = True
    status: BrokerStatus = BrokerStatus.DISCONNECTED
    consecutive_failures: int = 0
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_latency_ms: float = 0.0
    last_connected_utc: str | None = None
    last_success_utc: str | None = None
    last_failure_utc: str | None = None
    last_error: str | None = None

    def record_success(self, latency_ms: float) -> None:
        self.request_count += 1
        self.success_count += 1
        self.consecutive_failures = 0
        self.last_success_utc = datetime.now(timezone.utc).isoformat()
        self.average_latency_ms += (
            latency_ms - self.average_latency_ms
        ) / self.request_count
        self.status = BrokerStatus.CONNECTED if self.enabled else BrokerStatus.DISABLED

    def record_failure(self, error: str, failure_threshold: int) -> None:
        self.request_count += 1
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure_utc = datetime.now(timezone.utc).isoformat()
        self.last_error = error
        if not self.enabled:
            self.status = BrokerStatus.DISABLED
        elif self.consecutive_failures >= failure_threshold:
            self.status = BrokerStatus.UNAVAILABLE
        else:
            self.status = BrokerStatus.DEGRADED

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(slots=True)
class BrokerAbstractionConfig:
    auto_connect: bool = True
    auto_reconnect: bool = True
    allow_failover_for_reads: bool = True
    allow_failover_for_orders: bool = False
    failure_threshold: int = 3
    publish_events: bool = True

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be positive")


class BrokerAbstractionLayer:
    """
    Version 10.0.5 - Broker Abstraction Layer.

    Provides one broker-neutral interface for:
    connection lifecycle, capability discovery, account/position retrieval,
    order routing, cancellation, replacement, order synchronization,
    execution retrieval, health monitoring, metrics, and optional failover.
    """

    def __init__(
        self,
        *,
        config: BrokerAbstractionConfig | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.config = config or BrokerAbstractionConfig()
        self.event_publisher = event_publisher
        self._lock = RLock()
        self._adapters: dict[str, BrokerAdapter] = {}
        self._runtime: dict[str, BrokerRuntime] = {}
        self._priority: list[str] = []
        self._metrics: dict[str, int] = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "read_failovers": 0,
            "order_failovers": 0,
            "connects": 0,
            "disconnects": 0,
        }

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def register_broker(
        self,
        adapter: BrokerAdapter,
        *,
        priority: int | None = None,
        enabled: bool = True,
    ) -> None:
        name = adapter.name.strip()
        if not name:
            raise ValueError("broker name cannot be empty")
        with self._lock:
            if name in self._adapters:
                raise ValueError(f"broker already registered: {name}")
            self._adapters[name] = adapter
            self._runtime[name] = BrokerRuntime(
                name=name,
                enabled=enabled,
                status=BrokerStatus.DISCONNECTED if enabled else BrokerStatus.DISABLED,
            )
            if priority is None or priority >= len(self._priority):
                self._priority.append(name)
            else:
                self._priority.insert(max(priority, 0), name)

        if enabled and self.config.auto_connect:
            self.connect(name)

    def unregister_broker(self, name: str, *, disconnect: bool = True) -> bool:
        with self._lock:
            adapter = self._adapters.get(name)
        if adapter is None:
            return False
        if disconnect:
            try:
                self.disconnect(name)
            except Exception:
                pass
        with self._lock:
            self._adapters.pop(name, None)
            self._runtime.pop(name, None)
            self._priority = [item for item in self._priority if item != name]
        return True

    def enable_broker(self, name: str, enabled: bool = True) -> None:
        with self._lock:
            runtime = self._require_runtime(name)
            runtime.enabled = enabled
            runtime.status = (
                BrokerStatus.DISCONNECTED if enabled else BrokerStatus.DISABLED
            )
        if enabled and self.config.auto_connect:
            self.connect(name)
        elif not enabled:
            self.disconnect(name)

    def set_priority(self, names: Sequence[str]) -> None:
        with self._lock:
            unknown = [name for name in names if name not in self._adapters]
            if unknown:
                raise KeyError(f"unknown brokers: {unknown}")
            remaining = [name for name in self._priority if name not in names]
            self._priority = list(names) + remaining

    def connect(self, name: str) -> None:
        adapter = self._require_adapter(name)
        runtime = self._require_runtime(name)
        if not runtime.enabled:
            raise RuntimeError(f"broker is disabled: {name}")

        runtime.status = BrokerStatus.CONNECTING
        started = time.perf_counter()
        try:
            adapter.connect()
            if not adapter.is_connected():
                raise RuntimeError("adapter did not report a connected state")
            latency = (time.perf_counter() - started) * 1000
            runtime.record_success(latency)
            runtime.last_connected_utc = self._utc_now()
            self._metrics["connects"] += 1
            self._publish("broker.connected", {"broker": name})
        except Exception as exc:
            runtime.record_failure(str(exc), self.config.failure_threshold)
            self._metrics["failures"] += 1
            self._publish(
                "broker.connection_failed",
                {"broker": name, "error": str(exc)},
            )
            raise

    def disconnect(self, name: str) -> None:
        adapter = self._require_adapter(name)
        runtime = self._require_runtime(name)
        try:
            adapter.disconnect()
        finally:
            runtime.status = (
                BrokerStatus.DISCONNECTED if runtime.enabled else BrokerStatus.DISABLED
            )
            self._metrics["disconnects"] += 1
            self._publish("broker.disconnected", {"broker": name})

    def capabilities(self, name: str) -> BrokerCapabilities:
        return self._invoke_single(name, "capabilities", lambda adapter: adapter.capabilities())

    def get_account(
        self,
        *,
        broker_name: str | None = None,
        account_id: str | None = None,
    ) -> BrokerAccount:
        return self._invoke_read(
            broker_name,
            "get_account",
            lambda adapter: adapter.get_account(account_id),
        )

    def get_positions(
        self,
        *,
        broker_name: str | None = None,
        account_id: str | None = None,
    ) -> tuple[BrokerPosition, ...]:
        result = self._invoke_read(
            broker_name,
            "get_positions",
            lambda adapter: tuple(adapter.get_positions(account_id)),
        )
        return tuple(result)

    def submit_order(
        self,
        request: BrokerOrderRequest,
        *,
        broker_name: str | None = None,
        account_id: str | None = None,
    ) -> BrokerOrder:
        candidates = self._candidate_names(
            broker_name,
            allow_failover=self.config.allow_failover_for_orders,
        )
        last_error: Exception | None = None

        for index, name in enumerate(candidates):
            try:
                capabilities = self.capabilities(name)
                if not capabilities.supports_order(request):
                    raise ValueError(
                        f"broker {name} does not support this order request"
                    )
                order = self._invoke_single(
                    name,
                    "submit_order",
                    lambda adapter: adapter.submit_order(request, account_id),
                )
                if index > 0:
                    self._metrics["order_failovers"] += 1
                self._publish("broker.order_submitted", order.to_dict())
                return order
            except Exception as exc:
                last_error = exc
                if not self.config.allow_failover_for_orders:
                    break

        raise RuntimeError(f"order submission failed: {last_error}") from last_error

    def cancel_order(
        self,
        broker_name: str,
        broker_order_id: str,
        *,
        account_id: str | None = None,
    ) -> BrokerOrder:
        order = self._invoke_single(
            broker_name,
            "cancel_order",
            lambda adapter: adapter.cancel_order(broker_order_id, account_id),
        )
        self._publish("broker.order_cancelled", order.to_dict())
        return order

    def replace_order(
        self,
        broker_name: str,
        broker_order_id: str,
        request: BrokerOrderRequest,
        *,
        account_id: str | None = None,
    ) -> BrokerOrder:
        capabilities = self.capabilities(broker_name)
        if not capabilities.supports_order_replace:
            raise RuntimeError(f"broker {broker_name} does not support order replacement")
        if not capabilities.supports_order(request):
            raise ValueError(f"broker {broker_name} does not support replacement request")
        order = self._invoke_single(
            broker_name,
            "replace_order",
            lambda adapter: adapter.replace_order(
                broker_order_id, request, account_id
            ),
        )
        self._publish("broker.order_replaced", order.to_dict())
        return order

    def get_order(
        self,
        broker_name: str,
        broker_order_id: str,
        *,
        account_id: str | None = None,
    ) -> BrokerOrder:
        return self._invoke_single(
            broker_name,
            "get_order",
            lambda adapter: adapter.get_order(broker_order_id, account_id),
        )

    def list_open_orders(
        self,
        broker_name: str,
        *,
        account_id: str | None = None,
    ) -> tuple[BrokerOrder, ...]:
        result = self._invoke_single(
            broker_name,
            "list_open_orders",
            lambda adapter: tuple(adapter.list_open_orders(account_id)),
        )
        return tuple(result)

    def list_executions(
        self,
        broker_name: str,
        *,
        account_id: str | None = None,
        since_utc: str | None = None,
    ) -> tuple[BrokerExecution, ...]:
        result = self._invoke_single(
            broker_name,
            "list_executions",
            lambda adapter: tuple(adapter.list_executions(account_id, since_utc)),
        )
        return tuple(result)

    def synchronize_order(
        self,
        broker_name: str,
        broker_order_id: str,
        *,
        account_id: str | None = None,
    ) -> BrokerOrder:
        order = self.get_order(
            broker_name,
            broker_order_id,
            account_id=account_id,
        )
        self._publish("broker.order_synchronized", order.to_dict())
        return order

    def health_check(self) -> dict[str, Any]:
        broker_health: dict[str, Any] = {}
        with self._lock:
            names = list(self._priority)

        for name in names:
            runtime = self._require_runtime(name)
            adapter = self._require_adapter(name)
            adapter_health: Mapping[str, Any]
            try:
                adapter_health = adapter.health_check()
                if runtime.enabled and adapter.is_connected():
                    runtime.status = BrokerStatus.CONNECTED
            except Exception as exc:
                adapter_health = {"healthy": False, "error": str(exc)}
                runtime.record_failure(str(exc), self.config.failure_threshold)

            broker_health[name] = {
                **runtime.to_dict(),
                "adapter_health": dict(adapter_health),
                "capabilities": self.capabilities(name).to_dict()
                if runtime.enabled and runtime.status != BrokerStatus.UNAVAILABLE
                else None,
            }

        available = [
            item
            for item in broker_health.values()
            if item["enabled"] and item["status"] in {
                BrokerStatus.CONNECTED.value,
                BrokerStatus.DEGRADED.value,
            }
        ]
        return {
            "healthy": bool(available),
            "registered_brokers": len(broker_health),
            "available_brokers": len(available),
            "brokers": broker_health,
            "metrics": self.metrics(),
        }

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return dict(self._metrics)

    def _invoke_read(
        self,
        broker_name: str | None,
        operation: str,
        action: Any,
    ) -> Any:
        candidates = self._candidate_names(
            broker_name,
            allow_failover=self.config.allow_failover_for_reads,
        )
        last_error: Exception | None = None

        for index, name in enumerate(candidates):
            try:
                result = self._invoke_single(name, operation, action)
                if index > 0:
                    self._metrics["read_failovers"] += 1
                return result
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"{operation} failed: {last_error}") from last_error

    def _invoke_single(
        self,
        name: str,
        operation: str,
        action: Any,
    ) -> Any:
        adapter = self._require_adapter(name)
        runtime = self._require_runtime(name)
        if not runtime.enabled:
            raise RuntimeError(f"broker is disabled: {name}")

        if not adapter.is_connected():
            if not self.config.auto_reconnect:
                raise RuntimeError(f"broker is disconnected: {name}")
            self.connect(name)

        started = time.perf_counter()
        self._metrics["requests"] += 1
        try:
            result = action(adapter)
            latency = (time.perf_counter() - started) * 1000
            runtime.record_success(latency)
            self._metrics["successes"] += 1
            return result
        except Exception as exc:
            runtime.record_failure(str(exc), self.config.failure_threshold)
            self._metrics["failures"] += 1
            self._publish(
                "broker.operation_failed",
                {
                    "broker": name,
                    "operation": operation,
                    "error": str(exc),
                },
            )
            raise

    def _candidate_names(
        self,
        requested: str | None,
        *,
        allow_failover: bool,
    ) -> list[str]:
        with self._lock:
            if requested is not None:
                if requested not in self._adapters:
                    raise KeyError(f"unknown broker: {requested}")
                if not self._runtime[requested].enabled:
                    return []
                if not allow_failover:
                    return [requested]
                remaining = [
                    name
                    for name in self._priority
                    if name != requested
                    and self._runtime[name].enabled
                    and self._runtime[name].status != BrokerStatus.UNAVAILABLE
                ]
                return [requested] + remaining

            candidates = [
                name
                for name in self._priority
                if self._runtime[name].enabled
                and self._runtime[name].status != BrokerStatus.UNAVAILABLE
            ]
            return candidates if allow_failover else candidates[:1]

    def _require_adapter(self, name: str) -> BrokerAdapter:
        with self._lock:
            adapter = self._adapters.get(name)
        if adapter is None:
            raise KeyError(f"unknown broker: {name}")
        return adapter

    def _require_runtime(self, name: str) -> BrokerRuntime:
        with self._lock:
            runtime = self._runtime.get(name)
        if runtime is None:
            raise KeyError(f"unknown broker: {name}")
        return runtime

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="broker_abstraction_layer",
            )


class PaperBrokerAdapter:
    """
    Deterministic in-memory adapter for unit tests, integration tests,
    simulations, and paper-trading development.
    """

    name = "paper"

    def __init__(
        self,
        *,
        account_id: str = "PAPER-001",
        starting_cash: float = 100_000.0,
    ) -> None:
        self._connected = False
        self._account_id = account_id
        self._cash = starting_cash
        self._orders: dict[str, BrokerOrder] = {}
        self._positions: dict[str, BrokerPosition] = {}
        self._executions: list[BrokerExecution] = []
        self._lock = RLock()

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def health_check(self) -> Mapping[str, Any]:
        return {
            "healthy": self._connected,
            "mode": "paper",
            "orders": len(self._orders),
            "positions": len(self._positions),
        }

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            asset_classes=frozenset({AssetClass.EQUITY, AssetClass.CRYPTO}),
            order_types=frozenset(BrokerOrderType),
            time_in_force=frozenset(BrokerTimeInForce),
            supports_fractional_shares=True,
            supports_extended_hours=True,
            supports_bracket_orders=False,
            supports_trailing_stops=True,
            supports_short_selling=True,
            supports_order_replace=True,
        )

    def get_account(self, account_id: str | None = None) -> BrokerAccount:
        self._ensure_connected()
        resolved = account_id or self._account_id
        equity = self._cash
        for position in self._positions.values():
            price = position.market_price or position.average_price
            equity += position.quantity * price
        return BrokerAccount(
            broker=self.name,
            account_id=resolved,
            currency="USD",
            cash=self._cash,
            buying_power=self._cash,
            equity=equity,
        )

    def get_positions(self, account_id: str | None = None) -> Sequence[BrokerPosition]:
        self._ensure_connected()
        return tuple(self._positions.values())

    def submit_order(
        self,
        request: BrokerOrderRequest,
        account_id: str | None = None,
    ) -> BrokerOrder:
        self._ensure_connected()
        now = datetime.now(timezone.utc).isoformat()
        order = BrokerOrder(
            broker=self.name,
            account_id=account_id or self._account_id,
            broker_order_id=str(uuid.uuid4()),
            client_order_id=request.client_order_id,
            symbol=request.symbol.upper(),
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            filled_quantity=0.0,
            status=BrokerOrderStatus.ACKNOWLEDGED,
            submitted_at_utc=now,
            updated_at_utc=now,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
        )
        with self._lock:
            self._orders[order.broker_order_id] = order
        return order

    def cancel_order(
        self,
        broker_order_id: str,
        account_id: str | None = None,
    ) -> BrokerOrder:
        self._ensure_connected()
        with self._lock:
            current = self._orders[broker_order_id]
            if current.status in {
                BrokerOrderStatus.FILLED,
                BrokerOrderStatus.CANCELLED,
                BrokerOrderStatus.REJECTED,
                BrokerOrderStatus.EXPIRED,
            }:
                raise RuntimeError(f"order cannot be cancelled from {current.status.value}")
            updated = BrokerOrder(
                **{
                    **current.to_dict(),
                    "side": current.side,
                    "order_type": current.order_type,
                    "status": BrokerOrderStatus.CANCELLED,
                    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._orders[broker_order_id] = updated
            return updated

    def replace_order(
        self,
        broker_order_id: str,
        request: BrokerOrderRequest,
        account_id: str | None = None,
    ) -> BrokerOrder:
        self._ensure_connected()
        with self._lock:
            current = self._orders[broker_order_id]
            if current.status not in {
                BrokerOrderStatus.SUBMITTED,
                BrokerOrderStatus.ACKNOWLEDGED,
                BrokerOrderStatus.PARTIALLY_FILLED,
            }:
                raise RuntimeError(f"order cannot be replaced from {current.status.value}")
            updated = BrokerOrder(
                broker=current.broker,
                account_id=current.account_id,
                broker_order_id=current.broker_order_id,
                client_order_id=request.client_order_id,
                symbol=request.symbol.upper(),
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                filled_quantity=current.filled_quantity,
                status=BrokerOrderStatus.ACKNOWLEDGED,
                submitted_at_utc=current.submitted_at_utc,
                updated_at_utc=datetime.now(timezone.utc).isoformat(),
                average_fill_price=current.average_fill_price,
                limit_price=request.limit_price,
                stop_price=request.stop_price,
                commission=current.commission,
                metadata=current.metadata,
            )
            self._orders[broker_order_id] = updated
            return updated

    def get_order(
        self,
        broker_order_id: str,
        account_id: str | None = None,
    ) -> BrokerOrder:
        self._ensure_connected()
        return self._orders[broker_order_id]

    def list_open_orders(self, account_id: str | None = None) -> Sequence[BrokerOrder]:
        self._ensure_connected()
        open_statuses = {
            BrokerOrderStatus.CREATED,
            BrokerOrderStatus.SUBMITTED,
            BrokerOrderStatus.ACKNOWLEDGED,
            BrokerOrderStatus.PARTIALLY_FILLED,
            BrokerOrderStatus.CANCEL_PENDING,
        }
        return tuple(
            order for order in self._orders.values()
            if order.status in open_statuses
        )

    def list_executions(
        self,
        account_id: str | None = None,
        since_utc: str | None = None,
    ) -> Sequence[BrokerExecution]:
        self._ensure_connected()
        if since_utc is None:
            return tuple(self._executions)
        return tuple(
            execution
            for execution in self._executions
            if execution.timestamp_utc >= since_utc
        )

    def _ensure_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("paper broker is disconnected")
