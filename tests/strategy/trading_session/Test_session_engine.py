from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from app.strategy.trading_session.session_engine import (
    EnterpriseTradingSessionEngine,
)
from app.strategy.trading_session.session_models import (
    SessionDecision,
    SessionState,
    SessionType,
    SessionWindow,
    TradingCalendar,
)


NEW_YORK = ZoneInfo("America/New_York")

TRADING_DATE = date(2026, 8, 4)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def timestamp(
    hour: int,
    minute: int = 0,
    *,
    day: int = 4,
) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        minute,
        tzinfo=NEW_YORK,
    )


def pre_market_window() -> SessionWindow:
    return SessionWindow(
        window_id="pre-market-window",
        session_type=SessionType.PRE_MARKET,
        opens_at=time(4, 0),
        closes_at=time(9, 30),
        trading_allowed=True,
        order_types=("LIMIT",),
    )


def regular_window() -> SessionWindow:
    return SessionWindow(
        window_id="regular-window",
        session_type=SessionType.REGULAR,
        opens_at=time(9, 30),
        closes_at=time(16, 0),
        trading_allowed=True,
        order_types=("MARKET", "LIMIT"),
    )


def after_hours_window() -> SessionWindow:
    return SessionWindow(
        window_id="after-hours-window",
        session_type=SessionType.AFTER_HOURS,
        opens_at=time(16, 0),
        closes_at=time(20, 0),
        trading_allowed=True,
        order_types=("LIMIT",),
    )


def calendar(
    *,
    calendar_id: str = "calendar-001",
    market: str = "NYSE",
    effective_from: date | None = date(2026, 1, 1),
    effective_to: date | None = date(2026, 12, 31),
) -> TradingCalendar:
    return TradingCalendar(
        calendar_id=calendar_id,
        market=market,
        timezone_name="America/New_York",
        trading_days=(0, 1, 2, 3, 4),
        windows=(
            pre_market_window(),
            regular_window(),
            after_hours_window(),
        ),
        holidays=(),
        effective_from=effective_from,
        effective_to=effective_to,
    )


def engine(
    current_time: datetime | None = None,
) -> EnterpriseTradingSessionEngine:
    return EnterpriseTradingSessionEngine(
        clock=FixedClock(
            current_time or timestamp(10, 0)
        )
    )


def registered_engine(
    current_time: datetime | None = None,
) -> EnterpriseTradingSessionEngine:
    value = engine(current_time)
    value.register_calendar(calendar())
    return value


def test_register_calendar() -> None:
    value = engine()
    item = calendar()

    registered = value.register_calendar(item)

    assert registered == item
    assert value.calendar_ids == ("calendar-001",)
    assert value.markets == ("NYSE",)


def test_register_calendar_requires_calendar_model() -> None:
    with pytest.raises(
        TypeError,
        match="calendar must be a TradingCalendar",
    ):
        engine().register_calendar(object())


def test_duplicate_calendar_id_is_rejected() -> None:
    value = engine()
    value.register_calendar(calendar())

    with pytest.raises(
        ValueError,
        match="calendar_id is already registered",
    ):
        value.register_calendar(calendar())


def test_market_can_have_only_one_calendar() -> None:
    value = engine()
    value.register_calendar(calendar())

    with pytest.raises(
        ValueError,
        match=(
            "market already has a registered calendar"
        ),
    ):
        value.register_calendar(
            calendar(
                calendar_id="calendar-002",
                market="NYSE",
            )
        )


def test_register_multiple_markets() -> None:
    value = engine()

    value.register_calendar(calendar())

    value.register_calendar(
        calendar(
            calendar_id="calendar-002",
            market="NASDAQ",
        )
    )

    assert value.calendar_ids == (
        "calendar-001",
        "calendar-002",
    )
    assert value.markets == (
        "NASDAQ",
        "NYSE",
    )


def test_get_calendar() -> None:
    value = registered_engine()

    result = value.get_calendar(
        "calendar-001"
    )

    assert result.market == "NYSE"


def test_get_calendar_normalizes_identifier() -> None:
    value = registered_engine()

    result = value.get_calendar(
        "  calendar-001  "
    )

    assert result.calendar_id == "calendar-001"


def test_get_unknown_calendar_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="calendar not found",
    ):
        engine().get_calendar("missing")


def test_calendar_for_market() -> None:
    value = registered_engine()

    result = value.calendar_for_market("nyse")

    assert result.calendar_id == "calendar-001"


def test_calendar_for_market_normalizes_text() -> None:
    value = registered_engine()

    result = value.calendar_for_market(
        "  nyse  "
    )

    assert result.market == "NYSE"


def test_unknown_market_calendar_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="market calendar not found",
    ):
        engine().calendar_for_market("NASDAQ")


def test_unregister_calendar() -> None:
    value = registered_engine()

    removed = value.unregister_calendar(
        "calendar-001"
    )

    assert removed.market == "NYSE"
    assert value.calendar_ids == ()
    assert value.markets == ()


def test_unregister_unknown_calendar_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="calendar not found",
    ):
        engine().unregister_calendar("missing")


def test_evaluate_regular_session() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0),
    )

    assert report.status is SessionState.OPEN
    assert report.decision is SessionDecision.ALLOW
    assert report.session is not None
    assert (
        report.session.session_type
        is SessionType.REGULAR
    )
    assert report.session.trading_allowed is True


def test_regular_session_records_allowed_order_types() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(11, 0),
    )

    assert report.session is not None
    assert report.session.metadata == (
        (
            "allowed_order_types",
            "MARKET,LIMIT",
        ),
    )


