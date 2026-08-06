from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.strategy.market_data import MarketDataType

from app.strategy.market_data_adapter import (
    ConnectionStatus,
    MarketDataConnectionReport,
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
    20,
    0,
    tzinfo=timezone.utc,
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
    host: str | None = "127.0.0.1",
    port: int | None = 7497,
    client_id: int | None = 10,
    use_paper_environment: bool = True,
) -> MarketDataConnectionRequest:
    return MarketDataConnectionRequest(
        connection_id=connection_id,
        provider_name=provider_name,
        provider_type=provider_type,
        requested_at=requested_at,
        requested_by=requested_by,
        host=host,
        port=port,
        client_id=client_id,
        use_paper_environment=use_paper_environment,
        metadata=(
            ("source", "market-data-service"),
        ),
    )


def connected_result(
    *,
    connection_id: str = "connection-001",
    provider_name: str = "Interactive Brokers",
    provider_type: ProviderType = (
        ProviderType.INTERACTIVE_BROKERS
    ),
    status: ConnectionStatus = ConnectionStatus.CONNECTED,
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
    provider_session_id: str | None = "ibkr-session-001",
    message: str = "Provider connection established.",
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
        metadata=(
            ("environment", "paper"),
        ),
    )


def failed_result(
    *,
    connection_id: str = "connection-001",
    provider_name: str = "Interactive Brokers",
    provider_type: ProviderType = (
        ProviderType.INTERACTIVE_BROKERS
    ),
    evaluated_at: datetime = NOW,
    error: str = "Provider connection failed.",
) -> MarketDataConnectionResult:
    return MarketDataConnectionResult(
        connection_id=connection_id,
        provider_name=provider_name,
        provider_type=provider_type,
        status=ConnectionStatus.FAILED,
        connected_at=None,
        evaluated_at=evaluated_at,
        provider_session_id=None,
        message="Connection attempt failed.",
        error=error,
    )


def test_market_data_connection_request() -> None:
    value = connection_request()

    assert value.connection_id == "connection-001"
    assert value.provider_name == "Interactive Brokers"
    assert value.provider_type is (
        ProviderType.INTERACTIVE_BROKERS
    )
    assert value.requested_at == NOW
    assert value.requested_by == "market-data-service"
    assert value.host == "127.0.0.1"
    assert value.port == 7497
    assert value.client_id == 10
    assert value.use_paper_environment is True
    assert value.metadata == (
        ("source", "market-data-service"),
    )


def test_connection_request_allows_optional_network_fields(
) -> None:
    value = connection_request(
        host=None,
        port=None,
        client_id=None,
    )

    assert value.host is None
    assert value.port is None
    assert value.client_id is None


def test_connection_request_text_is_normalized() -> None:
    value = MarketDataConnectionRequest(
        connection_id="  connection-001  ",
        provider_name="  Interactive Brokers  ",
        provider_type=ProviderType.INTERACTIVE_BROKERS,
        requested_at=NOW,
        requested_by="  market-data-service  ",
        host="  127.0.0.1  ",
        port=7497,
        client_id=10,
        metadata=[
            ("  source  ", "  market-data-service  "),
        ],
    )

    assert value.connection_id == "connection-001"
    assert value.provider_name == "Interactive Brokers"
    assert value.requested_by == "market-data-service"
    assert value.host == "127.0.0.1"
    assert value.metadata == (
        ("source", "market-data-service"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "connection_id",
        "provider_name",
        "requested_by",
    ],
)
def test_connection_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "connection_id": "connection-001",
        "provider_name": "Interactive Brokers",
        "provider_type": ProviderType.INTERACTIVE_BROKERS,
        "requested_at": NOW,
        "requested_by": "market-data-service",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        MarketDataConnectionRequest(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "connection_id",
        "provider_name",
        "requested_by",
    ],
)
def test_connection_request_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "connection_id": "connection-001",
        "provider_name": "Interactive Brokers",
        "provider_type": ProviderType.INTERACTIVE_BROKERS,
        "requested_at": NOW,
        "requested_by": "market-data-service",
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        MarketDataConnectionRequest(**arguments)


def test_connection_request_requires_provider_type() -> None:
    with pytest.raises(
        TypeError,
        match="provider_type must be a ProviderType",
    ):
        connection_request(
            provider_type="INTERACTIVE_BROKERS"
        )


def test_connection_request_timestamp_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="requested_at must be a datetime",
    ):
        MarketDataConnectionRequest(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            requested_at="2026-08-06",
            requested_by="market-data-service",
        )


def test_connection_request_timestamp_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="requested_at must be timezone-aware",
    ):
        connection_request(
            requested_at=datetime(
                2026,
                8,
                6,
                20,
                0,
            )
        )


def test_connection_request_paper_flag_requires_bool(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "use_paper_environment must be a bool"
        ),
    ):
        connection_request(
            use_paper_environment="yes"
        )


@pytest.mark.parametrize(
    "port",
    [
        0,
        -1,
        65536,
    ],
)
def test_connection_request_port_must_be_valid(
    port: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="port must be between 1 and 65535",
    ):
        connection_request(port=port)


def test_connection_request_port_requires_integer() -> None:
    with pytest.raises(
        TypeError,
        match="port must be an integer or None",
    ):
        connection_request(port="7497")


def test_connection_request_client_id_must_not_be_negative(
) -> None:
    with pytest.raises(
        ValueError,
        match="client_id must not be negative",
    ):
        connection_request(client_id=-1)


def test_connection_request_client_id_requires_integer(
) -> None:
    with pytest.raises(
        TypeError,
        match="client_id must be an integer or None",
    ):
        connection_request(client_id="10")


def test_connection_request_host_must_not_be_empty(
) -> None:
    with pytest.raises(
        ValueError,
        match="host must not be empty",
    ):
        connection_request(host="   ")


def test_connection_request_metadata_is_normalized() -> None:
    value = MarketDataConnectionRequest(
        connection_id="connection-001",
        provider_name="Interactive Brokers",
        provider_type=ProviderType.INTERACTIVE_BROKERS,
        requested_at=NOW,
        requested_by="market-data-service",
        metadata=[
            ("  environment  ", "  paper  "),
            ("  region  ", "  us  "),
        ],
    )

    assert value.metadata == (
        ("environment", "paper"),
        ("region", "us"),
    )


def test_connection_request_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        MarketDataConnectionRequest(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            requested_at=NOW,
            requested_by="market-data-service",
            metadata=(
                ("source", "adapter"),
                ("source", "duplicate"),
            ),
        )


def test_connection_request_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        MarketDataConnectionRequest(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            requested_at=NOW,
            requested_by="market-data-service",
            metadata=(
                ("source",),
            ),
        )


def test_connected_connection_result() -> None:
    value = connected_result()

    assert value.connection_id == "connection-001"
    assert value.provider_name == "Interactive Brokers"
    assert value.status is ConnectionStatus.CONNECTED
    assert value.connected_at == NOW
    assert value.evaluated_at == NOW
    assert value.provider_session_id == (
        "ibkr-session-001"
    )
    assert value.is_connected is True
    assert value.error is None


def test_degraded_connection_result_is_connected() -> None:
    value = connected_result(
        status=ConnectionStatus.DEGRADED,
        message="Provider connection is degraded.",
    )

    assert value.status is ConnectionStatus.DEGRADED
    assert value.is_connected is True


def test_failed_connection_result() -> None:
    value = failed_result()

    assert value.status is ConnectionStatus.FAILED
    assert value.is_connected is False
    assert value.connected_at is None
    assert value.provider_session_id is None
    assert value.error == "Provider connection failed."


def test_disconnected_connection_result() -> None:
    value = MarketDataConnectionResult(
        connection_id="connection-001",
        provider_name="Interactive Brokers",
        provider_type=ProviderType.INTERACTIVE_BROKERS,
        status=ConnectionStatus.DISCONNECTED,
        connected_at=None,
        evaluated_at=NOW,
        message="Provider is disconnected.",
    )

    assert value.is_connected is False


