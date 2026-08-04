from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from app.strategy.order_manager import (
    OrderRequest,
    OrderSide,
    OrderType,
)

from .broker_models import (
    BrokerAccount,
    BrokerCapability,
    BrokerConnectionState,
    BrokerDecision,
    BrokerEnvironment,
    BrokerHealthReport,
    BrokerOrderRequest,
    BrokerOrderResponse,
    BrokerOrderStatus,
    BrokerStatus,
)


Clock = Callable[[], datetime]
BrokerSubmitter = Callable[
    [BrokerOrderRequest],
    BrokerOrderResponse,
]


class EnterpriseBrokerGateway:
    """
    Controlled boundary between the enterprise OMS and broker adapters.

    Phase 2A responsibilities:
    - broker account registration
    - adapter registration
    - account and connection validation
    - capability validation
    - OMS-to-broker order translation
    - live-environment authorization
    - idempotent submission
    - response validation and history
    - health reporting
    """

    def __init__(
        self,
        *,
        clock: Clock | None = None,
    ) -> None:
        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._accounts: dict[
            str,
            BrokerAccount,
        ] = {}

        self._submitters: dict[
            str,
            BrokerSubmitter,
        ] = {}

        self._gateway_orders: dict[
            str,
            BrokerOrderRequest,
        ] = {}

        self._gateway_order_by_order_id: dict[
            str,
            str,
        ] = {}

        self._gateway_order_by_client_id: dict[
            str,
            str,
        ] = {}

        self._responses: dict[
            str,
            BrokerOrderResponse,
        ] = {}

        self._response_history: list[
            BrokerOrderResponse
        ] = []

        self._health_history: list[
            BrokerHealthReport
        ] = []

        self._live_authorized_accounts: set[str] = set()

        self._next_gateway_order_number = 1
        self._next_response_number = 1
        self._next_health_number = 1

    @property
    def account_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._accounts)
        )

    @property
    def gateway_order_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._gateway_orders)
        )

    @property
    def response_history(
        self,
    ) -> tuple[BrokerOrderResponse, ...]:
        return tuple(self._response_history)

    @property
    def health_history(
        self,
    ) -> tuple[BrokerHealthReport, ...]:
        return tuple(self._health_history)

    def register_broker(
        self,
        *,
        account: BrokerAccount,
        submitter: BrokerSubmitter,
    ) -> BrokerAccount:
        if not isinstance(account, BrokerAccount):
            raise TypeError(
                "account must be a BrokerAccount"
            )

        if not callable(submitter):
            raise TypeError(
                "submitter must be callable"
            )

        if account.account_id in self._accounts:
            raise ValueError(
                "account_id is already registered"
            )

        normalized_broker_name = (
            self._normalize_identifier(
                account.broker_name,
                "broker_name",
            )
        )

        if normalized_broker_name in self._submitters:
            raise ValueError(
                "broker_name is already registered"
            )

        self._accounts[
            account.account_id
        ] = account

        self._submitters[
            normalized_broker_name
        ] = submitter

        return account

    def unregister_broker(
        self,
        account_id: str,
    ) -> BrokerAccount:
        account = self.get_account(account_id)

        self._accounts.pop(
            account.account_id
        )

        self._submitters.pop(
            account.broker_name,
            None,
        )

        self._live_authorized_accounts.discard(
            account.account_id
        )

        return account

    def update_account(
        self,
        account: BrokerAccount,
    ) -> BrokerAccount:
        if not isinstance(account, BrokerAccount):
            raise TypeError(
                "account must be a BrokerAccount"
            )

        existing = self.get_account(
            account.account_id
        )

        if account.broker_name != existing.broker_name:
            raise ValueError(
                "broker_name must not change"
            )

        if account.environment is not existing.environment:
            raise ValueError(
                "broker environment must not change"
            )

        if account.updated_at < existing.updated_at:
            raise ValueError(
                "account update must not be older "
                "than the current snapshot"
            )

        self._accounts[
            account.account_id
        ] = account

        return account

    def get_account(
        self,
        account_id: str,
    ) -> BrokerAccount:
        normalized_account_id = (
            self._normalize_identifier(
                account_id,
                "account_id",
            )
        )

        try:
            return self._accounts[
                normalized_account_id
            ]
        except KeyError as exc:
            raise KeyError(
                "broker account not found: "
                f"{normalized_account_id}"
            ) from exc

    def authorize_live_trading(
        self,
        account_id: str,
        *,
        confirmation: str,
    ) -> BrokerAccount:
        account = self.get_account(account_id)

        if (
            account.environment
            is not BrokerEnvironment.LIVE
        ):
            raise ValueError(
                "only live accounts require "
                "live-trading authorization"
            )

        normalized_confirmation = (
            self._normalize_identifier(
                confirmation,
                "confirmation",
            ).upper()
        )

        if normalized_confirmation != (
            "AUTHORIZE LIVE TRADING"
        ):
            raise ValueError(
                "invalid live-trading confirmation"
            )

        if (
            BrokerCapability.LIVE_TRADING
            not in account.capabilities
        ):
            raise ValueError(
                "account does not advertise "
                "LIVE_TRADING capability"
            )

        self._live_authorized_accounts.add(
            account.account_id
        )

        return account

    def revoke_live_trading(
        self,
        account_id: str,
    ) -> BrokerAccount:
        account = self.get_account(account_id)

        self._live_authorized_accounts.discard(
            account.account_id
        )

        return account

    def is_live_authorized(
        self,
        account_id: str,
    ) -> bool:
        account = self.get_account(account_id)

        return (
            account.account_id
            in self._live_authorized_accounts
        )

    def translate_order(
        self,
        request: OrderRequest,
        *,
        account_id: str,
        allow_extended_hours: bool = False,
    ) -> BrokerOrderRequest:
        if not isinstance(request, OrderRequest):
            raise TypeError(
                "request must be an OrderRequest"
            )

        if not isinstance(
            allow_extended_hours,
            bool,
        ):
            raise TypeError(
                "allow_extended_hours must be a bool"
            )

        account = self.get_account(
            account_id
        )

        self._validate_account_for_submission(
            account
        )

        self._validate_order_capabilities(
            account=account,
            request=request,
            allow_extended_hours=(
                allow_extended_hours
            ),
        )

        existing_gateway_order_id = (
            self._gateway_order_by_order_id.get(
                request.order_id
            )
        )

        if existing_gateway_order_id is not None:
            existing = self._gateway_orders[
                existing_gateway_order_id
            ]

            if (
                existing.client_order_id
                != request.client_order_id
            ):
                raise ValueError(
                    "order_id is already associated "
                    "with another client_order_id"
                )

            return existing

        existing_client_gateway_id = (
            self._gateway_order_by_client_id.get(
                request.client_order_id
            )
        )

        if existing_client_gateway_id is not None:
            existing = self._gateway_orders[
                existing_client_gateway_id
            ]

            if existing.order_id != request.order_id:
                raise ValueError(
                    "client_order_id is already associated "
                    "with another order_id"
                )

            return existing

        gateway_request = BrokerOrderRequest(
            gateway_order_id=(
                self._next_gateway_order_id()
            ),
            order_id=request.order_id,
            client_order_id=(
                request.client_order_id
            ),
            broker_name=account.broker_name,
            account_id=account.account_id,
            environment=account.environment,
            symbol=request.symbol,
            asset_class=request.asset_class,
            side=request.side,
            order_type=request.order_type,
            time_in_force=request.time_in_force,
            quantity=request.quantity,
            submitted_at=self._current_time(),
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            allow_extended_hours=(
                allow_extended_hours
            ),
            metadata=(
                (
                    "portfolio_id",
                    request.portfolio_id,
                ),
            )
            + (
                (
                    (
                        "strategy_id",
                        request.strategy_id,
                    ),
                )
                if request.strategy_id is not None
                else ()
            ),
        )

        self._gateway_orders[
            gateway_request.gateway_order_id
        ] = gateway_request

        self._gateway_order_by_order_id[
            request.order_id
        ] = gateway_request.gateway_order_id

        self._gateway_order_by_client_id[
            request.client_order_id
        ] = gateway_request.gateway_order_id

        return gateway_request

    def submit_order(
        self,
        request: OrderRequest,
        *,
        account_id: str,
        allow_extended_hours: bool = False,
    ) -> BrokerOrderResponse:
        gateway_request = self.translate_order(
            request,
            account_id=account_id,
            allow_extended_hours=(
                allow_extended_hours
            ),
        )

        existing_response = self._responses.get(
            gateway_request.gateway_order_id
        )

        if existing_response is not None:
            return existing_response

        account = self.get_account(
            gateway_request.account_id
        )

        self._validate_account_for_submission(
            account
        )

        try:
            submitter = self._submitters[
                account.broker_name
            ]
        except KeyError as exc:
            raise RuntimeError(
                "broker submitter is not registered"
            ) from exc

        raw_response = submitter(
            gateway_request
        )

        if not isinstance(
            raw_response,
            BrokerOrderResponse,
        ):
            raise TypeError(
                "submitter must return a "
                "BrokerOrderResponse"
            )

        response = self._normalize_response(
            request=gateway_request,
            response=raw_response,
        )

        self._responses[
            gateway_request.gateway_order_id
        ] = response

        self._response_history.append(
            response
        )

        return response

    def record_response(
        self,
        response: BrokerOrderResponse,
    ) -> BrokerOrderResponse:
        if not isinstance(
            response,
            BrokerOrderResponse,
        ):
            raise TypeError(
                "response must be a "
                "BrokerOrderResponse"
            )

        gateway_request = self.get_gateway_order(
            response.gateway_order_id
        )

        normalized_response = (
            self._normalize_response(
                request=gateway_request,
                response=response,
            )
        )

        current = self._responses.get(
            gateway_request.gateway_order_id
        )

        if (
            current is not None
            and current.is_terminal
        ):
            raise RuntimeError(
                "terminal broker responses "
                "cannot be replaced"
            )

        self._responses[
            gateway_request.gateway_order_id
        ] = normalized_response

        self._response_history.append(
            normalized_response
        )

        return normalized_response

    def get_gateway_order(
        self,
        gateway_order_id: str,
    ) -> BrokerOrderRequest:
        normalized_gateway_order_id = (
            self._normalize_identifier(
                gateway_order_id,
                "gateway_order_id",
            )
        )

        try:
            return self._gateway_orders[
                normalized_gateway_order_id
            ]
        except KeyError as exc:
            raise KeyError(
                "gateway order not found: "
                f"{normalized_gateway_order_id}"
            ) from exc

    def gateway_order_for_order(
        self,
        order_id: str,
    ) -> BrokerOrderRequest:
        normalized_order_id = (
            self._normalize_identifier(
                order_id,
                "order_id",
            )
        )

        try:
            gateway_order_id = (
                self._gateway_order_by_order_id[
                    normalized_order_id
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "gateway order not found for order: "
                f"{normalized_order_id}"
            ) from exc

        return self._gateway_orders[
            gateway_order_id
        ]

    def get_response(
        self,
        gateway_order_id: str,
    ) -> BrokerOrderResponse:
        gateway_request = self.get_gateway_order(
            gateway_order_id
        )

        try:
            return self._responses[
                gateway_request.gateway_order_id
            ]
        except KeyError as exc:
            raise KeyError(
                "gateway order has no broker response: "
                f"{gateway_request.gateway_order_id}"
            ) from exc

    def responses_for_order(
        self,
        order_id: str,
    ) -> tuple[BrokerOrderResponse, ...]:
        gateway_request = (
            self.gateway_order_for_order(
                order_id
            )
        )

        return tuple(
            response
            for response in self._response_history
            if (
                response.gateway_order_id
                == gateway_request.gateway_order_id
            )
        )

    def check_health(
        self,
        account_id: str,
        *,
        latency_ms: int = 0,
        message: str | None = None,
    ) -> BrokerHealthReport:
        account = self.get_account(account_id)

        if not isinstance(latency_ms, int):
            raise TypeError(
                "latency_ms must be an integer"
            )

        if latency_ms < 0:
            raise ValueError(
                "latency_ms must not be negative"
            )

        connected = (
            account.connection_state
            is BrokerConnectionState.CONNECTED
        )

        account_accessible = connected

        capability_available = (
            BrokerCapability.PAPER_TRADING
            in account.capabilities
            if account.environment
            is BrokerEnvironment.PAPER
            else (
                BrokerCapability.LIVE_TRADING
                in account.capabilities
                and account.account_id
                in self._live_authorized_accounts
            )
        )

        order_submission_available = (
            connected
            and account_accessible
            and capability_available
            and account.broker_name
            in self._submitters
        )

        if order_submission_available:
            status = BrokerStatus.COMPLETED
            decision = BrokerDecision.APPROVE
            default_message = (
                "Broker gateway is healthy and "
                "order submission is available."
            )
            error = None
            warnings: tuple[str, ...] = ()
        elif (
            account.connection_state
            is BrokerConnectionState.DEGRADED
        ):
            status = BrokerStatus.PENDING
            decision = BrokerDecision.HOLD
            default_message = (
                "Broker connection is degraded."
            )
            error = None
            warnings = (
                "Order submission is unavailable.",
            )
        elif (
            account.connection_state
            is BrokerConnectionState.FAILED
        ):
            status = BrokerStatus.FAILED
            decision = BrokerDecision.REJECT
            default_message = (
                "Broker connection has failed."
            )
            error = (
                "Broker connection is in FAILED state."
            )
            warnings = ()
        else:
            status = BrokerStatus.REJECTED
            decision = BrokerDecision.REJECT
            default_message = (
                "Broker gateway is not available "
                "for order submission."
            )
            error = None
            warnings = (
                "Verify connectivity, capabilities, "
                "and authorization.",
            )

        normalized_message = (
            default_message
            if message is None
            else self._normalize_identifier(
                message,
                "message",
            )
        )

        report = BrokerHealthReport(
            health_id=self._next_health_id(),
            broker_name=account.broker_name,
            environment=account.environment,
            connection_state=(
                account.connection_state
            ),
            status=status,
            decision=decision,
            checked_at=self._current_time(),
            latency_ms=latency_ms,
            account_accessible=(
                account_accessible
            ),
            order_submission_available=(
                order_submission_available
            ),
            message=normalized_message,
            warnings=warnings,
            error=error,
        )

        self._health_history.append(report)

        return report

    def health_reports_for_broker(
        self,
        broker_name: str,
    ) -> tuple[BrokerHealthReport, ...]:
        normalized_broker_name = (
            self._normalize_identifier(
                broker_name,
                "broker_name",
            )
        )

        return tuple(
            report
            for report in self._health_history
            if (
                report.broker_name
                == normalized_broker_name
            )
        )

    def _validate_account_for_submission(
        self,
        account: BrokerAccount,
    ) -> None:
        if (
            account.connection_state
            is not BrokerConnectionState.CONNECTED
        ):
            raise RuntimeError(
                "broker account must be connected"
            )

        if (
            account.broker_name
            not in self._submitters
        ):
            raise RuntimeError(
                "broker submitter is not registered"
            )

        if (
            account.environment
            is BrokerEnvironment.PAPER
        ):
            if (
                BrokerCapability.PAPER_TRADING
                not in account.capabilities
            ):
                raise RuntimeError(
                    "paper account lacks "
                    "PAPER_TRADING capability"
                )
        else:
            if (
                BrokerCapability.LIVE_TRADING
                not in account.capabilities
            ):
                raise RuntimeError(
                    "live account lacks "
                    "LIVE_TRADING capability"
                )

            if (
                account.account_id
                not in self._live_authorized_accounts
            ):
                raise PermissionError(
                    "live trading is not explicitly authorized"
                )

    def _validate_order_capabilities(
        self,
        *,
        account: BrokerAccount,
        request: OrderRequest,
        allow_extended_hours: bool,
    ) -> None:
        required_capability = {
            OrderType.MARKET: (
                BrokerCapability.MARKET_ORDERS
            ),
            OrderType.LIMIT: (
                BrokerCapability.LIMIT_ORDERS
            ),
            OrderType.STOP: (
                BrokerCapability.STOP_ORDERS
            ),
            OrderType.STOP_LIMIT: (
                BrokerCapability.STOP_LIMIT_ORDERS
            ),
        }[request.order_type]

        if (
            required_capability
            not in account.capabilities
        ):
            raise ValueError(
                "broker account does not support "
                f"{request.order_type.value} orders"
            )

        if (
            request.side
            is OrderSide.SELL_SHORT
            and BrokerCapability.SHORT_SELLING
            not in account.capabilities
        ):
            raise ValueError(
                "broker account does not support "
                "short selling"
            )

        if (
            allow_extended_hours
            and BrokerCapability.EXTENDED_HOURS
            not in account.capabilities
        ):
            raise ValueError(
                "broker account does not support "
                "extended-hours trading"
            )

    def _normalize_response(
        self,
        *,
        request: BrokerOrderRequest,
        response: BrokerOrderResponse,
    ) -> BrokerOrderResponse:
        if (
            response.gateway_order_id
            != request.gateway_order_id
        ):
            raise ValueError(
                "response gateway_order_id must "
                "match broker request"
            )

        if response.order_id != request.order_id:
            raise ValueError(
                "response order_id must match "
                "broker request"
            )

        if response.received_at < request.submitted_at:
            raise ValueError(
                "response received_at must not be earlier "
                "than request submitted_at"
            )

        return response

    def _next_gateway_order_id(self) -> str:
        value = (
            f"gateway-order-"
            f"{self._next_gateway_order_number:06d}"
        )
        self._next_gateway_order_number += 1
        return value

    def next_response_id(self) -> str:
        value = (
            f"response-"
            f"{self._next_response_number:06d}"
        )
        self._next_response_number += 1
        return value

    def _next_health_id(self) -> str:
        value = (
            f"health-"
            f"{self._next_health_number:06d}"
        )
        self._next_health_number += 1
        return value

    def _current_time(self) -> datetime:
        value = self._clock()

        if not isinstance(value, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware datetime"
            )

        return value

    @staticmethod
    def _normalize_identifier(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized