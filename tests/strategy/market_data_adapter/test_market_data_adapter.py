from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.market_data import MarketDataType

from app.strategy.market_data_adapter import (
    ConnectionStatus,
    EnterpriseMarketDataAdapter,
    MarketDataConnectionRequest,
    MarketDataConnectionResult,
    ProviderCapability,
    ProviderType,
    SubscriptionAction,
    SubscriptionRequest,
    SubscriptionResult,
)

NOW = datetime(
    2026,
    8,
    6,
    21,
    0,
    tzinfo=timezone.utc,
)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def adapter(
    *,
    current_time: datetime = NOW,
) -> EnterpriseMarketDataAdapter:
    return EnterpriseMarketDataAdapter(
        clock=FixedClock(current_time)
    )


def connection_request(
    *,
    connection_id: str = "connection-001",
    provider_name: str = "Interactive Brokers",
    provider_type: ProviderType = (
        ProviderType.INTERACTIVE_BROKERS
    ),
    requested_at: datetime = NOW,
    requested_by: str = "market-data-service",
) -> MarketDataConnectionRequest:
    return MarketDataConnectionRequest(
        connection_id=connection_id,
        provider_name=provider_name,
        provider_type=provider_type,
        requested_at=requested_at,
        requested_by=requested_by,
        host="127.0.0.1",
        port=7497,
        client_id=10,
        use_paper_environment=True,
        metadata=(
            ("environment", "paper"),
        ),
    )


def connection_result(
    *,
    connection_id: str = "connection-001",
    provider_name: str = "Interactive Brokers",
    provider_type: ProviderType = (
        ProviderType.INTERACTIVE_BROKERS
    ),
    status: ConnectionStatus = (
        ConnectionStatus.CONNECTED
    ),
    connected_at: datetime | None = NOW,
    evaluated_at: datetime = NOW,
    capabilities: tuple[
        ProviderCapability,
        ...,
    ] = (
        ProviderCapability.REAL_TIME_QUOTES,
        ProviderCapability.TRADES,
        ProviderCapability.REAL_TIME_BARS,
        ProviderCapability.SNAPSHOTS,
        ProviderCapability.HEARTBEAT,
    ),
    provider_session_id: str | None = (
        "ibkr-session-001"
    ),
    message: str = "Provider connected.",
) -> MarketDataConnectionResult:
    return MarketDataConnectionResult(
        connection_id=connection_id,
        provider_name=provider_name,
        provider_type=provider_type,
        status=status,
        connected_at=connected_at,
        evaluated_at=evaluated_at,
        capabilities=capabilities,
        provider_session_id=provider_session_id,
        message=message,
    )


def disconnected_result(
    *,
    connection_id: str = "connection-001",
    evaluated_at: datetime = NOW,
) -> MarketDataConnectionResult:
    return MarketDataConnectionResult(
        connection_id=connection_id,
        provider_name="Interactive Brokers",
        provider_type=(
            ProviderType.INTERACTIVE_BROKERS
        ),
        status=ConnectionStatus.DISCONNECTED,
        connected_at=None,
        evaluated_at=evaluated_at,
        capabilities=(),
        provider_session_id=None,
        message="Provider disconnected.",
    )


def failed_result(
    *,
    connection_id: str = "connection-001",
    evaluated_at: datetime = NOW,
) -> MarketDataConnectionResult:
    return MarketDataConnectionResult(
        connection_id=connection_id,
        provider_name="Interactive Brokers",
        provider_type=(
            ProviderType.INTERACTIVE_BROKERS
        ),
        status=ConnectionStatus.FAILED,
        connected_at=None,
        evaluated_at=evaluated_at,
        capabilities=(),
        provider_session_id=None,
        message="Provider connection failed.",
        error="Connection refused.",
    )


def registered_adapter(
) -> EnterpriseMarketDataAdapter:
    value = adapter()
    value.register_connection(
        connection_request()
    )
    return value


def connected_adapter(
) -> EnterpriseMarketDataAdapter:
    value = registered_adapter()
    value.record_connection_result(
        connection_result()
    )
    return value


def test_create_adapter() -> None:
    value = adapter()

    assert value.connection_ids == ()
    assert value.subscription_request_ids == ()
    assert value.connection_report_history == ()


def test_clock_must_be_callable() -> None:
    with pytest.raises(
        TypeError,
        match="clock must be callable",
    ):
        EnterpriseMarketDataAdapter(
            clock=NOW
        )


def test_register_connection() -> None:
    value = adapter()
    request = connection_request()

    result = value.register_connection(
        request
    )

    assert result == request
    assert value.connection_ids == (
        "connection-001",
    )


def test_register_connection_requires_request_model(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a "
            "MarketDataConnectionRequest"
        ),
    ):
        adapter().register_connection(
            object()
        )


def test_duplicate_connection_id_is_rejected() -> None:
    value = registered_adapter()

    with pytest.raises(
        ValueError,
        match=(
            "connection_id is already registered"
        ),
    ):
        value.register_connection(
            connection_request()
        )


def test_register_multiple_connections() -> None:
    value = adapter()

    value.register_connection(
        connection_request()
    )

    value.register_connection(
        connection_request(
            connection_id="connection-002",
            provider_name="Replay Feed",
            provider_type=ProviderType.REPLAY,
        )
    )

    assert value.connection_ids == (
        "connection-001",
        "connection-002",
    )


def test_get_connection_request() -> None:
    value = registered_adapter()

    request = value.get_connection_request(
        "connection-001"
    )

    assert request.connection_id == (
        "connection-001"
    )
    assert request.provider_type is (
        ProviderType.INTERACTIVE_BROKERS
    )


def test_get_connection_request_normalizes_identifier(
) -> None:
    value = registered_adapter()

    request = value.get_connection_request(
        "  connection-001  "
    )

    assert request.connection_id == (
        "connection-001"
    )


def test_get_unknown_connection_request_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data connection request not found"
        ),
    ):
        adapter().get_connection_request(
            "missing"
        )


def test_unregister_connection() -> None:
    value = registered_adapter()

    removed = value.unregister_connection(
        "connection-001"
    )

    assert removed.connection_id == (
        "connection-001"
    )
    assert value.connection_ids == ()


def test_unregister_unknown_connection_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data connection request not found"
        ),
    ):
        adapter().unregister_connection(
            "missing"
        )


@pytest.mark.parametrize(
    "status",
    [
        ConnectionStatus.CONNECTING,
        ConnectionStatus.CONNECTED,
        ConnectionStatus.DEGRADED,
    ],
)
def test_active_connection_cannot_be_unregistered(
    status: ConnectionStatus,
) -> None:
    value = registered_adapter()

    if status is ConnectionStatus.CONNECTING:
        result = MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=status,
            connected_at=None,
            evaluated_at=NOW,
            message="Connection in progress.",
        )
    else:
        result = connection_result(
            status=status,
            message="Connection active.",
        )

    value.record_connection_result(result)

    with pytest.raises(
        RuntimeError,
        match=(
            "active connections cannot be unregistered"
        ),
    ):
        value.unregister_connection(
            "connection-001"
        )


def test_disconnected_connection_can_be_unregistered(
) -> None:
    value = registered_adapter()

    value.record_connection_result(
        disconnected_result()
    )

    removed = value.unregister_connection(
        "connection-001"
    )

    assert removed.connection_id == (
        "connection-001"
    )


def test_failed_connection_can_be_unregistered() -> None:
    value = registered_adapter()

    value.record_connection_result(
        failed_result()
    )

    removed = value.unregister_connection(
        "connection-001"
    )

    assert removed.connection_id == (
        "connection-001"
    )


def test_record_connection_result() -> None:
    value = registered_adapter()
    result = connection_result()

    report = value.record_connection_result(
        result
    )

    assert report.request.connection_id == (
        "connection-001"
    )
    assert report.result == result
    assert report.report_id == (
        "connection-report-000001"
    )
    assert report.reported_at == NOW


def test_record_connection_result_requires_model(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "result must be a "
            "MarketDataConnectionResult"
        ),
    ):
        registered_adapter().record_connection_result(
            object()
        )


def test_record_result_requires_registered_connection(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data connection request not found"
        ),
    ):
        adapter().record_connection_result(
            connection_result()
        )


def test_result_provider_name_must_match_request(
) -> None:
    value = registered_adapter()

    with pytest.raises(
        ValueError,
        match=(
            "result provider_name must match "
            "connection request"
        ),
    ):
        value.record_connection_result(
            connection_result(
                provider_name="Different Provider"
            )
        )


def test_result_provider_type_must_match_request(
) -> None:
    value = registered_adapter()

    with pytest.raises(
        ValueError,
        match=(
            "result provider_type must match "
            "connection request"
        ),
    ):
        value.record_connection_result(
            connection_result(
                provider_type=ProviderType.REPLAY
            )
        )


def test_result_must_not_precede_request() -> None:
    value = registered_adapter()

    with pytest.raises(
        ValueError,
        match=(
            "result evaluated_at must not be earlier "
            "than request requested_at"
        ),
    ):
        value.record_connection_result(
            connection_result(
                connected_at=(
                    NOW - timedelta(seconds=1)
                ),
                evaluated_at=(
                    NOW - timedelta(seconds=1)
                ),
            )
        )

def test_connection_results_must_be_chronological(
) -> None:
    value = adapter()

    value.register_connection(
        connection_request(
            requested_at=(
                NOW - timedelta(seconds=2)
            )
        )
    )

    value.record_connection_result(
        connection_result(
            connected_at=NOW,
            evaluated_at=NOW,
        )
    )

    older = connection_result(
        connected_at=(
            NOW - timedelta(seconds=1)
        ),
        evaluated_at=(
            NOW - timedelta(seconds=1)
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "connection result evaluated_at must not "
            "be earlier than the latest result"
        ),
    ):
        value.record_connection_result(older)
        value = registered_adapter()

    value.record_connection_result(
        connection_result(
            evaluated_at=NOW,
        )
    )

    older = connection_result(
        connected_at=(
            NOW - timedelta(seconds=1)
        ),
        evaluated_at=(
            NOW - timedelta(seconds=1)
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "connection result evaluated_at must not "
            "be earlier than the latest result"
        ),
    ):
        value.record_connection_result(
            older
        )


def test_connection_results_allow_same_timestamp(
) -> None:
    value = registered_adapter()

    first = connection_result(
        status=ConnectionStatus.CONNECTED,
        message="Connected.",
    )
    second = connection_result(
        status=ConnectionStatus.DEGRADED,
        message="Connection degraded.",
    )

    value.record_connection_result(first)
    report = value.record_connection_result(second)

    assert report.result == second
    assert len(
        value.connection_results_for(
            "connection-001"
        )
    ) == 2


def test_get_connection_result() -> None:
    value = connected_adapter()

    result = value.get_connection_result(
        "connection-001"
    )

    assert result.status is (
        ConnectionStatus.CONNECTED
    )


def test_get_result_before_recording_is_rejected(
) -> None:
    value = registered_adapter()

    with pytest.raises(
        KeyError,
        match=(
            "market-data connection has no result"
        ),
    ):
        value.get_connection_result(
            "connection-001"
        )


def test_get_connection_report() -> None:
    value = connected_adapter()

    report = value.get_connection_report(
        "connection-001"
    )

    assert report.result.status is (
        ConnectionStatus.CONNECTED
    )


def test_get_report_before_recording_is_rejected(
) -> None:
    value = registered_adapter()

    with pytest.raises(
        KeyError,
        match=(
            "market-data connection has no report"
        ),
    ):
        value.get_connection_report(
            "connection-001"
        )


def test_connection_result_history() -> None:
    value = registered_adapter()

    first = connection_result(
        status=ConnectionStatus.CONNECTED,
        message="Connected.",
    )
    second = connection_result(
        status=ConnectionStatus.DEGRADED,
        message="Connection degraded.",
    )

    value.record_connection_result(first)
    value.record_connection_result(second)

    assert value.connection_results_for(
        "connection-001"
    ) == (
        first,
        second,
    )


def test_connection_history_before_result_is_empty(
) -> None:
    value = registered_adapter()

    assert value.connection_results_for(
        "connection-001"
    ) == ()


def test_latest_connection_report() -> None:
    value = connected_adapter()

    latest = value.latest_connection_report()

    assert latest.report_id == (
        "connection-report-000001"
    )


def test_latest_report_without_history_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data adapter has no "
            "connection reports"
        ),
    ):
        adapter().latest_connection_report()


def test_connection_report_history_property() -> None:
    value = connected_adapter()

    assert len(
        value.connection_report_history
    ) == 1

    assert (
        value.connection_report_history[0]
        .report_id
        == "connection-report-000001"
    )


def test_connection_report_ids_are_deterministic(
) -> None:
    value = registered_adapter()

    first = value.record_connection_result(
        connection_result(
            status=ConnectionStatus.CONNECTED,
            message="Connected.",
        )
    )

    second = value.record_connection_result(
        connection_result(
            status=ConnectionStatus.DEGRADED,
            message="Connection degraded.",
        )
    )

    assert first.report_id == (
        "connection-report-000001"
    )
    assert second.report_id == (
        "connection-report-000002"
    )


def test_report_ids_continue_across_connections(
) -> None:
    value = adapter()

    value.register_connection(
        connection_request()
    )

    value.register_connection(
        connection_request(
            connection_id="connection-002",
            provider_name="Replay Feed",
            provider_type=ProviderType.REPLAY,
        )
    )

    first = value.record_connection_result(
        connection_result()
    )

    second_result = MarketDataConnectionResult(
        connection_id="connection-002",
        provider_name="Replay Feed",
        provider_type=ProviderType.REPLAY,
        status=ConnectionStatus.CONNECTED,
        connected_at=NOW,
        evaluated_at=NOW,
        capabilities=(
            ProviderCapability.HISTORICAL_BARS,
        ),
        provider_session_id="replay-session-001",
        message="Replay provider connected.",
    )

    second = value.record_connection_result(
        second_result
    )

    assert first.report_id == (
        "connection-report-000001"
    )
    assert second.report_id == (
        "connection-report-000002"
    )


def test_connection_report_contains_provider_metadata(
) -> None:
    value = connected_adapter()

    report = value.get_connection_report(
        "connection-001"
    )

    assert report.metadata == (
        (
            "provider_name",
            "Interactive Brokers",
        ),
        (
            "provider_type",
            "INTERACTIVE_BROKERS",
        ),
    )


def test_is_connected() -> None:
    value = connected_adapter()

    assert value.is_connected(
        "connection-001"
    ) is True


def test_is_connected_returns_false_for_disconnected(
) -> None:
    value = registered_adapter()

    value.record_connection_result(
        disconnected_result()
    )

    assert value.is_connected(
        "connection-001"
    ) is False


def test_capabilities_for_active_connection() -> None:
    value = connected_adapter()

    capabilities = value.capabilities_for(
        "connection-001"
    )

    assert (
        ProviderCapability.REAL_TIME_QUOTES
        in capabilities
    )

    assert (
        ProviderCapability.HEARTBEAT
        in capabilities
    )


def test_capabilities_require_active_connection(
) -> None:
    value = registered_adapter()

    value.record_connection_result(
        disconnected_result()
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "provider connection is not active"
        ),
    ):
        value.capabilities_for(
            "connection-001"
        )


def test_supports_capability() -> None:
    value = connected_adapter()

    assert value.supports(
        "connection-001",
        ProviderCapability.REAL_TIME_QUOTES,
    ) is True

    assert value.supports(
        "connection-001",
        ProviderCapability.MARKET_DEPTH,
    ) is False


def test_supports_requires_capability_enum() -> None:
    value = connected_adapter()

    with pytest.raises(
        TypeError,
        match=(
            "capability must be a "
            "ProviderCapability"
        ),
    ):
        value.supports(
            "connection-001",
            "REAL_TIME_QUOTES",
        )