def test_connecting_connection_result() -> None:
    value = MarketDataConnectionResult(
        connection_id="connection-001",
        provider_name="Interactive Brokers",
        provider_type=ProviderType.INTERACTIVE_BROKERS,
        status=ConnectionStatus.CONNECTING,
        connected_at=None,
        evaluated_at=NOW,
        message="Provider connection is in progress.",
    )

    assert value.is_connected is False


def test_connection_result_text_is_normalized() -> None:
    value = MarketDataConnectionResult(
        connection_id="  connection-001  ",
        provider_name="  Interactive Brokers  ",
        provider_type=ProviderType.INTERACTIVE_BROKERS,
        status=ConnectionStatus.CONNECTED,
        connected_at=NOW,
        evaluated_at=NOW,
        provider_session_id="  ibkr-session-001  ",
        message="  Provider connected.  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.connection_id == "connection-001"
    assert value.provider_name == "Interactive Brokers"
    assert value.provider_session_id == (
        "ibkr-session-001"
    )
    assert value.message == "Provider connected."
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "connection_id",
        "provider_name",
        "message",
    ],
)
def test_connection_result_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "connection_id": "connection-001",
        "provider_name": "Interactive Brokers",
        "provider_type": ProviderType.INTERACTIVE_BROKERS,
        "status": ConnectionStatus.CONNECTED,
        "connected_at": NOW,
        "evaluated_at": NOW,
        "provider_session_id": "ibkr-session-001",
        "message": "Provider connected.",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        MarketDataConnectionResult(**arguments)


def test_connection_result_requires_provider_type() -> None:
    with pytest.raises(
        TypeError,
        match="provider_type must be a ProviderType",
    ):
        connected_result(
            provider_type="INTERACTIVE_BROKERS"
        )


def test_connection_result_requires_status_enum() -> None:
    with pytest.raises(
        TypeError,
        match="status must be a ConnectionStatus",
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status="CONNECTED",
            connected_at=NOW,
            evaluated_at=NOW,
            provider_session_id="ibkr-session-001",
        )


def test_connection_result_evaluated_at_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="evaluated_at must be a datetime",
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=ConnectionStatus.DISCONNECTED,
            connected_at=None,
            evaluated_at="2026-08-06",
        )


def test_connection_result_evaluated_at_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="evaluated_at must be timezone-aware",
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=ConnectionStatus.DISCONNECTED,
            connected_at=None,
            evaluated_at=datetime(
                2026,
                8,
                6,
                20,
                0,
            ),
        )


def test_connection_result_connected_at_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="connected_at must be timezone-aware",
    ):
        connected_result(
            connected_at=datetime(
                2026,
                8,
                6,
                20,
                0,
            )
        )


def test_connected_at_must_not_follow_evaluation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "connected_at must not be later "
            "than evaluated_at"
        ),
    ):
        connected_result(
            connected_at=(
                NOW + timedelta(seconds=1)
            ),
            evaluated_at=NOW,
        )


@pytest.mark.parametrize(
    "status",
    [
        ConnectionStatus.CONNECTED,
        ConnectionStatus.DEGRADED,
    ],
)
def test_connected_status_requires_connected_at(
    status: ConnectionStatus,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "connected and degraded results "
            "require connected_at"
        ),
    ):
        connected_result(
            status=status,
            connected_at=None,
        )


@pytest.mark.parametrize(
    "status",
    [
        ConnectionStatus.CONNECTED,
        ConnectionStatus.DEGRADED,
    ],
)
def test_connected_status_requires_session_id(
    status: ConnectionStatus,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "connected and degraded results "
            "require provider_session_id"
        ),
    ):
        connected_result(
            status=status,
            provider_session_id=None,
        )


def test_connected_result_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "connected and degraded results "
            "must not include an error"
        ),
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=ConnectionStatus.CONNECTED,
            connected_at=NOW,
            evaluated_at=NOW,
            provider_session_id="ibkr-session-001",
            error="Unexpected error.",
        )