def test_evaluate_pre_market_session() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(8, 0),
    )

    assert report.status is SessionState.PRE_MARKET
    assert (
        report.decision
        is SessionDecision.ALLOW_LIMITED
    )
    assert report.session is not None
    assert (
        report.session.session_type
        is SessionType.PRE_MARKET
    )
    assert report.session.trading_allowed is True


def test_pre_market_allows_limit_orders_only() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(7, 0),
    )

    assert report.session is not None
    assert report.session.metadata == (
        (
            "allowed_order_types",
            "LIMIT",
        ),
    )


def test_evaluate_after_hours_session() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(17, 30),
    )

    assert (
        report.status
        is SessionState.AFTER_HOURS
    )
    assert (
        report.decision
        is SessionDecision.ALLOW_LIMITED
    )
    assert report.session is not None
    assert (
        report.session.session_type
        is SessionType.AFTER_HOURS
    )


def test_before_first_window_queues_orders() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(3, 30),
    )

    assert report.status is SessionState.SCHEDULED
    assert report.decision is SessionDecision.QUEUE
    assert report.session is not None
    assert report.session.trading_allowed is False
    assert report.session.opened_at is None


def test_after_final_window_rejects_orders() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(20, 30),
    )

    assert report.status is SessionState.CLOSED
    assert report.decision is SessionDecision.REJECT
    assert report.session is not None
    assert report.session.closed_at is not None
    assert report.session.trading_allowed is False


def test_regular_session_opens_at_boundary() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(9, 30),
    )

    assert report.status is SessionState.OPEN
    assert report.session is not None
    assert (
        report.session.session_type
        is SessionType.REGULAR
    )


def test_after_hours_begins_at_regular_close() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(16, 0),
    )

    assert (
        report.status
        is SessionState.AFTER_HOURS
    )
    assert report.session is not None
    assert (
        report.session.session_type
        is SessionType.AFTER_HOURS
    )


def test_market_is_closed_at_final_boundary() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(20, 0),
    )

    assert report.status is SessionState.CLOSED
    assert report.decision is SessionDecision.REJECT


def test_weekend_is_closed() -> None:
    value = registered_engine()

    # August 8, 2026 is Saturday.
    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(
            10,
            0,
            day=8,
        ),
    )

    assert report.status is SessionState.SCHEDULED
    assert report.decision is SessionDecision.REJECT
    assert report.session is not None
    assert report.session.trading_allowed is False
    assert "non-trading day" in (
        report.session.reason
    )


def test_calendar_before_effective_date_is_closed() -> None:
    value = engine()

    value.register_calendar(
        calendar(
            effective_from=date(2026, 9, 1),
            effective_to=date(2026, 12, 31),
        )
    )

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0),
    )

    assert report.status is SessionState.SCHEDULED
    assert report.decision is SessionDecision.REJECT
    assert report.session is not None
    assert "not effective" in report.session.reason


def test_calendar_after_effective_date_is_closed() -> None:
    value = engine()

    value.register_calendar(
        calendar(
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 7, 31),
        )
    )

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0),
    )

    assert report.status is SessionState.SCHEDULED
    assert report.decision is SessionDecision.REJECT


def test_evaluate_uses_engine_clock() -> None:
    value = registered_engine(
        timestamp(10, 15)
    )

    report = value.evaluate(
        market="NYSE"
    )

    assert report.status is SessionState.OPEN
    assert report.evaluated_at == timestamp(10, 15)


def test_utc_timestamp_is_converted_to_market_timezone() -> None:
    value = registered_engine()

    # 14:00 UTC is 10:00 in New York during EDT.
    utc_time = datetime(
        2026,
        8,
        4,
        14,
        0,
        tzinfo=timezone.utc,
    )

    report = value.evaluate(
        market="NYSE",
        evaluated_at=utc_time,
    )

    assert report.status is SessionState.OPEN
    assert report.evaluated_at.hour == 10
    assert report.evaluated_at.tzinfo == NEW_YORK


def test_session_is_stored_for_trading_date() -> None:
    value = registered_engine()

    report = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0),
    )

    stored = value.get_session(
        market="NYSE",
        trading_date=TRADING_DATE,
    )

    assert report.session == stored


def test_get_unknown_session_is_rejected() -> None:
    value = registered_engine()

    with pytest.raises(
        KeyError,
        match="session not found",
    ):
        value.get_session(
            market="NYSE",
            trading_date=TRADING_DATE,
        )


def test_session_id_is_reused_during_same_day() -> None:
    value = registered_engine()

    first = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(8, 0),
    )

    second = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0),
    )

    assert first.session is not None
    assert second.session is not None
    assert (
        first.session.session_id
        == second.session.session_id
    )


def test_session_ids_are_deterministic_across_days() -> None:
    value = registered_engine()

    first = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0, day=4),
    )

    second = value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0, day=5),
    )

    assert first.session is not None
    assert second.session is not None

    assert first.session.session_id == (
        "session-000001"
    )
    assert second.session.session_id == (
        "session-000002"
    )


def test_history_records_each_evaluation() -> None:
    value = registered_engine()

    value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(8, 0),
    )

    value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0),
    )

    assert len(value.history) == 2


def test_reports_for_market() -> None:
    value = registered_engine()

    value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(8, 0),
    )

    value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0),
    )

    reports = value.reports_for_market(
        "nyse"
    )

    assert len(reports) == 2


def test_reports_for_date() -> None:
    value = registered_engine()

    value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(8, 0, day=4),
    )

    value.evaluate(
        market="NYSE",
        evaluated_at=timestamp(10, 0, day=5),
    )

    reports = value.reports_for_date(
        market="NYSE",
        trading_date=TRADING_DATE,
    )

    assert len(reports) == 1
    assert reports[0].session is not None
    assert (
        reports[0].session.trading_date
        == TRADING_DATE
    )