def test_connection_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="connection_id must not be empty",
    ):
        adapter().get_connection_request(
            "   "
        )


def test_connection_identifier_must_be_string(
) -> None:
    with pytest.raises(
        TypeError,
        match="connection_id must be a string",
    ):
        adapter().get_connection_request(
            123
        )

def subscription_request(
    *,
    request_id: str = "request-001",
    connection_id: str = "connection-001",
    subscription_id: str = "subscription-001",
    action: SubscriptionAction = (
        SubscriptionAction.SUBSCRIBE
    ),
    symbol: str = "NVDA",
    market: str = "NASDAQ",
    data_type: MarketDataType = MarketDataType.QUOTE,
    requested_at: datetime = NOW,
    requested_by: str = "market-data-service",
) -> SubscriptionRequest:
    return SubscriptionRequest(
        request_id=request_id,
        connection_id=connection_id,
        subscription_id=subscription_id,
        action=action,
        symbol=symbol,
        market=market,
        data_type=data_type,
        requested_at=requested_at,
        requested_by=requested_by,
        metadata=(
            ("environment", "paper"),
        ),
    )


def subscription_result(
    *,
    request_id: str = "request-001",
    connection_id: str = "connection-001",
    subscription_id: str = "subscription-001",
    action: SubscriptionAction = (
        SubscriptionAction.SUBSCRIBE
    ),
    symbol: str = "NVDA",
    market: str = "NASDAQ",
    data_type: MarketDataType = MarketDataType.QUOTE,
    successful: bool = True,
    evaluated_at: datetime = NOW,
    provider_subscription_id: str | None = (
        "ibkr-subscription-001"
    ),
    message: str = "Subscription succeeded.",
    error: str | None = None,
) -> SubscriptionResult:
    return SubscriptionResult(
        request_id=request_id,
        connection_id=connection_id,
        subscription_id=subscription_id,
        action=action,
        symbol=symbol,
        market=market,
        data_type=data_type,
        successful=successful,
        evaluated_at=evaluated_at,
        provider_subscription_id=(
            provider_subscription_id
        ),
        message=message,
        error=error,
        metadata=(
            ("environment", "paper"),
        ),
    )


def registered_subscription_adapter(
) -> EnterpriseMarketDataAdapter:
    value = connected_adapter()

    value.register_subscription_request(
        subscription_request()
    )

    return value


def test_register_subscription_request() -> None:
    value = connected_adapter()
    request = subscription_request()

    result = value.register_subscription_request(
        request
    )

    assert result == request
    assert value.subscription_request_ids == (
        "request-001",
    )


def test_register_subscription_request_requires_model(
) -> None:
    with pytest.raises(
        TypeError,
        match="request must be a SubscriptionRequest",
    ):
        connected_adapter().register_subscription_request(
            object()
        )


def test_subscription_request_requires_active_connection(
) -> None:
    value = registered_adapter()

    value.record_connection_result(
        disconnected_result()
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "provider connection must be active"
        ),
    ):
        value.register_subscription_request(
            subscription_request()
        )


def test_subscription_request_requires_connection_result(
) -> None:
    value = registered_adapter()

    with pytest.raises(
        KeyError,
        match=(
            "market-data connection has no result"
        ),
    ):
        value.register_subscription_request(
            subscription_request()
        )


def test_subscription_request_requires_registered_connection(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data connection request not found"
        ),
    ):
        adapter().register_subscription_request(
            subscription_request()
        )


def test_duplicate_subscription_request_id_is_rejected(
) -> None:
    value = registered_subscription_adapter()

    with pytest.raises(
        ValueError,
        match="request_id is already registered",
    ):
        value.register_subscription_request(
            subscription_request()
        )


def test_duplicate_subscription_id_is_rejected() -> None:
    value = registered_subscription_adapter()

    with pytest.raises(
        ValueError,
        match=(
            "subscription_id is already registered"
        ),
    ):
        value.register_subscription_request(
            subscription_request(
                request_id="request-002",
            )
        )


