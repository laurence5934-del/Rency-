from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Callable, Iterable, Iterator, Sequence

from .audit_log import BacktestAuditLog


ZERO = Decimal("0")


class SimulationError(ValueError):
    """Raised when historical replay cannot proceed safely."""


class MarketEventType(str, Enum):
    MARKET_OPEN = "market_open"
    BAR = "bar"
    MARKET_CLOSE = "market_close"


@dataclass(frozen=True, slots=True)
class HistoricalBar:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = ZERO

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise SimulationError("historical bar symbol is required")
        if self.timestamp.tzinfo is None:
            raise SimulationError("historical bar timestamp must be timezone-aware")
        if min(self.open, self.high, self.low, self.close) <= ZERO:
            raise SimulationError("OHLC prices must be greater than zero")
        if self.high < max(self.open, self.close, self.low):
            raise SimulationError("high price is inconsistent with OHLC values")
        if self.low > min(self.open, self.close, self.high):
            raise SimulationError("low price is inconsistent with OHLC values")
        if self.volume < ZERO:
            raise SimulationError("volume cannot be negative")


@dataclass(frozen=True, slots=True)
class MarketEvent:
    sequence: int
    event_type: MarketEventType
    timestamp: datetime
    bar: HistoricalBar


MarketEventHandler = Callable[[MarketEvent], None]


class SimulationEngine:
    """Chronological, no-look-ahead replay engine for historical bars."""

    def __init__(
        self,
        bars: Iterable[HistoricalBar] = (),
        *,
        audit_log: BacktestAuditLog | None = None,
        backtest_id: str = "UNASSIGNED",
    ) -> None:
        self.audit_log = audit_log
        self.backtest_id = backtest_id
        self._bars: tuple[HistoricalBar, ...] = ()
        self._index = 0
        self._subscribers: list[MarketEventHandler] = []
        self._lock = RLock()
        self.load_history(bars)

    def load_history(self, bars: Iterable[HistoricalBar]) -> None:
        normalized = tuple(bars)
        self._validate_history(normalized)
        with self._lock:
            self._bars = normalized
            self._index = 0
        if self.audit_log is not None:
            self.audit_log.record(
                self.backtest_id,
                "SIMULATION_HISTORY_LOADED",
                bar_count=len(normalized),
            )

    def subscribe(self, handler: MarketEventHandler) -> None:
        if not callable(handler):
            raise SimulationError("simulation subscriber must be callable")
        with self._lock:
            if handler not in self._subscribers:
                self._subscribers.append(handler)

    def unsubscribe(self, handler: MarketEventHandler) -> None:
        with self._lock:
            if handler in self._subscribers:
                self._subscribers.remove(handler)

    @property
    def current_bar(self) -> HistoricalBar | None:
        with self._lock:
            if self._index == 0 or not self._bars:
                return None
            return self._bars[self._index - 1]

    @property
    def current_index(self) -> int:
        with self._lock:
            return self._index

    @property
    def total_bars(self) -> int:
        with self._lock:
            return len(self._bars)

    def visible_history(self) -> tuple[HistoricalBar, ...]:
        """Return only bars already released by the simulation clock."""
        with self._lock:
            return self._bars[: self._index]

    def is_finished(self) -> bool:
        with self._lock:
            return self._index >= len(self._bars)

    def reset(self) -> None:
        with self._lock:
            self._index = 0
        if self.audit_log is not None:
            self.audit_log.record(self.backtest_id, "SIMULATION_RESET")

    def next_event(self) -> MarketEvent | None:
        with self._lock:
            if self._index >= len(self._bars):
                return None
            bar = self._bars[self._index]
            self._index += 1
            event = MarketEvent(
                sequence=self._index,
                event_type=MarketEventType.BAR,
                timestamp=bar.timestamp,
                bar=bar,
            )
            subscribers = tuple(self._subscribers)

        for subscriber in subscribers:
            subscriber(event)
        if self.audit_log is not None:
            self.audit_log.record(
                self.backtest_id,
                "MARKET_BAR_RELEASED",
                sequence=event.sequence,
                symbol=bar.symbol,
                timestamp=bar.timestamp.isoformat(),
            )
        return event

    def run(self) -> tuple[MarketEvent, ...]:
        events: list[MarketEvent] = []
        while True:
            event = self.next_event()
            if event is None:
                break
            events.append(event)
        if self.audit_log is not None:
            self.audit_log.record(
                self.backtest_id,
                "SIMULATION_COMPLETED",
                event_count=len(events),
            )
        return tuple(events)

    def __iter__(self) -> Iterator[MarketEvent]:
        while True:
            event = self.next_event()
            if event is None:
                return
            yield event

    @staticmethod
    def _validate_history(bars: Sequence[HistoricalBar]) -> None:
        previous_key: tuple[datetime, str] | None = None
        for bar in bars:
            key = (bar.timestamp, bar.symbol.upper())
            if previous_key is not None and key < previous_key:
                raise SimulationError("historical bars must be sorted by timestamp and symbol")
            previous_key = key
