from dataclasses import FrozenInstanceError
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.strategy.trading_session.session_models import (
    HolidayType,
    SessionDecision,
    SessionReport,
    SessionState,
    SessionType,
    SessionWindow,
    TradingCalendar,
    TradingHoliday,
    TradingSession,
)


NEW_YORK = ZoneInfo("America/New_York")

NOW = datetime(
    2026,
    8,
    4,
    10,
    0,
    tzinfo=NEW_YORK,
)

TRADING_DATE = date(2026, 8, 4)


def regular_window() -> SessionWindow:
    return SessionWindow(
        window_id="regular-window",
        session_type=SessionType.REGULAR,
        opens_at=time(9, 30),
        closes_at=time(16, 0),
        trading_allowed=True,
        order_types=("MARKET", "LIMIT"),
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


def after_hours_window() -> SessionWindow:
    return SessionWindow(
        window_id="after-hours-window",
        session_type=SessionType.AFTER_HOURS,
        opens_at=time(16, 0),
        closes_at=time(20, 0),
        trading_allowed=True,
        order_types=("LIMIT",),
    )


def full_close_holiday() -> TradingHoliday:
    return TradingHoliday(
        holiday_id="holiday-001",
        market="NYSE",
        holiday_date=date(2026, 12, 25),
        name="Christmas Day",
        holiday_type=HolidayType.FULL_CLOSE,
    )


def early_close_holiday() -> TradingHoliday:
    return TradingHoliday(
        holiday_id="holiday-002",
        market="NYSE",
        holiday_date=date(2026, 11, 27),
        name="Day After Thanksgiving",
        holiday_type=HolidayType.EARLY_CLOSE,
        early_close_time=time(13, 0),
    )


def late_open_holiday() -> TradingHoliday:
    return TradingHoliday(
        holiday_id="holiday-003",
        market="NYSE",
        holiday_date=date(2026, 12, 26),
        name="Delayed Opening",
        holiday_type=HolidayType.LATE_OPEN,
        late_open_time=time(10, 30),
    )


def calendar() -> TradingCalendar:
    return TradingCalendar(
        calendar_id="calendar-001",
        market="NYSE",
        timezone_name="America/New_York",
        trading_days=(0, 1, 2, 3, 4),
        windows=(
            pre_market_window(),
            regular_window(),
            after_hours_window(),
        ),
        holidays=(
            early_close_holiday(),
            full_close_holiday(),
        ),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )


def open_session() -> TradingSession:
    return TradingSession(
        session_id="session-001",
        calendar_id="calendar-001",
        market="NYSE",
        trading_date=TRADING_DATE,
        state=SessionState.OPEN,
        session_type=SessionType.REGULAR,
        opened_at=datetime(
            2026,
            8,
            4,
            9,
            30,
            tzinfo=NEW_YORK,
        ),
        closed_at=None,
        evaluated_at=NOW,
        trading_allowed=True,
        reason="Regular trading session is open.",
    )


def closed_session() -> TradingSession:
    return TradingSession(
        session_id="session-001",
        calendar_id="calendar-001",
        market="NYSE",
        trading_date=TRADING_DATE,
        state=SessionState.CLOSED,
        session_type=SessionType.REGULAR,
        opened_at=datetime(
            2026,
            8,
            4,
            9,
            30,
            tzinfo=NEW_YORK,
        ),
        closed_at=datetime(
            2026,
            8,
            4,
            16,
            0,
            tzinfo=NEW_YORK,
        ),
        evaluated_at=datetime(
            2026,
            8,
            4,
            16,
            1,
            tzinfo=NEW_YORK,
        ),
        trading_allowed=False,
        reason="Regular trading session is closed.",
    )


def halted_session() -> TradingSession:
    return TradingSession(
        session_id="session-001",
        calendar_id="calendar-001",
        market="NYSE",
        trading_date=TRADING_DATE,
        state=SessionState.HALTED,
        session_type=SessionType.REGULAR,
        opened_at=datetime(
            2026,
            8,
            4,
            9,
            30,
            tzinfo=NEW_YORK,
        ),
        closed_at=None,
        evaluated_at=NOW,
        trading_allowed=False,
        reason="Trading is temporarily halted.",
        halt_reason="Exchange-wide volatility halt.",
    )


def test_full_close_holiday() -> None:
    value = full_close_holiday()

    assert value.market == "NYSE"
    assert value.holiday_type is HolidayType.FULL_CLOSE
    assert value.early_close_time is None
    assert value.late_open_time is None


def test_holiday_text_is_normalized() -> None:
    value = TradingHoliday(
        holiday_id="  holiday-001  ",
        market="  nyse  ",
        holiday_date=date(2026, 12, 25),
        name="  Christmas Day  ",
        holiday_type=HolidayType.FULL_CLOSE,
    )

    assert value.holiday_id == "holiday-001"
    assert value.market == "NYSE"
    assert value.name == "Christmas Day"


def test_holiday_date_rejects_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="holiday_date must be a date, not a datetime",
    ):
        TradingHoliday(
            holiday_id="holiday-001",
            market="NYSE",
            holiday_date=NOW,
            name="Invalid Holiday",
            holiday_type=HolidayType.FULL_CLOSE,
        )


def test_full_close_rejects_early_close_time() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "full-close holidays must not include "
            "early_close_time"
        ),
    ):
        TradingHoliday(
            holiday_id="holiday-001",
            market="NYSE",
            holiday_date=date(2026, 12, 25),
            name="Christmas Day",
            holiday_type=HolidayType.FULL_CLOSE,
            early_close_time=time(13, 0),
        )


def test_early_close_requires_time() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "early-close holidays must include "
            "early_close_time"
        ),
    ):
        TradingHoliday(
            holiday_id="holiday-001",
            market="NYSE",
            holiday_date=date(2026, 11, 27),
            name="Early Close",
            holiday_type=HolidayType.EARLY_CLOSE,
        )


def test_valid_early_close_holiday() -> None:
    value = early_close_holiday()

    assert value.early_close_time == time(13, 0)
    assert value.late_open_time is None


def test_late_open_requires_time() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "late-open holidays must include "
            "late_open_time"
        ),
    ):
        TradingHoliday(
            holiday_id="holiday-001",
            market="NYSE",
            holiday_date=date(2026, 12, 26),
            name="Late Open",
            holiday_type=HolidayType.LATE_OPEN,
        )


def test_valid_late_open_holiday() -> None:
    value = late_open_holiday()

    assert value.late_open_time == time(10, 30)
    assert value.early_close_time is None


def test_holiday_metadata_is_normalized() -> None:
    value = TradingHoliday(
        holiday_id="holiday-001",
        market="NYSE",
        holiday_date=date(2026, 12, 25),
        name="Christmas Day",
        holiday_type=HolidayType.FULL_CLOSE,
        metadata=[
            ("  source  ", "  exchange  "),
        ],
    )

    assert value.metadata == (
        ("source", "exchange"),
    )


def test_session_window() -> None:
    value = regular_window()

    assert value.session_type is SessionType.REGULAR
    assert value.opens_at == time(9, 30)
    assert value.closes_at == time(16, 0)
    assert value.order_types == ("MARKET", "LIMIT")


def test_window_text_is_normalized() -> None:
    value = SessionWindow(
        window_id="  regular-window  ",
        session_type=SessionType.REGULAR,
        opens_at=time(9, 30),
        closes_at=time(16, 0),
        order_types=("  market  ", "  limit  "),
    )

    assert value.window_id == "regular-window"
    assert value.order_types == ("MARKET", "LIMIT")


def test_window_requires_open_before_close() -> None:
    with pytest.raises(
        ValueError,
        match="opens_at must be earlier than closes_at",
    ):
        SessionWindow(
            window_id="regular-window",
            session_type=SessionType.REGULAR,
            opens_at=time(16, 0),
            closes_at=time(9, 30),
        )


def test_window_order_types_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="order_types must be unique",
    ):
        SessionWindow(
            window_id="regular-window",
            session_type=SessionType.REGULAR,
            opens_at=time(9, 30),
            closes_at=time(16, 0),
            order_types=("LIMIT", "limit"),
        )


def test_non_trading_window_rejects_order_types() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-trading windows must not include order_types"
        ),
    ):
        SessionWindow(
            window_id="closed-window",
            session_type=SessionType.FULL_DAY,
            opens_at=time(0, 0),
            closes_at=time(23, 59),
            trading_allowed=False,
            order_types=("LIMIT",),
        )


def test_trading_calendar() -> None:
    value = calendar()

    assert value.market == "NYSE"
    assert value.trading_days == (0, 1, 2, 3, 4)
    assert len(value.windows) == 3
    assert isinstance(value.timezone, ZoneInfo)


def test_calendar_timezone_must_be_valid() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "timezone_name must be a valid IANA timezone"
        ),
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="Invalid/Timezone",
            trading_days=(0, 1, 2, 3, 4),
            windows=(regular_window(),),
        )


def test_calendar_requires_trading_days() -> None:
    with pytest.raises(
        ValueError,
        match="trading_days must not be empty",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(),
            windows=(regular_window(),),
        )


def test_trading_days_must_be_valid() -> None:
    with pytest.raises(
        ValueError,
        match="trading days must be between 0 and 6",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 7),
            windows=(regular_window(),),
        )


def test_trading_days_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="trading_days must be unique",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 1, 2),
            windows=(regular_window(),),
        )


def test_trading_days_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match="trading_days must be ordered",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 2, 1),
            windows=(regular_window(),),
        )


def test_calendar_requires_windows() -> None:
    with pytest.raises(
        ValueError,
        match="windows must not be empty",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(),
        )


def test_window_ids_must_be_unique() -> None:
    window = regular_window()

    with pytest.raises(
        ValueError,
        match="window_id values must be unique",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(window, window),
        )


def test_session_types_must_be_unique() -> None:
    first = regular_window()
    second = SessionWindow(
        window_id="regular-window-002",
        session_type=SessionType.REGULAR,
        opens_at=time(16, 0),
        closes_at=time(17, 0),
    )

    with pytest.raises(
        ValueError,
        match="session_type values must be unique",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(first, second),
        )


def test_windows_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match="windows must be ordered by opens_at",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(
                regular_window(),
                pre_market_window(),
            ),
        )


def test_windows_must_not_overlap() -> None:
    overlapping = SessionWindow(
        window_id="overlap-window",
        session_type=SessionType.AFTER_HOURS,
        opens_at=time(15, 30),
        closes_at=time(18, 0),
    )

    with pytest.raises(
        ValueError,
        match="session windows must not overlap",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(
                regular_window(),
                overlapping,
            ),
        )


def test_holiday_market_must_match_calendar() -> None:
    holiday = TradingHoliday(
        holiday_id="holiday-001",
        market="NASDAQ",
        holiday_date=date(2026, 12, 25),
        name="Christmas Day",
        holiday_type=HolidayType.FULL_CLOSE,
    )

    with pytest.raises(
        ValueError,
        match="holiday market must match calendar market",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(regular_window(),),
            holidays=(holiday,),
        )


def test_holiday_ids_must_be_unique() -> None:
    holiday = full_close_holiday()

    with pytest.raises(
        ValueError,
        match="holiday_id values must be unique",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(regular_window(),),
            holidays=(holiday, holiday),
        )


def test_holiday_dates_must_be_unique() -> None:
    first = full_close_holiday()
    second = TradingHoliday(
        holiday_id="holiday-002",
        market="NYSE",
        holiday_date=first.holiday_date,
        name="Duplicate Holiday",
        holiday_type=HolidayType.FULL_CLOSE,
    )

    with pytest.raises(
        ValueError,
        match="holiday dates must be unique",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(regular_window(),),
            holidays=(first, second),
        )


def test_holidays_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match="holidays must be ordered by holiday_date",
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(regular_window(),),
            holidays=(
                full_close_holiday(),
                early_close_holiday(),
            ),
        )