def test_failed_result_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed connection results require an error"
        ),
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=ConnectionStatus.FAILED,
            connected_at=None,
            evaluated_at=NOW,
        )


def test_failed_result_rejects_connected_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "failed connection results must not "
            "include connected_at"
        ),
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=ConnectionStatus.FAILED,
            connected_at=NOW,
            evaluated_at=NOW,
            error="Provider connection failed.",
        )


@pytest.mark.parametrize(
    "status",
    [
        ConnectionStatus.DISCONNECTED,
        ConnectionStatus.CONNECTING,
    ],
)
def test_inactive_status_rejects_connected_at(
    status: ConnectionStatus,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "disconnected and connecting results "
            "must not include connected_at"
        ),
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=status,
            connected_at=NOW,
            evaluated_at=NOW,
        )


@pytest.mark.parametrize(
    "status",
    [
        ConnectionStatus.DISCONNECTED,
        ConnectionStatus.CONNECTING,
    ],
)
def test_inactive_status_rejects_session_id(
    status: ConnectionStatus,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "disconnected and connecting results "
            "must not include provider_session_id"
        ),
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=status,
            connected_at=None,
            evaluated_at=NOW,
            provider_session_id="ibkr-session-001",
        )


def test_only_failed_result_may_include_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "only failed connection results "
            "may include an error"
        ),
    ):
        MarketDataConnectionResult(
            connection_id="connection-001",
            provider_name="Interactive Brokers",
            provider_type=(
                ProviderType.INTERACTIVE_BROKERS
            ),
            status=ConnectionStatus.DISCONNECTED,
            connected_at=None,
            evaluated_at=NOW,
            error="Unexpected error.",
        )


def test_connection_capabilities_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="capabilities must be unique",
    ):
        connected_result(
            capabilities=(
                ProviderCapability.REAL_TIME_QUOTES,
                ProviderCapability.REAL_TIME_QUOTES,
            )
        )


def test_connection_capabilities_require_enum_values(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "every capability must be a "
            "ProviderCapability"
        ),
    ):
        connected_result(
            capabilities=(
                ProviderCapability.REAL_TIME_QUOTES,
                "TRADES",
            )
        )


def test_connection_result_supports_capability() -> None:
    value = connected_result()

    assert value.supports(
        ProviderCapability.REAL_TIME_QUOTES
    ) is True

    assert value.supports(
        ProviderCapability.MARKET_DEPTH
    ) is False


def test_supports_requires_capability_enum() -> None:
    value = connected_result()

    with pytest.raises(
        TypeError,
        match=(
            "capability must be a "
            "ProviderCapability"
        ),
    ):
        value.supports("REAL_TIME_QUOTES")


@pytest.mark.parametrize(
    "model",
    [
        connection_request(),
        connected_result(),
        failed_result(),
    ],
)
def test_connection_models_are_immutable(
    model: object,
) -> None:
    with pytest.raises(FrozenInstanceError):
        model.connection_id = "changed"

def connection_report(
    *,
    report_id: str = "connection-report-001",
    request: MarketDataConnectionRequest | None = None,
    result: MarketDataConnectionResult | None = None,
    reported_at: datetime = NOW,
    message: str = "Connection workflow completed.",
) -> MarketDataConnectionReport:
    return MarketDataConnectionReport(
        report_id=report_id,
        request=request or connection_request(),
        result=result or connected_result(),
        reported_at=reported_at,
        message=message,
        metadata=(
            ("source", "market-data-adapter"),
        ),
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
            ("source", "market-data-service"),
        ),
    )


def successful_subscription_result(
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
    evaluated_at: datetime = NOW,
    provider_subscription_id: str | None = (
        "ibkr-subscription-001"
    ),
    message: str = "Subscription request succeeded.",
) -> SubscriptionResult:
    return SubscriptionResult(
        request_id=request_id,
        connection_id=connection_id,
        subscription_id=subscription_id,
        action=action,
        symbol=symbol,
        market=market,
        data_type=data_type,
        successful=True,
        evaluated_at=evaluated_at,
        provider_subscription_id=(
            provider_subscription_id
        ),
        message=message,
        metadata=(
            ("environment", "paper"),
        ),
    )


