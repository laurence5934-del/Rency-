from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .adapter_models import (
    ConnectionStatus,
    MarketDataConnectionReport,
    MarketDataConnectionRequest,
    MarketDataConnectionResult,
    ProviderCapability,
    SubscriptionAction,
    SubscriptionRequest,
    SubscriptionResult,
)


Clock = Callable[[], datetime]


class EnterpriseMarketDataAdapter:
    """
    Coordinates provider connections and subscription operations.

    The adapter owns connection state, provider capabilities,
    subscription routing, immutable histories, and audit reports.
    Provider-specific networking remains outside this core engine.
    """

    def __init__(
        self,
        *,
        clock: Clock | None = None,
    ) -> None:
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")

        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._connection_requests: dict[
            str,
            MarketDataConnectionRequest,
        ] = {}

        self._connection_results: dict[
            str,
            MarketDataConnectionResult,
        ] = {}

        self._connection_result_history: dict[
            str,
            list[MarketDataConnectionResult],
        ] = {}

        self._connection_reports: dict[
            str,
            MarketDataConnectionReport,
        ] = {}

        self._connection_report_history: list[
            MarketDataConnectionReport
        ] = []

        self._subscription_requests: dict[
            str,
            SubscriptionRequest,
        ] = {}

        self._subscription_request_by_subscription: dict[
            str,
            str,
        ] = {}

        self._subscription_results: dict[
            str,
            SubscriptionResult,
        ] = {}

        self._subscription_result_history: dict[
            str,
            list[SubscriptionResult],
        ] = {}

        self._next_connection_report_number = 1

    @property
    def connection_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._connection_requests)
        )

    @property
    def subscription_request_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._subscription_requests)
        )

    @property
    def connection_report_history(
        self,
    ) -> tuple[MarketDataConnectionReport, ...]:
        return tuple(
            self._connection_report_history
        )

    def register_connection(
        self,
        request: MarketDataConnectionRequest,
    ) -> MarketDataConnectionRequest:
        if not isinstance(
            request,
            MarketDataConnectionRequest,
        ):
            raise TypeError(
                "request must be a "
                "MarketDataConnectionRequest"
            )

        if (
            request.connection_id
            in self._connection_requests
        ):
            raise ValueError(
                "connection_id is already registered"
            )

        self._connection_requests[
            request.connection_id
        ] = request

        return request

    def unregister_connection(
        self,
        connection_id: str,
    ) -> MarketDataConnectionRequest:
        request = self.get_connection_request(
            connection_id
        )

        result = self._connection_results.get(
            request.connection_id
        )

        if (
            result is not None
            and result.status
            in {
                ConnectionStatus.CONNECTING,
                ConnectionStatus.CONNECTED,
                ConnectionStatus.DEGRADED,
            }
        ):
            raise RuntimeError(
                "active connections cannot be unregistered"
            )

        self._connection_requests.pop(
            request.connection_id
        )

        self._connection_results.pop(
            request.connection_id,
            None,
        )

        self._connection_reports.pop(
            request.connection_id,
            None,
        )

        return request

    def get_connection_request(
        self,
        connection_id: str,
    ) -> MarketDataConnectionRequest:
        normalized_connection_id = (
            self._normalize_identifier(
                connection_id,
                "connection_id",
            )
        )

        try:
            return self._connection_requests[
                normalized_connection_id
            ]
        except KeyError as exc:
            raise KeyError(
                "market-data connection request "
                "not found: "
                f"{normalized_connection_id}"
            ) from exc

    def record_connection_result(
        self,
        result: MarketDataConnectionResult,
    ) -> MarketDataConnectionReport:
        if not isinstance(
            result,
            MarketDataConnectionResult,
        ):
            raise TypeError(
                "result must be a "
                "MarketDataConnectionResult"
            )

        request = self.get_connection_request(
            result.connection_id
        )

        if (
            result.provider_name
            != request.provider_name
        ):
            raise ValueError(
                "result provider_name must match "
                "connection request"
            )

        if (
            result.provider_type
            is not request.provider_type
        ):
            raise ValueError(
                "result provider_type must match "
                "connection request"
            )

        if result.evaluated_at < request.requested_at:
            raise ValueError(
                "result evaluated_at must not be earlier "
                "than request requested_at"
            )

        current = self._connection_results.get(
            result.connection_id
        )

        if (
            current is not None
            and result.evaluated_at
            < current.evaluated_at
        ):
            raise ValueError(
                "connection result evaluated_at must not "
                "be earlier than the latest result"
            )

        self._connection_results[
            result.connection_id
        ] = result

        self._connection_result_history.setdefault(
            result.connection_id,
            [],
        ).append(result)

        report = MarketDataConnectionReport(
            report_id=(
                self._next_connection_report_id()
            ),
            request=request,
            result=result,
            reported_at=result.evaluated_at,
            message=(
                "Market-data connection result recorded."
            ),
            metadata=(
                (
                    "provider_name",
                    request.provider_name,
                ),
                (
                    "provider_type",
                    request.provider_type.value,
                ),
            ),
        )

        self._connection_reports[
            result.connection_id
        ] = report

        self._connection_report_history.append(
            report
        )

        return report

    def get_connection_result(
        self,
        connection_id: str,
    ) -> MarketDataConnectionResult:
        request = self.get_connection_request(
            connection_id
        )

        try:
            return self._connection_results[
                request.connection_id
            ]
        except KeyError as exc:
            raise KeyError(
                "market-data connection has no result: "
                f"{request.connection_id}"
            ) from exc

    def get_connection_report(
        self,
        connection_id: str,
    ) -> MarketDataConnectionReport:
        request = self.get_connection_request(
            connection_id
        )

        try:
            return self._connection_reports[
                request.connection_id
            ]
        except KeyError as exc:
            raise KeyError(
                "market-data connection has no report: "
                f"{request.connection_id}"
            ) from exc

    def connection_results_for(
        self,
        connection_id: str,
    ) -> tuple[MarketDataConnectionResult, ...]:
        request = self.get_connection_request(
            connection_id
        )

        return tuple(
            self._connection_result_history.get(
                request.connection_id,
                (),
            )
        )

    def latest_connection_report(
        self,
    ) -> MarketDataConnectionReport:
        if not self._connection_report_history:
            raise KeyError(
                "market-data adapter has no "
                "connection reports"
            )

        return self._connection_report_history[-1]

    def is_connected(
        self,
        connection_id: str,
    ) -> bool:
        return self.get_connection_result(
            connection_id
        ).is_connected

    def capabilities_for(
        self,
        connection_id: str,
    ) -> tuple[ProviderCapability, ...]:
        result = self.get_connection_result(
            connection_id
        )

        if not result.is_connected:
            raise RuntimeError(
                "provider connection is not active"
            )

        return result.capabilities

    def supports(
        self,
        connection_id: str,
        capability: ProviderCapability,
    ) -> bool:
        if not isinstance(
            capability,
            ProviderCapability,
        ):
            raise TypeError(
                "capability must be a "
                "ProviderCapability"
            )

        return capability in self.capabilities_for(
            connection_id
        )

    def register_subscription_request(
        self,
        request: SubscriptionRequest,
    ) -> SubscriptionRequest:
        if not isinstance(
            request,
            SubscriptionRequest,
        ):
            raise TypeError(
                "request must be a SubscriptionRequest"
            )

        if (
            request.request_id
            in self._subscription_requests
        ):
            raise ValueError(
                "request_id is already registered"
            )

        self._require_active_connection(
            request.connection_id
        )

        existing_request_id = (
            self._subscription_request_by_subscription.get(
                request.subscription_id
            )
        )

        if existing_request_id is not None:
            existing = self._subscription_requests[
                existing_request_id
            ]

            if existing.request_id != request.request_id:
                raise ValueError(
                    "subscription_id is already registered"
                )

        self._subscription_requests[
            request.request_id
        ] = request

        self._subscription_request_by_subscription[
            request.subscription_id
        ] = request.request_id

        return request

    def get_subscription_request(
        self,
        request_id: str,
    ) -> SubscriptionRequest:
        normalized_request_id = (
            self._normalize_identifier(
                request_id,
                "request_id",
            )
        )

        try:
            return self._subscription_requests[
                normalized_request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "subscription request not found: "
                f"{normalized_request_id}"
            ) from exc

    def request_for_subscription(
        self,
        subscription_id: str,
    ) -> SubscriptionRequest:
        normalized_subscription_id = (
            self._normalize_identifier(
                subscription_id,
                "subscription_id",
            )
        )

        try:
            request_id = (
                self._subscription_request_by_subscription[
                    normalized_subscription_id
                ]
            )
        except KeyError as exc:
            raise KeyError(
                "subscription request not found for "
                f"subscription_id: "
                f"{normalized_subscription_id}"
            ) from exc

        return self._subscription_requests[
            request_id
        ]

    def record_subscription_result(
        self,
        result: SubscriptionResult,
    ) -> SubscriptionResult:
        if not isinstance(
            result,
            SubscriptionResult,
        ):
            raise TypeError(
                "result must be a SubscriptionResult"
            )

        request = self.get_subscription_request(
            result.request_id
        )

        self._validate_subscription_result(
            request=request,
            result=result,
        )

        current = self._subscription_results.get(
            result.request_id
        )

        if (
            current is not None
            and result.evaluated_at
            < current.evaluated_at
        ):
            raise ValueError(
                "subscription result evaluated_at must "
                "not be earlier than the latest result"
            )

        self._subscription_results[
            result.request_id
        ] = result

        self._subscription_result_history.setdefault(
            result.request_id,
            [],
        ).append(result)

        return result

    def get_subscription_result(
        self,
        request_id: str,
    ) -> SubscriptionResult:
        request = self.get_subscription_request(
            request_id
        )

        try:
            return self._subscription_results[
                request.request_id
            ]
        except KeyError as exc:
            raise KeyError(
                "subscription request has no result: "
                f"{request.request_id}"
            ) from exc

    def subscription_results_for(
        self,
        request_id: str,
    ) -> tuple[SubscriptionResult, ...]:
        request = self.get_subscription_request(
            request_id
        )

        return tuple(
            self._subscription_result_history.get(
                request.request_id,
                (),
            )
        )

    def disconnect(
        self,
        connection_id: str,
        *,
        message: str = "Provider disconnected.",
    ) -> MarketDataConnectionReport:
        request = self.get_connection_request(
            connection_id
        )

        current = self.get_connection_result(
            request.connection_id
        )

        if current.status is ConnectionStatus.DISCONNECTED:
            return self.get_connection_report(
                request.connection_id
            )

        if current.status is ConnectionStatus.FAILED:
            raise RuntimeError(
                "failed connections cannot be "
                "disconnected"
            )

        now = self._current_time()

        if now < current.evaluated_at:
            raise ValueError(
                "disconnect time must not be earlier "
                "than the latest connection result"
            )

        result = MarketDataConnectionResult(
            connection_id=request.connection_id,
            provider_name=request.provider_name,
            provider_type=request.provider_type,
            status=ConnectionStatus.DISCONNECTED,
            connected_at=None,
            evaluated_at=now,
            capabilities=(),
            provider_session_id=None,
            message=message,
        )

        return self.record_connection_result(result)

    def _require_active_connection(
        self,
        connection_id: str,
    ) -> MarketDataConnectionResult:
        result = self.get_connection_result(
            connection_id
        )

        if not result.is_connected:
            raise RuntimeError(
                "provider connection must be active"
            )

        return result

    @staticmethod
    def _validate_subscription_result(
        *,
        request: SubscriptionRequest,
        result: SubscriptionResult,
    ) -> None:
        if result.connection_id != request.connection_id:
            raise ValueError(
                "result connection_id must match request"
            )

        if (
            result.subscription_id
            != request.subscription_id
        ):
            raise ValueError(
                "result subscription_id must match request"
            )

        if result.action is not request.action:
            raise ValueError(
                "result action must match request"
            )

        if result.symbol != request.symbol:
            raise ValueError(
                "result symbol must match request"
            )

        if result.market != request.market:
            raise ValueError(
                "result market must match request"
            )

        if result.data_type is not request.data_type:
            raise ValueError(
                "result data_type must match request"
            )

        if result.evaluated_at < request.requested_at:
            raise ValueError(
                "result evaluated_at must not be earlier "
                "than request requested_at"
            )

    def _next_connection_report_id(self) -> str:
        value = (
            "connection-report-"
            f"{self._next_connection_report_number:06d}"
        )

        self._next_connection_report_number += 1
        return value

    def _current_time(self) -> datetime:
        value = self._clock()

        if not isinstance(value, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                "clock must return a "
                "timezone-aware datetime"
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