def test_calendar_effective_dates_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "effective_to must not be earlier than "
            "effective_from"
        ),
    ):
        TradingCalendar(
            calendar_id="calendar-001",
            market="NYSE",
            timezone_name="America/New_York",
            trading_days=(0, 1, 2, 3, 4),
            windows=(regular_window(),),
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )


def test_open_trading_session() -> None:
    value = open_session()

    assert value.state is SessionState.OPEN
    assert value.trading_allowed is True
    assert value.session_type is SessionType.REGULAR
    assert value.is_terminal is False


def test_session_text_is_normalized() -> None:
    value = TradingSession(
        session_id="  session-001  ",
        calendar_id="  calendar-001  ",
        market="  nyse  ",
        trading_date=TRADING_DATE,
        state=SessionState.OPEN,
        session_type=SessionType.REGULAR,
        opened_at=datetime(
            2026,
            8,
            4,
            9,
            30,
            tzinfo=NEW_YORK,
        ),
        closed_at=None,
        evaluated_at=NOW,
        trading_allowed=True,
        reason="  Session open.  ",
    )

    assert value.session_id == "session-001"
    assert value.calendar_id == "calendar-001"
    assert value.market == "NYSE"
    assert value.reason == "Session open."


def test_open_session_requires_trading_allowed() -> None:
    with pytest.raises(
        ValueError,
        match="open sessions must allow trading",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=TRADING_DATE,
            state=SessionState.OPEN,
            session_type=SessionType.REGULAR,
            opened_at=NOW,
            closed_at=None,
            evaluated_at=NOW,
            trading_allowed=False,
            reason="Invalid open session.",
        )


def test_open_session_requires_session_type() -> None:
    with pytest.raises(
        ValueError,
        match="open sessions must include session_type",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=TRADING_DATE,
            state=SessionState.OPEN,
            session_type=None,
            opened_at=NOW,
            closed_at=None,
            evaluated_at=NOW,
            trading_allowed=True,
            reason="Invalid open session.",
        )


def test_open_session_requires_opened_at() -> None:
    with pytest.raises(
        ValueError,
        match="open sessions must include opened_at",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=TRADING_DATE,
            state=SessionState.OPEN,
            session_type=SessionType.REGULAR,
            opened_at=None,
            closed_at=None,
            evaluated_at=NOW,
            trading_allowed=True,
            reason="Invalid open session.",
        )


def test_closed_session() -> None:
    value = closed_session()

    assert value.state is SessionState.CLOSED
    assert value.trading_allowed is False
    assert value.closed_at is not None
    assert value.is_terminal is True


def test_closed_session_requires_closed_at() -> None:
    with pytest.raises(
        ValueError,
        match="closed sessions must include closed_at",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=TRADING_DATE,
            state=SessionState.CLOSED,
            session_type=SessionType.REGULAR,
            opened_at=NOW,
            closed_at=None,
            evaluated_at=NOW,
            trading_allowed=False,
            reason="Session closed.",
        )


def test_halted_session() -> None:
    value = halted_session()

    assert value.state is SessionState.HALTED
    assert value.halt_reason == (
        "Exchange-wide volatility halt."
    )


def test_halted_session_requires_reason() -> None:
    with pytest.raises(
        ValueError,
        match="halted sessions must include halt_reason",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=TRADING_DATE,
            state=SessionState.HALTED,
            session_type=SessionType.REGULAR,
            opened_at=NOW,
            closed_at=None,
            evaluated_at=NOW,
            trading_allowed=False,
            reason="Trading halted.",
        )


def test_non_halted_session_rejects_halt_reason() -> None:
    with pytest.raises(
        ValueError,
        match="only halted sessions may include halt_reason",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=TRADING_DATE,
            state=SessionState.OPEN,
            session_type=SessionType.REGULAR,
            opened_at=NOW,
            closed_at=None,
            evaluated_at=NOW,
            trading_allowed=True,
            reason="Session open.",
            halt_reason="Invalid halt.",
        )


def test_holiday_session_must_not_allow_trading() -> None:
    with pytest.raises(
        ValueError,
        match="holiday sessions must not allow trading",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=date(2026, 12, 25),
            state=SessionState.OPEN,
            session_type=SessionType.REGULAR,
            opened_at=NOW,
            closed_at=None,
            evaluated_at=NOW,
            trading_allowed=True,
            reason="Invalid holiday session.",
            holiday_id="holiday-001",
        )


