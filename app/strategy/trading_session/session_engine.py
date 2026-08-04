from __future__ import annotations

from datetime import date, datetime
from typing import Callable

from .session_models import (
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


Clock = Callable[[], datetime]


class EnterpriseTradingSessionEngine:
    """Evaluates and controls enterprise market sessions."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
    ) -> None:
        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._clock = clock or self._system_clock

        self._calendars: dict[
            str,
            TradingCalendar,
        ] = {}

        self._market_calendars: dict[
            str,
            str,
        ] = {}

        self._sessions: dict[
            tuple[str, date],
            TradingSession,
        ] = {}

        self._history: list[
            SessionReport
        ] = []

        self._halts: dict[
            str,
            str,
        ] = {}

        self._next_session_number = 1

    @property
    def calendar_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._calendars)
        )

    @property
    def markets(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._market_calendars)
        )

    @property
    def history(
        self,
    ) -> tuple[SessionReport, ...]:
        return tuple(self._history)

    def register_calendar(
        self,
        calendar: TradingCalendar,
    ) -> TradingCalendar:
        if not isinstance(
            calendar,
            TradingCalendar,
        ):
            raise TypeError(
                "calendar must be a TradingCalendar"
            )

        if calendar.calendar_id in self._calendars:
            raise ValueError(
                "calendar_id is already registered"
            )

        if calendar.market in self._market_calendars:
            raise ValueError(
                "market already has a registered calendar"
            )

        self._calendars[
            calendar.calendar_id
        ] = calendar

        self._market_calendars[
            calendar.market
        ] = calendar.calendar_id

        return calendar

    def unregister_calendar(
        self,
        calendar_id: str,
    ) -> TradingCalendar:
        normalized_calendar_id = (
            self._normalize_identifier(
                calendar_id,
                "calendar_id",
            )
        )

        try:
            calendar = self._calendars.pop(
                normalized_calendar_id
            )
        except KeyError as exc:
            raise KeyError(
                "calendar not found: "
                f"{normalized_calendar_id}"
            ) from exc

        self._market_calendars.pop(
            calendar.market,
            None,
        )

        self._halts.pop(
            calendar.market,
            None,
        )

        return calendar

    def get_calendar(
        self,
        calendar_id: str,
    ) -> TradingCalendar:
        normalized_calendar_id = (
            self._normalize_identifier(
                calendar_id,
                "calendar_id",
            )
        )

        try:
            return self._calendars[
                normalized_calendar_id
            ]
        except KeyError as exc:
            raise KeyError(
                "calendar not found: "
                f"{normalized_calendar_id}"
            ) from exc

    def calendar_for_market(
        self,
        market: str,
    ) -> TradingCalendar:
        normalized_market = (
            self._normalize_identifier(
                market,
                "market",
            ).upper()
        )

        try:
            calendar_id = self._market_calendars[
                normalized_market
            ]
        except KeyError as exc:
            raise KeyError(
                "market calendar not found: "
                f"{normalized_market}"
            ) from exc

        return self._calendars[calendar_id]

    def evaluate(
        self,
        *,
        market: str,
        evaluated_at: datetime | None = None,
    ) -> SessionReport:
        calendar = self.calendar_for_market(
            market
        )

        effective_time = (
            self._current_time()
            if evaluated_at is None
            else self._validate_evaluated_at(
                evaluated_at
            )
        )

        market_time = effective_time.astimezone(
            calendar.timezone
        )

        trading_date = market_time.date()

        if not self._calendar_is_effective(
            calendar=calendar,
            trading_date=trading_date,
        ):
            return self._closed_report(
                calendar=calendar,
                evaluated_at=market_time,
                reason=(
                    "The trading calendar is not effective "
                    "for this date."
                ),
                decision=SessionDecision.REJECT,
            )

        halt_reason = self._halts.get(
            calendar.market
        )

        if halt_reason is not None:
            return self._halted_report(
                calendar=calendar,
                evaluated_at=market_time,
                halt_reason=halt_reason,
            )

        holiday = self._holiday_for_date(
            calendar=calendar,
            trading_date=trading_date,
        )

        if (
            holiday is not None
            and holiday.holiday_type
            is HolidayType.FULL_CLOSE
        ):
            return self._holiday_closed_report(
                calendar=calendar,
                holiday=holiday,
                evaluated_at=market_time,
            )

        if (
            market_time.weekday()
            not in calendar.trading_days
        ):
            return self._closed_report(
                calendar=calendar,
                evaluated_at=market_time,
                reason=(
                    "The market is closed on this "
                    "non-trading day."
                ),
                decision=SessionDecision.REJECT,
            )

        window = self._window_for_time(
            calendar=calendar,
            market_time=market_time,
            holiday=holiday,
        )

        if window is None:
            return self._outside_window_report(
                calendar=calendar,
                evaluated_at=market_time,
                holiday=holiday,
            )

        return self._window_report(
            calendar=calendar,
            window=window,
            evaluated_at=market_time,
            holiday=holiday,
        )

    def halt_market(
        self,
        *,
        market: str,
        reason: str,
        evaluated_at: datetime | None = None,
    ) -> SessionReport:
        calendar = self.calendar_for_market(
            market
        )

        normalized_reason = (
            self._normalize_identifier(
                reason,
                "reason",
            )
        )

        if calendar.market in self._halts:
            raise RuntimeError(
                "market is already halted"
            )

        self._halts[
            calendar.market
        ] = normalized_reason

        effective_time = (
            self._current_time()
            if evaluated_at is None
            else self._validate_evaluated_at(
                evaluated_at
            )
        ).astimezone(calendar.timezone)

        return self._halted_report(
            calendar=calendar,
            evaluated_at=effective_time,
            halt_reason=normalized_reason,
        )

    def resume_market(
        self,
        *,
        market: str,
        evaluated_at: datetime | None = None,
    ) -> SessionReport:
        calendar = self.calendar_for_market(
            market
        )

        if calendar.market not in self._halts:
            raise RuntimeError(
                "market is not halted"
            )

        self._halts.pop(calendar.market)

        return self.evaluate(
            market=calendar.market,
            evaluated_at=evaluated_at,
        )

    def get_session(
        self,
        *,
        market: str,
        trading_date: date,
    ) -> TradingSession:
        normalized_market = (
            self._normalize_identifier(
                market,
                "market",
            ).upper()
        )

        if not isinstance(trading_date, date):
            raise TypeError(
                "trading_date must be a date"
            )

        if isinstance(trading_date, datetime):
            raise TypeError(
                "trading_date must be a date, "
                "not a datetime"
            )

        try:
            return self._sessions[
                (
                    normalized_market,
                    trading_date,
                )
            ]
        except KeyError as exc:
            raise KeyError(
                "session not found for "
                f"{normalized_market} on {trading_date}"
            ) from exc

    def reports_for_market(
        self,
        market: str,
    ) -> tuple[SessionReport, ...]:
        normalized_market = (
            self._normalize_identifier(
                market,
                "market",
            ).upper()
        )

        return tuple(
            report
            for report in self._history
            if (
                report.session is not None
                and report.session.market
                == normalized_market
            )
        )

    def reports_for_date(
        self,
        *,
        market: str,
        trading_date: date,
    ) -> tuple[SessionReport, ...]:
        normalized_market = (
            self._normalize_identifier(
                market,
                "market",
            ).upper()
        )

        if not isinstance(trading_date, date):
            raise TypeError(
                "trading_date must be a date"
            )

        if isinstance(trading_date, datetime):
            raise TypeError(
                "trading_date must be a date, "
                "not a datetime"
            )

        return tuple(
            report
            for report in self._history
            if (
                report.session is not None
                and report.session.market
                == normalized_market
                and report.session.trading_date
                == trading_date
            )
        )

    def _window_report(
        self,
        *,
        calendar: TradingCalendar,
        window: SessionWindow,
        evaluated_at: datetime,
        holiday: TradingHoliday | None,
    ) -> SessionReport:
        effective_window = self._apply_holiday_window(
            window=window,
            holiday=holiday,
        )

        local_time = evaluated_at.timetz().replace(
            tzinfo=None
        )

        opened_at = datetime.combine(
            evaluated_at.date(),
            effective_window.opens_at,
            tzinfo=calendar.timezone,
        )

        if (
            local_time
            >= effective_window.closes_at
        ):
            closed_at = datetime.combine(
                evaluated_at.date(),
                effective_window.closes_at,
                tzinfo=calendar.timezone,
            )

            session = self._new_session(
                calendar=calendar,
                evaluated_at=evaluated_at,
                state=SessionState.CLOSED,
                session_type=(
                    effective_window.session_type
                ),
                opened_at=opened_at,
                closed_at=closed_at,
                trading_allowed=False,
                reason=(
                    "The selected trading window "
                    "has closed."
                ),
                holiday=holiday,
            )

            return self._record_report(
                session=session,
                decision=SessionDecision.REJECT,
                recommendation=(
                    "Wait for the next permitted "
                    "trading window."
                ),
            )

        if not effective_window.trading_allowed:
            session = self._new_session(
                calendar=calendar,
                evaluated_at=evaluated_at,
                state=SessionState.SCHEDULED,
                session_type=(
                    effective_window.session_type
                ),
                opened_at=None,
                closed_at=None,
                trading_allowed=False,
                reason=(
                    "This session window does not "
                    "permit trading."
                ),
                holiday=holiday,
            )

            return self._record_report(
                session=session,
                decision=SessionDecision.REJECT,
                recommendation=(
                    "Do not submit orders during "
                    "this session window."
                ),
            )

        if (
            effective_window.session_type
            is SessionType.PRE_MARKET
        ):
            state = SessionState.PRE_MARKET
            decision = (
                SessionDecision.ALLOW_LIMITED
            )
            recommendation = (
                "Use only order types permitted "
                "during pre-market trading."
            )
            reason = (
                "The pre-market trading session "
                "is active."
            )
        elif (
            effective_window.session_type
            is SessionType.AFTER_HOURS
        ):
            state = SessionState.AFTER_HOURS
            decision = (
                SessionDecision.ALLOW_LIMITED
            )
            recommendation = (
                "Use only order types permitted "
                "during after-hours trading."
            )
            reason = (
                "The after-hours trading session "
                "is active."
            )
        else:
            state = SessionState.OPEN
            decision = SessionDecision.ALLOW
            recommendation = (
                "Trading may proceed under the "
                "regular session rules."
            )
            reason = (
                "The regular trading session "
                "is open."
            )

        session = self._new_session(
            calendar=calendar,
            evaluated_at=evaluated_at,
            state=state,
            session_type=(
                effective_window.session_type
            ),
            opened_at=opened_at,
            closed_at=None,
            trading_allowed=True,
            reason=reason,
            holiday=holiday,
            metadata=(
                (
                    "allowed_order_types",
                    ",".join(
                        effective_window.order_types
                    ),
                ),
            ),
        )

        return self._record_report(
            session=session,
            decision=decision,
            recommendation=recommendation,
        )

    def _outside_window_report(
        self,
        *,
        calendar: TradingCalendar,
        evaluated_at: datetime,
        holiday: TradingHoliday | None,
    ) -> SessionReport:
        first_window = calendar.windows[0]
        final_window = calendar.windows[-1]

        local_time = evaluated_at.timetz().replace(
            tzinfo=None
        )

        if local_time < first_window.opens_at:
            state = SessionState.SCHEDULED
            decision = SessionDecision.QUEUE
            reason = (
                "The market has not reached its "
                "first trading window."
            )
            recommendation = (
                "Queue eligible orders until a "
                "permitted session opens."
            )
            opened_at = None
            closed_at = None
        else:
            state = SessionState.CLOSED
            decision = SessionDecision.REJECT
            reason = (
                "All trading windows have closed "
                "for this market day."
            )
            recommendation = (
                "Wait for the next trading day."
            )
            opened_at = datetime.combine(
                evaluated_at.date(),
                first_window.opens_at,
                tzinfo=calendar.timezone,
            )
            closed_at = datetime.combine(
                evaluated_at.date(),
                final_window.closes_at,
                tzinfo=calendar.timezone,
            )

        session = self._new_session(
            calendar=calendar,
            evaluated_at=evaluated_at,
            state=state,
            session_type=None,
            opened_at=opened_at,
            closed_at=closed_at,
            trading_allowed=False,
            reason=reason,
            holiday=holiday,
        )

        return self._record_report(
            session=session,
            decision=decision,
            recommendation=recommendation,
        )

    def _closed_report(
        self,
        *,
        calendar: TradingCalendar,
        evaluated_at: datetime,
        reason: str,
        decision: SessionDecision,
    ) -> SessionReport:
        session = self._new_session(
            calendar=calendar,
            evaluated_at=evaluated_at,
            state=SessionState.SCHEDULED,
            session_type=None,
            opened_at=None,
            closed_at=None,
            trading_allowed=False,
            reason=reason,
        )

        return self._record_report(
            session=session,
            decision=decision,
            recommendation=(
                "Do not submit trading orders."
            ),
        )

    def _holiday_closed_report(
        self,
        *,
        calendar: TradingCalendar,
        holiday: TradingHoliday,
        evaluated_at: datetime,
    ) -> SessionReport:
        session = self._new_session(
            calendar=calendar,
            evaluated_at=evaluated_at,
            state=SessionState.SCHEDULED,
            session_type=None,
            opened_at=None,
            closed_at=None,
            trading_allowed=False,
            reason=(
                f"The market is closed for "
                f"{holiday.name}."
            ),
            holiday=holiday,
        )

        return self._record_report(
            session=session,
            decision=SessionDecision.REJECT,
            recommendation=(
                "Wait until the next eligible "
                "trading day."
            ),
        )

    def _halted_report(
        self,
        *,
        calendar: TradingCalendar,
        evaluated_at: datetime,
        halt_reason: str,
    ) -> SessionReport:
        existing = self._sessions.get(
            (
                calendar.market,
                evaluated_at.date(),
            )
        )

        opened_at = (
            existing.opened_at
            if existing is not None
            else None
        )

        session_type = (
            existing.session_type
            if existing is not None
            else None
        )

        session = self._new_session(
            calendar=calendar,
            evaluated_at=evaluated_at,
            state=SessionState.HALTED,
            session_type=session_type,
            opened_at=opened_at,
            closed_at=None,
            trading_allowed=False,
            reason=(
                "Trading is temporarily halted."
            ),
            halt_reason=halt_reason,
        )

        return self._record_report(
            session=session,
            decision=(
                SessionDecision.REVIEW_REQUIRED
            ),
            recommendation=(
                "Do not submit orders until the "
                "market halt is cleared."
            ),
            warnings=(halt_reason,),
        )

    def _new_session(
        self,
        *,
        calendar: TradingCalendar,
        evaluated_at: datetime,
        state: SessionState,
        session_type: SessionType | None,
        opened_at: datetime | None,
        closed_at: datetime | None,
        trading_allowed: bool,
        reason: str,
        holiday: TradingHoliday | None = None,
        halt_reason: str | None = None,
        metadata: tuple[
            tuple[str, str],
            ...,
        ] = (),
    ) -> TradingSession:
        key = (
            calendar.market,
            evaluated_at.date(),
        )

        existing = self._sessions.get(key)

        session_id = (
            existing.session_id
            if existing is not None
            else self._next_session_id()
        )

        session = TradingSession(
            session_id=session_id,
            calendar_id=calendar.calendar_id,
            market=calendar.market,
            trading_date=evaluated_at.date(),
            state=state,
            session_type=session_type,
            opened_at=opened_at,
            closed_at=closed_at,
            evaluated_at=evaluated_at,
            trading_allowed=trading_allowed,
            reason=reason,
            holiday_id=(
                holiday.holiday_id
                if holiday is not None
                else None
            ),
            halt_reason=halt_reason,
            metadata=metadata,
        )

        self._sessions[key] = session

        return session

    def _record_report(
        self,
        *,
        session: TradingSession,
        decision: SessionDecision,
        recommendation: str,
        warnings: tuple[str, ...] = (),
    ) -> SessionReport:
        report = SessionReport(
            status=session.state,
            decision=decision,
            session=session,
            recommendation=recommendation,
            evaluated_at=session.evaluated_at,
            warnings=warnings,
        )

        self._history.append(report)

        return report

    @staticmethod
    def _calendar_is_effective(
        *,
        calendar: TradingCalendar,
        trading_date: date,
    ) -> bool:
        if (
            calendar.effective_from is not None
            and trading_date
            < calendar.effective_from
        ):
            return False

        if (
            calendar.effective_to is not None
            and trading_date
            > calendar.effective_to
        ):
            return False

        return True

    @staticmethod
    def _holiday_for_date(
        *,
        calendar: TradingCalendar,
        trading_date: date,
    ) -> TradingHoliday | None:
        for holiday in calendar.holidays:
            if holiday.holiday_date == trading_date:
                return holiday

        return None

    def _window_for_time(
        self,
        *,
        calendar: TradingCalendar,
        market_time: datetime,
        holiday: TradingHoliday | None,
    ) -> SessionWindow | None:
        local_time = market_time.timetz().replace(
            tzinfo=None
        )

        for window in calendar.windows:
            effective_window = (
                self._apply_holiday_window(
                    window=window,
                    holiday=holiday,
                )
            )

            if (
                effective_window.opens_at
                <= local_time
                < effective_window.closes_at
            ):
                return effective_window

        return None

    @staticmethod
    def _apply_holiday_window(
        *,
        window: SessionWindow,
        holiday: TradingHoliday | None,
    ) -> SessionWindow:
        if holiday is None:
            return window

        opens_at = window.opens_at
        closes_at = window.closes_at

        if (
            holiday.holiday_type
            is HolidayType.EARLY_CLOSE
            and holiday.early_close_time is not None
            and holiday.early_close_time < closes_at
        ):
            closes_at = holiday.early_close_time

        if (
            holiday.holiday_type
            is HolidayType.LATE_OPEN
            and holiday.late_open_time is not None
            and holiday.late_open_time > opens_at
        ):
            opens_at = holiday.late_open_time

        if opens_at >= closes_at:
            return SessionWindow(
                window_id=window.window_id,
                session_type=window.session_type,
                opens_at=window.opens_at,
                closes_at=window.closes_at,
                trading_allowed=False,
                order_types=(),
                metadata=window.metadata,
            )

        return SessionWindow(
            window_id=window.window_id,
            session_type=window.session_type,
            opens_at=opens_at,
            closes_at=closes_at,
            trading_allowed=window.trading_allowed,
            order_types=window.order_types,
            metadata=window.metadata,
        )

    def _next_session_id(self) -> str:
        session_id = (
            f"session-"
            f"{self._next_session_number:06d}"
        )
        self._next_session_number += 1
        return session_id

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
    def _validate_evaluated_at(
        value: datetime,
    ) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError(
                "evaluated_at must be a datetime"
            )

        if value.tzinfo is None:
            raise ValueError(
                "evaluated_at must be timezone-aware"
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

    @staticmethod
    def _system_clock() -> datetime:
        return datetime.now().astimezone()