def test_register_multiple_subscription_requests(
) -> None:
    value = connected_adapter()

    value.register_subscription_request(
        subscription_request()
    )

    value.register_subscription_request(
        subscription_request(
            request_id="request-002",
            subscription_id="subscription-002",
            symbol="AAPL",
            data_type=MarketDataType.TRADE,
        )
    )

    assert value.subscription_request_ids == (
        "request-001",
        "request-002",
    )


def test_get_subscription_request() -> None:
    value = registered_subscription_adapter()

    request = value.get_subscription_request(
        "request-001"
    )

    assert request.subscription_id == (
        "subscription-001"
    )


def test_get_subscription_request_normalizes_identifier(
) -> None:
    value = registered_subscription_adapter()

    request = value.get_subscription_request(
        "  request-001  "
    )

    assert request.request_id == "request-001"


def test_get_unknown_subscription_request_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match="subscription request not found",
    ):
        connected_adapter().get_subscription_request(
            "missing"
        )


def test_request_for_subscription() -> None:
    value = registered_subscription_adapter()

    request = value.request_for_subscription(
        "subscription-001"
    )

    assert request.request_id == "request-001"


def test_request_for_subscription_normalizes_identifier(
) -> None:
    value = registered_subscription_adapter()

    request = value.request_for_subscription(
        "  subscription-001  "
    )

    assert request.subscription_id == (
        "subscription-001"
    )


def test_unknown_subscription_id_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match=(
            "subscription request not found for "
            "subscription_id"
        ),
    ):
        connected_adapter().request_for_subscription(
            "missing"
        )


def test_record_subscription_result() -> None:
    value = registered_subscription_adapter()
    result = subscription_result()

    recorded = value.record_subscription_result(
        result
    )

    assert recorded == result
    assert value.get_subscription_result(
        "request-001"
    ) == result


def test_record_subscription_result_requires_model(
) -> None:
    with pytest.raises(
        TypeError,
        match="result must be a SubscriptionResult",
    ):
        registered_subscription_adapter(
        ).record_subscription_result(
            object()
        )


def test_subscription_result_requires_registered_request(
) -> None:
    value = connected_adapter()

    with pytest.raises(
        KeyError,
        match="subscription request not found",
    ):
        value.record_subscription_result(
            subscription_result()
        )


def test_subscription_result_connection_id_must_match(
) -> None:
    value = registered_subscription_adapter()

    with pytest.raises(
        ValueError,
        match=(
            "result connection_id must match request"
        ),
    ):
        value.record_subscription_result(
            subscription_result(
                connection_id="different-connection"
            )
        )


def test_subscription_result_subscription_id_must_match(
) -> None:
    value = registered_subscription_adapter()

    with pytest.raises(
        ValueError,
        match=(
            "result subscription_id must match request"
        ),
    ):
        value.record_subscription_result(
            subscription_result(
                subscription_id=(
                    "different-subscription"
                )
            )
        )


def test_subscription_result_action_must_match() -> None:
    value = registered_subscription_adapter()

    result = SubscriptionResult(
        request_id="request-001",
        connection_id="connection-001",
        subscription_id="subscription-001",
        action=SubscriptionAction.RESUME,
        symbol="NVDA",
        market="NASDAQ",
        data_type=MarketDataType.QUOTE,
        successful=True,
        evaluated_at=NOW,
        provider_subscription_id=(
            "ibkr-subscription-001"
        ),
        message="Subscription resumed.",
    )

    with pytest.raises(
        ValueError,
        match="result action must match request",
    ):
        value.record_subscription_result(result)


def test_subscription_result_symbol_must_match() -> None:
    value = registered_subscription_adapter()

    with pytest.raises(
        ValueError,
        match="result symbol must match request",
    ):
        value.record_subscription_result(
            subscription_result(symbol="AAPL")
        )


def test_subscription_result_market_must_match() -> None:
    value = registered_subscription_adapter()

    with pytest.raises(
        ValueError,
        match="result market must match request",
    ):
        value.record_subscription_result(
            subscription_result(market="NYSE")
        )