def test_session_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="evaluated_at must be timezone-aware",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=TRADING_DATE,
            state=SessionState.SCHEDULED,
            session_type=None,
            opened_at=None,
            closed_at=None,
            evaluated_at=datetime(2026, 8, 4, 8, 0),
            trading_allowed=False,
            reason="Session scheduled.",
        )


def test_opened_at_must_not_follow_evaluated_at() -> None:
    with pytest.raises(
        ValueError,
        match="opened_at must not be later than evaluated_at",
    ):
        TradingSession(
            session_id="session-001",
            calendar_id="calendar-001",
            market="NYSE",
            trading_date=TRADING_DATE,
            state=SessionState.OPEN,
            session_type=SessionType.REGULAR,
            opened_at=NOW + timedelta(minutes=1),
            closed_at=None,
            evaluated_at=NOW,
            trading_allowed=True,
            reason="Invalid session.",
        )


def test_session_warnings_are_normalized() -> None:
    value = TradingSession(
        session_id="session-001",
        calendar_id="calendar-001",
        market="NYSE",
        trading_date=TRADING_DATE,
        state=SessionState.SCHEDULED,
        session_type=None,
        opened_at=None,
        closed_at=None,
        evaluated_at=NOW,
        trading_allowed=False,
        reason="Session scheduled.",
        warnings=["  Session warning.  "],
    )

    assert value.warnings == (
        "Session warning.",
    )


def test_session_report() -> None:
    session = open_session()

    report = SessionReport(
        status=SessionState.OPEN,
        decision=SessionDecision.ALLOW,
        session=session,
        recommendation="Trading may proceed.",
        evaluated_at=session.evaluated_at,
    )

    assert report.session == session
    assert report.decision is SessionDecision.ALLOW


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        SessionReport(
            status=SessionState.FAILED,
            decision=SessionDecision.REJECT,
            session=None,
            recommendation="Session evaluation failed.",
            evaluated_at=NOW,
        )


def test_non_failed_report_requires_session() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-failed reports must include a session"
        ),
    ):
        SessionReport(
            status=SessionState.CLOSED,
            decision=SessionDecision.REJECT,
            session=None,
            recommendation="Session closed.",
            evaluated_at=NOW,
        )


def test_report_status_must_match_session() -> None:
    with pytest.raises(
        ValueError,
        match="report status must match session state",
    ):
        SessionReport(
            status=SessionState.CLOSED,
            decision=SessionDecision.REJECT,
            session=open_session(),
            recommendation="Session closed.",
            evaluated_at=NOW,
        )


def test_report_evaluated_at_must_match_session() -> None:
    session = open_session()

    with pytest.raises(
        ValueError,
        match="report evaluated_at must match session",
    ):
        SessionReport(
            status=SessionState.OPEN,
            decision=SessionDecision.ALLOW,
            session=session,
            recommendation="Trading may proceed.",
            evaluated_at=NOW + timedelta(seconds=1),
        )


def test_allow_requires_trading_allowed() -> None:
    session = closed_session()

    with pytest.raises(
        ValueError,
        match=(
            "allow decisions require trading_allowed=True"
        ),
    ):
        SessionReport(
            status=SessionState.CLOSED,
            decision=SessionDecision.ALLOW,
            session=session,
            recommendation="Invalid allow decision.",
            evaluated_at=session.evaluated_at,
        )


def test_reject_requires_trading_not_allowed() -> None:
    session = open_session()

    with pytest.raises(
        ValueError,
        match=(
            "reject and queue decisions require "
            "trading_allowed=False"
        ),
    ):
        SessionReport(
            status=SessionState.OPEN,
            decision=SessionDecision.REJECT,
            session=session,
            recommendation="Invalid rejection.",
            evaluated_at=session.evaluated_at,
        )


def test_models_are_immutable() -> None:
    value = open_session()

    with pytest.raises(FrozenInstanceError):
        value.state = SessionState.CLOSED