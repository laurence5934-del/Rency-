from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from itertools import count
from typing import Callable, Protocol

from .execution_models import (
    ExecutionOrderType,
    ExecutionReceipt,
    ExecutionReport,
    ExecutionRequest,
    ExecutionSide,
    ExecutionStatus,
)


_ZERO = Decimal("0")


class BrokerAdapter(Protocol):
    """Contract implemented by broker-specific adapters."""

    @property
    def name(self) -> str:
        """Return the broker name."""
        ...

    def execute(
        self,
        request: ExecutionRequest,
    ) -> ExecutionReceipt:
        """Execute one broker-neutral request."""
        ...


class ExecutionGateway:
    """Validates and routes orders through a broker adapter."""

    def __init__(
        self,
        *,
        adapter: BrokerAdapter,
    ) -> None:
        if not hasattr(adapter, "execute"):
            raise TypeError(
                "adapter must provide an execute method"
            )

        if not hasattr(adapter, "name"):
            raise TypeError(
                "adapter must provide a name"
            )

        self._adapter = adapter

    def submit(
        self,
        request: ExecutionRequest,
    ) -> ExecutionReport:
        if not isinstance(
            request,
            ExecutionRequest,
        ):
            raise TypeError(
                "request must be an ExecutionRequest"
            )

        try:
            receipt = self._adapter.execute(request)

            if not isinstance(
                receipt,
                ExecutionReceipt,
            ):
                raise TypeError(
                    "adapter execute must return ExecutionReceipt"
                )

            if receipt.execution_id != request.execution_id:
                raise ValueError(
                    "adapter receipt execution_id must match request"
                )

            if receipt.filled_quantity > request.quantity:
                raise ValueError(
                    "filled quantity must not exceed "
                    "requested quantity"
                )

            warnings: list[str] = []

            if receipt.filled_quantity < request.quantity:
                warnings.append(
                    "The execution was partially filled."
                )

            return ExecutionReport(
                status=ExecutionStatus.COMPLETED,
                request=request,
                receipt=receipt,
                warnings=tuple(warnings),
            )

        except Exception as exc:
            return ExecutionReport(
                status=ExecutionStatus.FAILED,
                request=request,
                receipt=None,
                warnings=(
                    "Broker execution did not complete.",
                ),
                error=str(exc),
            )


PriceProvider = Callable[[str], Decimal]
Clock = Callable[[], datetime]


class SimulatorBrokerAdapter:
    """Deterministic in-memory broker simulator."""

    def __init__(
        self,
        *,
        price_provider: PriceProvider,
        commission_per_order: Decimal = Decimal("0"),
        clock: Clock | None = None,
    ) -> None:
        if not callable(price_provider):
            raise TypeError(
                "price_provider must be callable"
            )

        if not isinstance(
            commission_per_order,
            Decimal,
        ):
            raise TypeError(
                "commission_per_order must be a Decimal"
            )

        if commission_per_order < _ZERO:
            raise ValueError(
                "commission_per_order must not be negative"
            )

        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._price_provider = price_provider
        self._commission_per_order = (
            commission_per_order
        )
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )
        self._order_sequence = count(1)

    @property
    def name(self) -> str:
        return "SIMULATOR"

    def execute(
        self,
        request: ExecutionRequest,
    ) -> ExecutionReceipt:
        if not isinstance(
            request,
            ExecutionRequest,
        ):
            raise TypeError(
                "request must be an ExecutionRequest"
            )

        market_price = self._price_provider(
            request.symbol
        )

        if not isinstance(market_price, Decimal):
            raise TypeError(
                "price_provider must return a Decimal"
            )

        if market_price <= _ZERO:
            raise ValueError(
                "market price must be greater than zero"
            )

        execution_price = self._execution_price(
            request=request,
            market_price=market_price,
        )

        executed_at = self._clock()

        if not isinstance(executed_at, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        if executed_at.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware datetime"
            )

        order_number = next(self._order_sequence)

        return ExecutionReceipt(
            execution_id=request.execution_id,
            broker_name=self.name,
            order_id=f"SIM-{order_number:06d}",
            filled_quantity=request.quantity,
            average_price=execution_price,
            commission=self._commission_per_order,
            executed_at=executed_at,
        )

    @staticmethod
    def _execution_price(
        *,
        request: ExecutionRequest,
        market_price: Decimal,
    ) -> Decimal:
        if (
            request.order_type
            is ExecutionOrderType.MARKET
        ):
            return market_price

        assert request.limit_price is not None

        if request.side is ExecutionSide.BUY:
            if market_price > request.limit_price:
                raise ValueError(
                    "buy limit price has not been reached"
                )

        if request.side is ExecutionSide.SELL:
            if market_price < request.limit_price:
                raise ValueError(
                    "sell limit price has not been reached"
                )

        return market_price


class UnavailableBrokerAdapter:
    """Safe placeholder for an unconfigured live broker."""

    def __init__(
        self,
        *,
        broker_name: str,
    ) -> None:
        normalized_name = broker_name.strip()

        if not normalized_name:
            raise ValueError(
                "broker_name must not be empty"
            )

        self._name = normalized_name

    @property
    def name(self) -> str:
        return self._name

    def execute(
        self,
        request: ExecutionRequest,
    ) -> ExecutionReceipt:
        if not isinstance(
            request,
            ExecutionRequest,
        ):
            raise TypeError(
                "request must be an ExecutionRequest"
            )

        raise RuntimeError(
            f"{self._name} broker integration "
            "is not configured"
        )


class InteractiveBrokersAdapter(
    UnavailableBrokerAdapter
):
    """Placeholder for future IBKR integration."""

    def __init__(self) -> None:
        super().__init__(
            broker_name="INTERACTIVE_BROKERS"
        )


class AlpacaAdapter(UnavailableBrokerAdapter):
    """Placeholder for future Alpaca integration."""

    def __init__(self) -> None:
        super().__init__(
            broker_name="ALPACA"
        )


class TradierAdapter(UnavailableBrokerAdapter):
    """Placeholder for future Tradier integration."""

    def __init__(self) -> None:
        super().__init__(
            broker_name="TRADIER"
        )