def test_subscription_result_data_type_must_match(
) -> None:
    value = registered_subscription_adapter()

    with pytest.raises(
        ValueError,
        match=(
            "result data_type must match request"
        ),
    ):
        value.record_subscription_result(
            subscription_result(
                data_type=MarketDataType.TRADE
            )
        )


def test_subscription_result_must_not_precede_request(
) -> None:
    value = connected_adapter()

    value.register_subscription_request(
        subscription_request(
            requested_at=NOW,
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "result evaluated_at must not be earlier "
            "than request requested_at"
        ),
    ):
        value.record_subscription_result(
            subscription_result(
                evaluated_at=(
                    NOW - timedelta(seconds=1)
                )
            )
        )


def test_subscription_results_must_be_chronological(
) -> None:
    value = connected_adapter()

    value.register_subscription_request(
        subscription_request(
            requested_at=(
                NOW - timedelta(seconds=2)
            )
        )
    )

    value.record_subscription_result(
        subscription_result(
            evaluated_at=NOW,
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "subscription result evaluated_at must "
            "not be earlier than the latest result"
        ),
    ):
        value.record_subscription_result(
            subscription_result(
                evaluated_at=(
                    NOW - timedelta(seconds=1)
                )
            )
        )


def test_subscription_results_allow_same_timestamp(
) -> None:
    value = registered_subscription_adapter()

    first = subscription_result(
        successful=True,
        evaluated_at=NOW,
    )

    second = subscription_result(
        successful=False,
        evaluated_at=NOW,
        provider_subscription_id=None,
        message="Subscription later failed.",
        error="Provider rejected renewal.",
    )

    value.record_subscription_result(first)
    value.record_subscription_result(second)

    assert value.get_subscription_result(
        "request-001"
    ) == second

    assert len(
        value.subscription_results_for(
            "request-001"
        )
    ) == 2


def test_get_subscription_result_before_recording(
) -> None:
    value = registered_subscription_adapter()

    with pytest.raises(
        KeyError,
        match=(
            "subscription request has no result"
        ),
    ):
        value.get_subscription_result(
            "request-001"
        )


def test_subscription_result_history() -> None:
    value = registered_subscription_adapter()

    first = subscription_result(
        successful=True,
    )

    second = subscription_result(
        successful=False,
        provider_subscription_id=None,
        message="Subscription failed later.",
        error="Provider disconnected.",
    )

    value.record_subscription_result(first)
    value.record_subscription_result(second)

    assert value.subscription_results_for(
        "request-001"
    ) == (
        first,
        second,
    )


def test_subscription_result_history_before_recording(
) -> None:
    value = registered_subscription_adapter()

    assert value.subscription_results_for(
        "request-001"
    ) == ()


def test_subscription_request_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="request_id must not be empty",
    ):
        connected_adapter().get_subscription_request(
            "   "
        )


def test_subscription_request_identifier_must_be_string(
) -> None:
    with pytest.raises(
        TypeError,
        match="request_id must be a string",
    ):
        connected_adapter().get_subscription_request(
            123
        )


def test_subscription_identifier_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="subscription_id must not be empty",
    ):
        connected_adapter().request_for_subscription(
            "   "
        )


def test_disconnect_connected_provider() -> None:
    value = connected_adapter()

    report = value.disconnect(
        "connection-001"
    )

    assert report.result.status is (
        ConnectionStatus.DISCONNECTED
    )
    assert report.result.is_connected is False
    assert report.result.connected_at is None
    assert report.result.capabilities == ()
    assert report.result.provider_session_id is None
    assert report.report_id == (
        "connection-report-000002"
    )


def test_disconnect_message_is_normalized() -> None:
    value = connected_adapter()

    report = value.disconnect(
        "connection-001",
        message="  Provider manually disconnected.  ",
    )

    assert report.result.message == (
        "Provider manually disconnected."
    )


