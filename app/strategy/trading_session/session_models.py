from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from zoneinfo import ZoneInfo


class SessionState(str, Enum):
    """Current lifecycle state of a trading session."""

    SCHEDULED = "SCHEDULED"
    PRE_MARKET = "PRE_MARKET"
    OPEN = "OPEN"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"
    HALTED = "HALTED"
    FAILED = "FAILED"


class SessionDecision(str, Enum):
    """Trading decision produced by the session manager."""

    ALLOW = "ALLOW"
    ALLOW_LIMITED = "ALLOW_LIMITED"
    QUEUE = "QUEUE"
    REJECT = "REJECT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_ACTION = "NO_ACTION"


class SessionType(str, Enum):
    """Supported trading-session windows."""

    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    FULL_DAY = "FULL_DAY"


class HolidayType(str, Enum):
    """How a holiday affects a market session."""

    FULL_CLOSE = "FULL_CLOSE"
    EARLY_CLOSE = "EARLY_CLOSE"
    LATE_OPEN = "LATE_OPEN"


_TERMINAL_STATES = {
    SessionState.CLOSED,
    SessionState.FAILED,
}


@dataclass(frozen=True, slots=True)
class TradingHoliday:
    """Immutable market-holiday definition."""

    holiday_id: str
    market: str
    holiday_date: date
    name: str
    holiday_type: HolidayType
    early_close_time: time | None = None
    late_open_time: time | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_holiday_id = SessionModelSupport.required_text(
            self.holiday_id,
            "holiday_id",
        )
        normalized_market = SessionModelSupport.required_text(
            self.market,
            "market",
        ).upper()
        normalized_name = SessionModelSupport.required_text(
            self.name,
            "name",
        )

        if not isinstance(self.holiday_date, date):
            raise TypeError(
                "holiday_date must be a date"
            )

        if isinstance(self.holiday_date, datetime):
            raise TypeError(
                "holiday_date must be a date, not a datetime"
            )

        if not isinstance(self.holiday_type, HolidayType):
            raise TypeError(
                "holiday_type must be a HolidayType"
            )

        if (
            self.early_close_time is not None
            and not isinstance(self.early_close_time, time)
        ):
            raise TypeError(
                "early_close_time must be a time or None"
            )

        if (
            self.late_open_time is not None
            and not isinstance(self.late_open_time, time)
        ):
            raise TypeError(
                "late_open_time must be a time or None"
            )

        if self.holiday_type is HolidayType.FULL_CLOSE:
            if self.early_close_time is not None:
                raise ValueError(
                    "full-close holidays must not include "
                    "early_close_time"
                )

            if self.late_open_time is not None:
                raise ValueError(
                    "full-close holidays must not include "
                    "late_open_time"
                )

        if self.holiday_type is HolidayType.EARLY_CLOSE:
            if self.early_close_time is None:
                raise ValueError(
                    "early-close holidays must include "
                    "early_close_time"
                )

            if self.late_open_time is not None:
                raise ValueError(
                    "early-close holidays must not include "
                    "late_open_time"
                )

        if self.holiday_type is HolidayType.LATE_OPEN:
            if self.late_open_time is None:
                raise ValueError(
                    "late-open holidays must include "
                    "late_open_time"
                )

            if self.early_close_time is not None:
                raise ValueError(
                    "late-open holidays must not include "
                    "early_close_time"
                )

        normalized_metadata = SessionModelSupport.normalize_pairs(
            self.metadata,
            "metadata",
        )

        object.__setattr__(
            self,
            "holiday_id",
            normalized_holiday_id,
        )
        object.__setattr__(
            self,
            "market",
            normalized_market,
        )
        object.__setattr__(
            self,
            "name",
            normalized_name,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )


@dataclass(frozen=True, slots=True)
class SessionWindow:
    """Immutable market-session time window."""

    window_id: str
    session_type: SessionType
    opens_at: time
    closes_at: time
    trading_allowed: bool = True
    order_types: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_window_id = SessionModelSupport.required_text(
            self.window_id,
            "window_id",
        )

        if not isinstance(self.session_type, SessionType):
            raise TypeError(
                "session_type must be a SessionType"
            )

        if not isinstance(self.opens_at, time):
            raise TypeError(
                "opens_at must be a time"
            )

        if not isinstance(self.closes_at, time):
            raise TypeError(
                "closes_at must be a time"
            )

        if self.opens_at >= self.closes_at:
            raise ValueError(
                "opens_at must be earlier than closes_at"
            )

        if not isinstance(self.trading_allowed, bool):
            raise TypeError(
                "trading_allowed must be a bool"
            )

        normalized_order_types: list[str] = []

        for order_type in self.order_types:
            normalized_order_types.append(
                SessionModelSupport.required_text(
                    order_type,
                    "order_type",
                ).upper()
            )

        if len(set(normalized_order_types)) != len(
            normalized_order_types
        ):
            raise ValueError(
                "order_types must be unique"
            )

        if (
            not self.trading_allowed
            and normalized_order_types
        ):
            raise ValueError(
                "non-trading windows must not include order_types"
            )

        normalized_metadata = SessionModelSupport.normalize_pairs(
            self.metadata,
            "metadata",
        )

        object.__setattr__(
            self,
            "window_id",
            normalized_window_id,
        )
        object.__setattr__(
            self,
            "order_types",
            tuple(normalized_order_types),
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )


@dataclass(frozen=True, slots=True)
class TradingCalendar:
    """Immutable market calendar and session schedule."""

    calendar_id: str
    market: str
    timezone_name: str
    trading_days: tuple[int, ...]
    windows: tuple[SessionWindow, ...]
    holidays: tuple[TradingHoliday, ...] = field(
        default_factory=tuple
    )
    effective_from: date | None = None
    effective_to: date | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_calendar_id = SessionModelSupport.required_text(
            self.calendar_id,
            "calendar_id",
        )
        normalized_market = SessionModelSupport.required_text(
            self.market,
            "market",
        ).upper()
        normalized_timezone_name = (
            SessionModelSupport.required_text(
                self.timezone_name,
                "timezone_name",
            )
        )

        try:
            ZoneInfo(normalized_timezone_name)
        except Exception as exc:
            raise ValueError(
                "timezone_name must be a valid IANA timezone"
            ) from exc

        normalized_trading_days = tuple(self.trading_days)

        if not normalized_trading_days:
            raise ValueError(
                "trading_days must not be empty"
            )

        for trading_day in normalized_trading_days:
            if not isinstance(trading_day, int):
                raise TypeError(
                    "every trading day must be an integer"
                )

            if not 0 <= trading_day <= 6:
                raise ValueError(
                    "trading days must be between 0 and 6"
                )

        if len(set(normalized_trading_days)) != len(
            normalized_trading_days
        ):
            raise ValueError(
                "trading_days must be unique"
            )

        if normalized_trading_days != tuple(
            sorted(normalized_trading_days)
        ):
            raise ValueError(
                "trading_days must be ordered"
            )

        normalized_windows = tuple(self.windows)

        if not normalized_windows:
            raise ValueError(
                "windows must not be empty"
            )

        for window in normalized_windows:
            if not isinstance(window, SessionWindow):
                raise TypeError(
                    "every window must be a SessionWindow"
                )

        window_ids = [
            window.window_id
            for window in normalized_windows
        ]

        if len(set(window_ids)) != len(window_ids):
            raise ValueError(
                "window_id values must be unique"
            )

        session_types = [
            window.session_type
            for window in normalized_windows
        ]

        if len(set(session_types)) != len(session_types):
            raise ValueError(
                "session_type values must be unique"
            )

        windows_by_open = tuple(
            sorted(
                normalized_windows,
                key=lambda window: window.opens_at,
            )
        )

        if windows_by_open != normalized_windows:
            raise ValueError(
                "windows must be ordered by opens_at"
            )

        for previous, current in zip(
            normalized_windows,
            normalized_windows[1:],
        ):
            if current.opens_at < previous.closes_at:
                raise ValueError(
                    "session windows must not overlap"
                )

        normalized_holidays = tuple(self.holidays)

        for holiday in normalized_holidays:
            if not isinstance(holiday, TradingHoliday):
                raise TypeError(
                    "every holiday must be a TradingHoliday"
                )

            if holiday.market != normalized_market:
                raise ValueError(
                    "holiday market must match calendar market"
                )

        holiday_ids = [
            holiday.holiday_id
            for holiday in normalized_holidays
        ]

        if len(set(holiday_ids)) != len(holiday_ids):
            raise ValueError(
                "holiday_id values must be unique"
            )

        holiday_dates = [
            holiday.holiday_date
            for holiday in normalized_holidays
        ]

        if len(set(holiday_dates)) != len(holiday_dates):
            raise ValueError(
                "holiday dates must be unique"
            )

        if holiday_dates != sorted(holiday_dates):
            raise ValueError(
                "holidays must be ordered by holiday_date"
            )

        if (
            self.effective_from is not None
            and not isinstance(self.effective_from, date)
        ):
            raise TypeError(
                "effective_from must be a date or None"
            )

        if (
            self.effective_to is not None
            and not isinstance(self.effective_to, date)
        ):
            raise TypeError(
                "effective_to must be a date or None"
            )

        if (
            isinstance(self.effective_from, datetime)
            or isinstance(self.effective_to, datetime)
        ):
            raise TypeError(
                "calendar effective dates must not be datetimes"
            )

        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError(
                "effective_to must not be earlier than effective_from"
            )

        normalized_metadata = SessionModelSupport.normalize_pairs(
            self.metadata,
            "metadata",
        )

        object.__setattr__(
            self,
            "calendar_id",
            normalized_calendar_id,
        )
        object.__setattr__(
            self,
            "market",
            normalized_market,
        )
        object.__setattr__(
            self,
            "timezone_name",
            normalized_timezone_name,
        )
        object.__setattr__(
            self,
            "trading_days",
            normalized_trading_days,
        )
        object.__setattr__(
            self,
            "windows",
            normalized_windows,
        )
        object.__setattr__(
            self,
            "holidays",
            normalized_holidays,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


@dataclass(frozen=True, slots=True)
class TradingSession:
    """Immutable state of one market trading day."""

    session_id: str
    calendar_id: str
    market: str
    trading_date: date
    state: SessionState
    session_type: SessionType | None
    opened_at: datetime | None
    closed_at: datetime | None
    evaluated_at: datetime
    trading_allowed: bool
    reason: str
    holiday_id: str | None = None
    halt_reason: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_session_id = SessionModelSupport.required_text(
            self.session_id,
            "session_id",
        )
        normalized_calendar_id = SessionModelSupport.required_text(
            self.calendar_id,
            "calendar_id",
        )
        normalized_market = SessionModelSupport.required_text(
            self.market,
            "market",
        ).upper()
        normalized_reason = SessionModelSupport.required_text(
            self.reason,
            "reason",
        )

        if not isinstance(self.trading_date, date):
            raise TypeError(
                "trading_date must be a date"
            )

        if isinstance(self.trading_date, datetime):
            raise TypeError(
                "trading_date must be a date, not a datetime"
            )

        if not isinstance(self.state, SessionState):
            raise TypeError(
                "state must be a SessionState"
            )

        if (
            self.session_type is not None
            and not isinstance(self.session_type, SessionType)
        ):
            raise TypeError(
                "session_type must be a SessionType or None"
            )

        SessionModelSupport.validate_datetime(
            self.evaluated_at,
            "evaluated_at",
        )

        if self.opened_at is not None:
            SessionModelSupport.validate_datetime(
                self.opened_at,
                "opened_at",
            )

        if self.closed_at is not None:
            SessionModelSupport.validate_datetime(
                self.closed_at,
                "closed_at",
            )

        if (
            self.opened_at is not None
            and self.opened_at > self.evaluated_at
        ):
            raise ValueError(
                "opened_at must not be later than evaluated_at"
            )

        if (
            self.closed_at is not None
            and self.opened_at is None
        ):
            raise ValueError(
                "closed sessions must include opened_at"
            )

        if (
            self.closed_at is not None
            and self.opened_at is not None
            and self.closed_at < self.opened_at
        ):
            raise ValueError(
                "closed_at must not be earlier than opened_at"
            )

        if (
            self.closed_at is not None
            and self.closed_at > self.evaluated_at
        ):
            raise ValueError(
                "closed_at must not be later than evaluated_at"
            )

        if not isinstance(self.trading_allowed, bool):
            raise TypeError(
                "trading_allowed must be a bool"
            )

        normalized_holiday_id = SessionModelSupport.optional_text(
            self.holiday_id,
            "holiday_id",
        )
        normalized_halt_reason = SessionModelSupport.optional_text(
            self.halt_reason,
            "halt_reason",
        )

        if self.state is SessionState.OPEN:
            if not self.trading_allowed:
                raise ValueError(
                    "open sessions must allow trading"
                )

            if self.session_type is None:
                raise ValueError(
                    "open sessions must include session_type"
                )

            if self.opened_at is None:
                raise ValueError(
                    "open sessions must include opened_at"
                )

            if self.closed_at is not None:
                raise ValueError(
                    "open sessions must not include closed_at"
                )

        if self.state in {
            SessionState.SCHEDULED,
            SessionState.CLOSED,
            SessionState.HALTED,
            SessionState.FAILED,
        }:
            if self.trading_allowed:
                raise ValueError(
                    f"{self.state.value.lower()} sessions "
                    "must not allow trading"
                )

        if self.state is SessionState.CLOSED:
            if self.closed_at is None:
                raise ValueError(
                    "closed sessions must include closed_at"
                )

        if self.state is SessionState.HALTED:
            if normalized_halt_reason is None:
                raise ValueError(
                    "halted sessions must include halt_reason"
                )
        elif normalized_halt_reason is not None:
            raise ValueError(
                "only halted sessions may include halt_reason"
            )

        if (
            normalized_holiday_id is not None
            and self.trading_allowed
        ):
            raise ValueError(
                "holiday sessions must not allow trading"
            )

        normalized_metadata = SessionModelSupport.normalize_pairs(
            self.metadata,
            "metadata",
        )
        normalized_warnings = (
            SessionModelSupport.normalize_warnings(
                self.warnings
            )
        )

        object.__setattr__(
            self,
            "session_id",
            normalized_session_id,
        )
        object.__setattr__(
            self,
            "calendar_id",
            normalized_calendar_id,
        )
        object.__setattr__(
            self,
            "market",
            normalized_market,
        )
        object.__setattr__(
            self,
            "reason",
            normalized_reason,
        )
        object.__setattr__(
            self,
            "holiday_id",
            normalized_holiday_id,
        )
        object.__setattr__(
            self,
            "halt_reason",
            normalized_halt_reason,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )

    @property
    def is_terminal(self) -> bool:
        return self.state in _TERMINAL_STATES


@dataclass(frozen=True, slots=True)
class SessionReport:
    """Unified decision returned by the session manager."""

    status: SessionState
    decision: SessionDecision
    session: TradingSession | None
    recommendation: str
    evaluated_at: datetime
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, SessionState):
            raise TypeError(
                "status must be a SessionState"
            )

        if not isinstance(self.decision, SessionDecision):
            raise TypeError(
                "decision must be a SessionDecision"
            )

        if (
            self.session is not None
            and not isinstance(self.session, TradingSession)
        ):
            raise TypeError(
                "session must be a TradingSession or None"
            )

        normalized_recommendation = (
            SessionModelSupport.required_text(
                self.recommendation,
                "recommendation",
            )
        )

        SessionModelSupport.validate_datetime(
            self.evaluated_at,
            "evaluated_at",
        )

        normalized_error = SessionModelSupport.optional_text(
            self.error,
            "error",
        )

        if self.status is SessionState.FAILED:
            if normalized_error is None:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only failed reports may include an error"
            )

        if self.status is not SessionState.FAILED:
            if self.session is None:
                raise ValueError(
                    "non-failed reports must include a session"
                )

        if self.session is not None:
            if self.session.state is not self.status:
                raise ValueError(
                    "report status must match session state"
                )

            if self.session.evaluated_at != self.evaluated_at:
                raise ValueError(
                    "report evaluated_at must match session"
                )

        if self.decision is SessionDecision.ALLOW:
            if self.session is None:
                raise ValueError(
                    "allow decisions require a session"
                )

            if not self.session.trading_allowed:
                raise ValueError(
                    "allow decisions require trading_allowed=True"
                )

        if self.decision in {
            SessionDecision.REJECT,
            SessionDecision.QUEUE,
        }:
            if (
                self.session is not None
                and self.session.trading_allowed
            ):
                raise ValueError(
                    "reject and queue decisions require "
                    "trading_allowed=False"
                )

        normalized_warnings = (
            SessionModelSupport.normalize_warnings(
                self.warnings
            )
        )

        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )


class SessionModelSupport:
    """Shared validation helpers for session models."""

    @staticmethod
    def required_text(
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

    @staticmethod
    def optional_text(
        value: str | None,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string or None"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized

    @staticmethod
    def validate_datetime(
        value: datetime,
        field_name: str,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )

    @staticmethod
    def normalize_pairs(
        values: tuple[tuple[str, str], ...],
        collection_name: str,
    ) -> tuple[tuple[str, str], ...]:
        normalized: list[tuple[str, str]] = []
        seen_keys: set[str] = set()

        for item in values:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    f"each {collection_name} item must be "
                    "a two-item tuple"
                )

            raw_key, raw_value = item
            key = str(raw_key).strip()
            value = str(raw_value).strip()

            if not key:
                raise ValueError(
                    f"{collection_name} keys must not be empty"
                )

            if key in seen_keys:
                raise ValueError(
                    f"{collection_name} keys must be unique"
                )

            seen_keys.add(key)
            normalized.append(
                (key, value)
            )

        return tuple(normalized)

    @staticmethod
    def normalize_warnings(
        warnings: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        normalized: list[str] = []

        for warning in warnings:
            if not isinstance(warning, str):
                raise TypeError(
                    "every warning must be a string"
                )

            value = warning.strip()

            if not value:
                raise ValueError(
                    "warnings must not contain empty values"
                )

            normalized.append(value)

        return tuple(normalized)