def unsuccessful_subscription_result(
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
    evaluated_at: datetime = NOW,
    error: str = "Provider rejected subscription.",
) -> SubscriptionResult:
    return SubscriptionResult(
        request_id=request_id,
        connection_id=connection_id,
        subscription_id=subscription_id,
        action=action,
        symbol=symbol,
        market=market,
        data_type=data_type,
        successful=False,
        evaluated_at=evaluated_at,
        message="Subscription request failed.",
        error=error,
    )


def test_market_data_connection_report() -> None:
    value = connection_report()

    assert value.report_id == "connection-report-001"
    assert value.request.connection_id == "connection-001"
    assert value.result.connection_id == "connection-001"
    assert value.reported_at == NOW
    assert value.message == "Connection workflow completed."
    assert value.metadata == (
        ("source", "market-data-adapter"),
    )


def test_connection_report_text_is_normalized() -> None:
    value = MarketDataConnectionReport(
        report_id="  connection-report-001  ",
        request=connection_request(),
        result=connected_result(),
        reported_at=NOW,
        message="  Connection completed.  ",
        metadata=[
            ("  source  ", "  adapter  "),
        ],
    )

    assert value.report_id == "connection-report-001"
    assert value.message == "Connection completed."
    assert value.metadata == (
        ("source", "adapter"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_connection_report_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "connection-report-001",
        "request": connection_request(),
        "result": connected_result(),
        "reported_at": NOW,
        "message": "Connection completed.",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        MarketDataConnectionReport(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "report_id",
        "message",
    ],
)
def test_connection_report_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "report_id": "connection-report-001",
        "request": connection_request(),
        "result": connected_result(),
        "reported_at": NOW,
        "message": "Connection completed.",
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        MarketDataConnectionReport(**arguments)


def test_connection_report_requires_request_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a "
            "MarketDataConnectionRequest"
        ),
    ):
        MarketDataConnectionReport(
            report_id="connection-report-001",
            request=object(),
            result=connected_result(),
            reported_at=NOW,
            message="Connection completed.",
        )


def test_connection_report_requires_result_model() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "result must be a "
            "MarketDataConnectionResult"
        ),
    ):
        MarketDataConnectionReport(
            report_id="connection-report-001",
            request=connection_request(),
            result=object(),
            reported_at=NOW,
            message="Connection completed.",
        )


def test_connection_reported_at_requires_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="reported_at must be a datetime",
    ):
        MarketDataConnectionReport(
            report_id="connection-report-001",
            request=connection_request(),
            result=connected_result(),
            reported_at="2026-08-06",
            message="Connection completed.",
        )


def test_connection_reported_at_must_be_timezone_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="reported_at must be timezone-aware",
    ):
        MarketDataConnectionReport(
            report_id="connection-report-001",
            request=connection_request(),
            result=connected_result(),
            reported_at=datetime(
                2026,
                8,
                6,
                20,
                0,
            ),
            message="Connection completed.",
        )


def test_connection_report_connection_ids_must_match(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "request and result connection_id "
            "values must match"
        ),
    ):
        connection_report(
            result=connected_result(
                connection_id="different-connection"
            )
        )


def test_connection_report_provider_names_must_match(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "request and result provider_name "
            "values must match"
        ),
    ):
        connection_report(
            result=connected_result(
                provider_name="Different Provider"
            )
        )


def test_connection_report_provider_types_must_match(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "request and result provider_type "
            "values must match"
        ),
    ):
        connection_report(
            result=connected_result(
                provider_type=ProviderType.REPLAY
            )
        )


def test_connection_result_must_not_precede_request(
) -> None:
    request = connection_request(
        requested_at=NOW
    )

    result = connected_result(
        connected_at=NOW - timedelta(seconds=1),
        evaluated_at=NOW - timedelta(seconds=1),
    )

    with pytest.raises(
        ValueError,
        match=(
            "result evaluated_at must not be earlier "
            "than request requested_at"
        ),
    ):
        connection_report(
            request=request,
            result=result,
            reported_at=NOW,
        )