def test_disconnect_is_idempotent() -> None:
    value = connected_adapter()

    first = value.disconnect(
        "connection-001"
    )
    second = value.disconnect(
        "connection-001"
    )

    assert first == second
    assert len(
        value.connection_report_history
    ) == 2

    assert len(
        value.connection_results_for(
            "connection-001"
        )
    ) == 2


def test_failed_connection_cannot_be_disconnected(
) -> None:
    value = registered_adapter()

    value.record_connection_result(
        failed_result()
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "failed connections cannot be "
            "disconnected"
        ),
    ):
        value.disconnect(
            "connection-001"
        )


def test_disconnect_requires_connection_result() -> None:
    value = registered_adapter()

    with pytest.raises(
        KeyError,
        match=(
            "market-data connection has no result"
        ),
    ):
        value.disconnect(
            "connection-001"
        )


def test_disconnect_unknown_connection_is_rejected(
) -> None:
    with pytest.raises(
        KeyError,
        match=(
            "market-data connection request not found"
        ),
    ):
        adapter().disconnect(
            "missing"
        )


def test_disconnect_time_must_follow_latest_result(
) -> None:
    value = adapter(
        current_time=NOW
    )

    value.register_connection(
        connection_request(
            requested_at=NOW,
        )
    )

    value.record_connection_result(
        connection_result(
            connected_at=NOW,
            evaluated_at=(
                NOW + timedelta(seconds=1)
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "disconnect time must not be earlier "
            "than the latest connection result"
        ),
    ):
        value.disconnect(
            "connection-001"
        )


def test_disconnect_report_becomes_latest() -> None:
    value = connected_adapter()

    expected = value.disconnect(
        "connection-001"
    )

    assert value.latest_connection_report() == expected
    assert value.get_connection_report(
        "connection-001"
    ) == expected


def test_disconnect_clears_active_capabilities() -> None:
    value = connected_adapter()

    value.disconnect(
        "connection-001"
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "provider connection is not active"
        ),
    ):
        value.capabilities_for(
            "connection-001"
        )


def test_disconnected_provider_rejects_new_subscription(
) -> None:
    value = connected_adapter()

    value.disconnect(
        "connection-001"
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "provider connection must be active"
        ),
    ):
        value.register_subscription_request(
            subscription_request()
        )


def test_degraded_connection_accepts_subscription(
) -> None:
    value = registered_adapter()

    value.record_connection_result(
        connection_result(
            status=ConnectionStatus.DEGRADED,
            message="Provider is degraded.",
        )
    )

    request = value.register_subscription_request(
        subscription_request()
    )

    assert request.request_id == "request-001"


def test_clock_must_return_datetime() -> None:
    value = EnterpriseMarketDataAdapter(
        clock=lambda: "now"
    )

    value.register_connection(
        connection_request()
    )

    value.record_connection_result(
        connection_result()
    )

    with pytest.raises(
        TypeError,
        match="clock must return a datetime",
    ):
        value.disconnect(
            "connection-001"
        )


def test_clock_must_return_timezone_aware_datetime(
) -> None:
    value = EnterpriseMarketDataAdapter(
        clock=lambda: datetime(
            2026,
            8,
            6,
            21,
            0,
        )
    )

    value.register_connection(
        connection_request()
    )

    value.record_connection_result(
        connection_result()
    )

    with pytest.raises(
        ValueError,
        match=(
            "clock must return a "
            "timezone-aware datetime"
        ),
    ):
        value.disconnect(
            "connection-001"
        )


def test_full_connection_and_subscription_history(
) -> None:
    value = connected_adapter()

    request = value.register_subscription_request(
        subscription_request()
    )

    result = value.record_subscription_result(
        subscription_result()
    )

    disconnect_report = value.disconnect(
        "connection-001"
    )

    assert request.request_id == "request-001"
    assert result.successful is True
    assert disconnect_report.result.status is (
        ConnectionStatus.DISCONNECTED
    )

    assert len(
        value.connection_results_for(
            "connection-001"
        )
    ) == 2

    assert len(
        value.connection_report_history
    ) == 2

    assert value.subscription_results_for(
        "request-001"
    ) == (result,)