def test_connection_reported_at_must_follow_result(
) -> None:
    result = connected_result(
        connected_at=NOW,
        evaluated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "reported_at must not be earlier "
            "than result evaluated_at"
        ),
    ):
        connection_report(
            result=result,
            reported_at=NOW - timedelta(seconds=1),
        )


def test_connection_report_metadata_keys_must_be_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        MarketDataConnectionReport(
            report_id="connection-report-001",
            request=connection_request(),
            result=connected_result(),
            reported_at=NOW,
            message="Connection completed.",
            metadata=(
                ("source", "adapter"),
                ("source", "duplicate"),
            ),
        )


def test_connection_report_metadata_items_must_be_pairs(
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "each metadata item must be "
            "a two-item tuple"
        ),
    ):
        MarketDataConnectionReport(
            report_id="connection-report-001",
            request=connection_request(),
            result=connected_result(),
            reported_at=NOW,
            message="Connection completed.",
            metadata=(
                ("source",),
            ),
        )


def test_subscription_request() -> None:
    value = subscription_request()

    assert value.request_id == "request-001"
    assert value.connection_id == "connection-001"
    assert value.subscription_id == "subscription-001"
    assert value.action is SubscriptionAction.SUBSCRIBE
    assert value.symbol == "NVDA"
    assert value.market == "NASDAQ"
    assert value.data_type is MarketDataType.QUOTE
    assert value.requested_at == NOW
    assert value.requested_by == "market-data-service"
    assert value.metadata == (
        ("source", "market-data-service"),
    )


def test_subscription_request_text_is_normalized() -> None:
    value = SubscriptionRequest(
        request_id="  request-001  ",
        connection_id="  connection-001  ",
        subscription_id="  subscription-001  ",
        action=SubscriptionAction.SUBSCRIBE,
        symbol="  nvda  ",
        market="  nasdaq  ",
        data_type=MarketDataType.QUOTE,
        requested_at=NOW,
        requested_by="  market-data-service  ",
        metadata=[
            ("  source  ", "  adapter  "),
        ],
    )

    assert value.request_id == "request-001"
    assert value.connection_id == "connection-001"
    assert value.subscription_id == "subscription-001"
    assert value.symbol == "NVDA"
    assert value.market == "NASDAQ"
    assert value.requested_by == "market-data-service"
    assert value.metadata == (
        ("source", "adapter"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "connection_id",
        "subscription_id",
        "symbol",
        "market",
        "requested_by",
    ],
)
def test_subscription_request_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "connection_id": "connection-001",
        "subscription_id": "subscription-001",
        "action": SubscriptionAction.SUBSCRIBE,
        "symbol": "NVDA",
        "market": "NASDAQ",
        "data_type": MarketDataType.QUOTE,
        "requested_at": NOW,
        "requested_by": "market-data-service",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        SubscriptionRequest(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "connection_id",
        "subscription_id",
        "symbol",
        "market",
        "requested_by",
    ],
)
def test_subscription_request_required_text_must_be_string(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "connection_id": "connection-001",
        "subscription_id": "subscription-001",
        "action": SubscriptionAction.SUBSCRIBE,
        "symbol": "NVDA",
        "market": "NASDAQ",
        "data_type": MarketDataType.QUOTE,
        "requested_at": NOW,
        "requested_by": "market-data-service",
    }
    arguments[field_name] = 123

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        SubscriptionRequest(**arguments)


def test_subscription_request_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be a SubscriptionAction",
    ):
        subscription_request(
            action="SUBSCRIBE"
        )


def test_subscription_request_requires_data_type() -> None:
    with pytest.raises(
        TypeError,
        match="data_type must be a MarketDataType",
    ):
        subscription_request(
            data_type="QUOTE"
        )


def test_subscription_request_timestamp_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="requested_at must be a datetime",
    ):
        SubscriptionRequest(
            request_id="request-001",
            connection_id="connection-001",
            subscription_id="subscription-001",
            action=SubscriptionAction.SUBSCRIBE,
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            requested_at="2026-08-06",
            requested_by="market-data-service",
        )


def test_subscription_request_timestamp_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="requested_at must be timezone-aware",
    ):
        subscription_request(
            requested_at=datetime(
                2026,
                8,
                6,
                20,
                0,
            )
        )


def test_subscription_request_metadata_keys_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        SubscriptionRequest(
            request_id="request-001",
            connection_id="connection-001",
            subscription_id="subscription-001",
            action=SubscriptionAction.SUBSCRIBE,
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            requested_at=NOW,
            requested_by="market-data-service",
            metadata=(
                ("source", "adapter"),
                ("source", "duplicate"),
            ),
        )


@pytest.mark.parametrize(
    "action",
    [
        SubscriptionAction.SUBSCRIBE,
        SubscriptionAction.UNSUBSCRIBE,
        SubscriptionAction.PAUSE,
        SubscriptionAction.RESUME,
    ],
)
def test_subscription_request_supports_all_actions(
    action: SubscriptionAction,
) -> None:
    value = subscription_request(action=action)

    assert value.action is action


def test_successful_subscription_result() -> None:
    value = successful_subscription_result()

    assert value.request_id == "request-001"
    assert value.connection_id == "connection-001"
    assert value.subscription_id == "subscription-001"
    assert value.action is SubscriptionAction.SUBSCRIBE
    assert value.symbol == "NVDA"
    assert value.market == "NASDAQ"
    assert value.data_type is MarketDataType.QUOTE
    assert value.successful is True
    assert value.provider_subscription_id == (
        "ibkr-subscription-001"
    )
    assert value.error is None


def test_unsuccessful_subscription_result() -> None:
    value = unsuccessful_subscription_result()

    assert value.successful is False
    assert value.provider_subscription_id is None
    assert value.error == (
        "Provider rejected subscription."
    )


def test_subscription_result_text_is_normalized() -> None:
    value = SubscriptionResult(
        request_id="  request-001  ",
        connection_id="  connection-001  ",
        subscription_id="  subscription-001  ",
        action=SubscriptionAction.SUBSCRIBE,
        symbol="  nvda  ",
        market="  nasdaq  ",
        data_type=MarketDataType.QUOTE,
        successful=True,
        evaluated_at=NOW,
        provider_subscription_id=(
            "  ibkr-subscription-001  "
        ),
        message="  Subscription succeeded.  ",
        metadata=[
            ("  environment  ", "  paper  "),
        ],
    )

    assert value.request_id == "request-001"
    assert value.connection_id == "connection-001"
    assert value.subscription_id == "subscription-001"
    assert value.symbol == "NVDA"
    assert value.market == "NASDAQ"
    assert value.provider_subscription_id == (
        "ibkr-subscription-001"
    )
    assert value.message == "Subscription succeeded."
    assert value.metadata == (
        ("environment", "paper"),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "request_id",
        "connection_id",
        "subscription_id",
        "symbol",
        "market",
        "message",
    ],
)
def test_subscription_result_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "request_id": "request-001",
        "connection_id": "connection-001",
        "subscription_id": "subscription-001",
        "action": SubscriptionAction.SUBSCRIBE,
        "symbol": "NVDA",
        "market": "NASDAQ",
        "data_type": MarketDataType.QUOTE,
        "successful": True,
        "evaluated_at": NOW,
        "provider_subscription_id": (
            "ibkr-subscription-001"
        ),
        "message": "Subscription succeeded.",
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        SubscriptionResult(**arguments)


def test_subscription_result_requires_action_enum() -> None:
    with pytest.raises(
        TypeError,
        match="action must be a SubscriptionAction",
    ):
        successful_subscription_result(
            action="SUBSCRIBE"
        )


def test_subscription_result_requires_data_type() -> None:
    with pytest.raises(
        TypeError,
        match="data_type must be a MarketDataType",
    ):
        successful_subscription_result(
            data_type="QUOTE"
        )


def test_subscription_result_successful_must_be_bool(
) -> None:
    with pytest.raises(
        TypeError,
        match="successful must be a bool",
    ):
        SubscriptionResult(
            request_id="request-001",
            connection_id="connection-001",
            subscription_id="subscription-001",
            action=SubscriptionAction.SUBSCRIBE,
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            successful="yes",
            evaluated_at=NOW,
            provider_subscription_id=(
                "ibkr-subscription-001"
            ),
        )


def test_subscription_result_timestamp_requires_datetime(
) -> None:
    with pytest.raises(
        TypeError,
        match="evaluated_at must be a datetime",
    ):
        SubscriptionResult(
            request_id="request-001",
            connection_id="connection-001",
            subscription_id="subscription-001",
            action=SubscriptionAction.SUBSCRIBE,
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            successful=True,
            evaluated_at="2026-08-06",
            provider_subscription_id=(
                "ibkr-subscription-001"
            ),
        )


def test_subscription_result_timestamp_must_be_aware(
) -> None:
    with pytest.raises(
        ValueError,
        match="evaluated_at must be timezone-aware",
    ):
        successful_subscription_result(
            evaluated_at=datetime(
                2026,
                8,
                6,
                20,
                0,
            )
        )


def test_successful_subscription_rejects_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "successful subscription results "
            "must not include an error"
        ),
    ):
        SubscriptionResult(
            request_id="request-001",
            connection_id="connection-001",
            subscription_id="subscription-001",
            action=SubscriptionAction.SUBSCRIBE,
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            successful=True,
            evaluated_at=NOW,
            provider_subscription_id=(
                "ibkr-subscription-001"
            ),
            error="Unexpected error.",
        )


@pytest.mark.parametrize(
    "action",
    [
        SubscriptionAction.SUBSCRIBE,
        SubscriptionAction.RESUME,
    ],
)
def test_successful_subscribe_requires_provider_id(
    action: SubscriptionAction,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "successful subscribe and resume "
            "results require provider_subscription_id"
        ),
    ):
        successful_subscription_result(
            action=action,
            provider_subscription_id=None,
        )


@pytest.mark.parametrize(
    "action",
    [
        SubscriptionAction.UNSUBSCRIBE,
        SubscriptionAction.PAUSE,
    ],
)
def test_successful_inactive_action_allows_no_provider_id(
    action: SubscriptionAction,
) -> None:
    value = successful_subscription_result(
        action=action,
        provider_subscription_id=None,
    )

    assert value.successful is True
    assert value.provider_subscription_id is None


def test_unsuccessful_subscription_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unsuccessful subscription results "
            "require an error"
        ),
    ):
        SubscriptionResult(
            request_id="request-001",
            connection_id="connection-001",
            subscription_id="subscription-001",
            action=SubscriptionAction.SUBSCRIBE,
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            successful=False,
            evaluated_at=NOW,
            message="Subscription failed.",
        )


def test_subscription_result_metadata_keys_unique(
) -> None:
    with pytest.raises(
        ValueError,
        match="metadata keys must be unique",
    ):
        SubscriptionResult(
            request_id="request-001",
            connection_id="connection-001",
            subscription_id="subscription-001",
            action=SubscriptionAction.SUBSCRIBE,
            symbol="NVDA",
            market="NASDAQ",
            data_type=MarketDataType.QUOTE,
            successful=True,
            evaluated_at=NOW,
            provider_subscription_id=(
                "ibkr-subscription-001"
            ),
            metadata=(
                ("source", "adapter"),
                ("source", "duplicate"),
            ),
        )


@pytest.mark.parametrize(
    "model",
    [
        connection_report(),
        subscription_request(),
        successful_subscription_result(),
        unsuccessful_subscription_result(),
    ],
)
def test_remaining_adapter_models_are_immutable(
    model: object,
) -> None:
    with pytest.raises(FrozenInstanceError):
        if isinstance(model, MarketDataConnectionReport):
            model.report_id = "changed"
        else:
            model.request_id = "changed"