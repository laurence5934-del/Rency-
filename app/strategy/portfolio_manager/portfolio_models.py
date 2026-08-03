from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")


class PortfolioStatus(str, Enum):
    """Lifecycle status of an enterprise portfolio."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


class PortfolioDecision(str, Enum):
    """Decision produced by the portfolio manager."""

    APPROVE = "APPROVE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECT = "REJECT"
    NO_ACTION = "NO_ACTION"


class PositionSide(str, Enum):
    """Directional side of a portfolio position."""

    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, Enum):
    """Lifecycle status of a portfolio position."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


class AssetClass(str, Enum):
    """Supported portfolio asset classes."""

    EQUITY = "EQUITY"
    ETF = "ETF"
    OPTION = "OPTION"
    FUTURE = "FUTURE"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class Position:
    """Immutable portfolio position with reconciled valuation."""

    position_id: str
    symbol: str
    asset_class: AssetClass
    side: PositionSide
    status: PositionStatus
    quantity: Decimal
    average_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    opened_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    strategy_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_position_id = self._required_text(
            self.position_id,
            "position_id",
        )
        normalized_symbol = self._required_text(
            self.symbol,
            "symbol",
        ).upper()

        if not isinstance(self.asset_class, AssetClass):
            raise TypeError(
                "asset_class must be an AssetClass"
            )

        if not isinstance(self.side, PositionSide):
            raise TypeError(
                "side must be a PositionSide"
            )

        if not isinstance(self.status, PositionStatus):
            raise TypeError(
                "status must be a PositionStatus"
            )

        for field_name in (
            "quantity",
            "average_cost",
            "market_price",
            "market_value",
            "cost_basis",
            "realized_pnl",
            "unrealized_pnl",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.quantity < _ZERO:
            raise ValueError(
                "quantity must not be negative"
            )

        if self.average_cost < _ZERO:
            raise ValueError(
                "average_cost must not be negative"
            )

        if self.market_price < _ZERO:
            raise ValueError(
                "market_price must not be negative"
            )

        if self.market_value < _ZERO:
            raise ValueError(
                "market_value must not be negative"
            )

        if self.cost_basis < _ZERO:
            raise ValueError(
                "cost_basis must not be negative"
            )

        self._validate_datetime(
            self.opened_at,
            "opened_at",
        )
        self._validate_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.updated_at < self.opened_at:
            raise ValueError(
                "updated_at must not be earlier than opened_at"
            )

        if self.closed_at is not None:
            self._validate_datetime(
                self.closed_at,
                "closed_at",
            )

            if self.closed_at < self.opened_at:
                raise ValueError(
                    "closed_at must not be earlier than opened_at"
                )

            if self.closed_at < self.updated_at:
                raise ValueError(
                    "closed_at must not be earlier than updated_at"
                )

        if self.status is PositionStatus.OPEN:
            if self.quantity <= _ZERO:
                raise ValueError(
                    "open positions require positive quantity"
                )

            if self.average_cost <= _ZERO:
                raise ValueError(
                    "open positions require positive average_cost"
                )

            if self.market_price <= _ZERO:
                raise ValueError(
                    "open positions require positive market_price"
                )

            if self.closed_at is not None:
                raise ValueError(
                    "open positions must not include closed_at"
                )

        if self.status is PositionStatus.CLOSED:
            if self.quantity != _ZERO:
                raise ValueError(
                    "closed positions must have zero quantity"
                )

            if self.market_value != _ZERO:
                raise ValueError(
                    "closed positions must have zero market_value"
                )

            if self.cost_basis != _ZERO:
                raise ValueError(
                    "closed positions must have zero cost_basis"
                )

            if self.unrealized_pnl != _ZERO:
                raise ValueError(
                    "closed positions must have zero unrealized_pnl"
                )

            if self.closed_at is None:
                raise ValueError(
                    "closed positions must include closed_at"
                )

        expected_market_value = (
            self.quantity * self.market_price
        )

        if self.market_value != expected_market_value:
            raise ValueError(
                "market_value must equal quantity times market_price"
            )

        expected_cost_basis = (
            self.quantity * self.average_cost
        )

        if self.cost_basis != expected_cost_basis:
            raise ValueError(
                "cost_basis must equal quantity times average_cost"
            )

        expected_unrealized_pnl = (
            self._expected_unrealized_pnl()
        )

        if self.unrealized_pnl != expected_unrealized_pnl:
            raise ValueError(
                "unrealized_pnl must match position valuation"
            )

        normalized_strategy_id = self._optional_text(
            self.strategy_id,
            "strategy_id",
        )

        normalized_metadata = self._normalize_pairs(
            self.metadata,
            "metadata",
        )

        normalized_warnings = self._normalize_warnings(
            self.warnings
        )

        object.__setattr__(
            self,
            "position_id",
            normalized_position_id,
        )
        object.__setattr__(
            self,
            "symbol",
            normalized_symbol,
        )
        object.__setattr__(
            self,
            "strategy_id",
            normalized_strategy_id,
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
    def is_open(self) -> bool:
        return self.status is PositionStatus.OPEN

    @property
    def is_closed(self) -> bool:
        return self.status is PositionStatus.CLOSED

    @property
    def signed_quantity(self) -> Decimal:
        if self.side is PositionSide.LONG:
            return self.quantity

        return -self.quantity

    @property
    def signed_market_value(self) -> Decimal:
        if self.side is PositionSide.LONG:
            return self.market_value

        return -self.market_value

    def _expected_unrealized_pnl(self) -> Decimal:
        if self.status is PositionStatus.CLOSED:
            return _ZERO

        price_difference = (
            self.market_price - self.average_cost
        )

        if self.side is PositionSide.LONG:
            return price_difference * self.quantity

        return -price_difference * self.quantity

    @staticmethod
    def _required_text(
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
    def _optional_text(
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
    def _validate_datetime(
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
    def _normalize_pairs(
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
    def _normalize_warnings(
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
    
@dataclass(frozen=True, slots=True)
class CashAccount:
    """Immutable portfolio cash and buying-power state."""

    account_id: str
    cash_balance: Decimal
    settled_cash: Decimal
    reserved_cash: Decimal
    buying_power: Decimal
    margin_limit: Decimal
    margin_used: Decimal
    updated_at: datetime
    currency: str = "USD"
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_account_id = Position._required_text(
            self.account_id,
            "account_id",
        )
        normalized_currency = Position._required_text(
            self.currency,
            "currency",
        ).upper()

        for field_name in (
            "cash_balance",
            "settled_cash",
            "reserved_cash",
            "buying_power",
            "margin_limit",
            "margin_used",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

            if value < _ZERO:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        Position._validate_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.settled_cash > self.cash_balance:
            raise ValueError(
                "settled_cash must not exceed cash_balance"
            )

        if self.reserved_cash > self.cash_balance:
            raise ValueError(
                "reserved_cash must not exceed cash_balance"
            )

        if self.margin_used > self.margin_limit:
            raise ValueError(
                "margin_used must not exceed margin_limit"
            )

        expected_buying_power = (
            self.cash_balance
            - self.reserved_cash
            + self.margin_limit
            - self.margin_used
        )

        if self.buying_power != expected_buying_power:
            raise ValueError(
                "buying_power must equal cash_balance minus "
                "reserved_cash plus available margin"
            )

        normalized_warnings = Position._normalize_warnings(
            self.warnings
        )

        object.__setattr__(
            self,
            "account_id",
            normalized_account_id,
        )
        object.__setattr__(
            self,
            "currency",
            normalized_currency,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )

    @property
    def available_cash(self) -> Decimal:
        """Cash currently available for new purchases."""

        return self.cash_balance - self.reserved_cash

    @property
    def available_margin(self) -> Decimal:
        """Unused margin capacity."""

        return self.margin_limit - self.margin_used


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Immutable point-in-time portfolio valuation."""

    snapshot_id: str
    portfolio_id: str
    captured_at: datetime
    cash_balance: Decimal
    long_market_value: Decimal
    short_market_value: Decimal
    gross_exposure: Decimal
    net_exposure: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    equity: Decimal
    position_count: int
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_snapshot_id = Position._required_text(
            self.snapshot_id,
            "snapshot_id",
        )
        normalized_portfolio_id = Position._required_text(
            self.portfolio_id,
            "portfolio_id",
        )

        Position._validate_datetime(
            self.captured_at,
            "captured_at",
        )

        for field_name in (
            "cash_balance",
            "long_market_value",
            "short_market_value",
            "gross_exposure",
            "net_exposure",
            "realized_pnl",
            "unrealized_pnl",
            "equity",
        ):
            if not isinstance(
                getattr(self, field_name),
                Decimal,
            ):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        for field_name in (
            "cash_balance",
            "long_market_value",
            "short_market_value",
            "gross_exposure",
        ):
            if getattr(self, field_name) < _ZERO:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if not isinstance(self.position_count, int):
            raise TypeError(
                "position_count must be an integer"
            )

        if self.position_count < 0:
            raise ValueError(
                "position_count must not be negative"
            )

        expected_gross_exposure = (
            self.long_market_value
            + self.short_market_value
        )

        if self.gross_exposure != expected_gross_exposure:
            raise ValueError(
                "gross_exposure must equal long_market_value "
                "plus short_market_value"
            )

        expected_net_exposure = (
            self.long_market_value
            - self.short_market_value
        )

        if self.net_exposure != expected_net_exposure:
            raise ValueError(
                "net_exposure must equal long_market_value "
                "minus short_market_value"
            )

        expected_equity = (
            self.cash_balance
            + self.long_market_value
            - self.short_market_value
        )

        if self.equity != expected_equity:
            raise ValueError(
                "equity must equal cash_balance plus long "
                "market value minus short market value"
            )

        normalized_warnings = Position._normalize_warnings(
            self.warnings
        )

        object.__setattr__(
            self,
            "snapshot_id",
            normalized_snapshot_id,
        )
        object.__setattr__(
            self,
            "portfolio_id",
            normalized_portfolio_id,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )
    


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """Immutable complete state of an enterprise portfolio."""

    portfolio_id: str
    account_id: str
    status: PortfolioStatus
    cash_account: CashAccount
    positions: tuple[Position, ...]
    snapshot: PortfolioSnapshot
    created_at: datetime
    updated_at: datetime
    version: int = 1
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_portfolio_id = Position._required_text(
            self.portfolio_id,
            "portfolio_id",
        )
        normalized_account_id = Position._required_text(
            self.account_id,
            "account_id",
        )

        if not isinstance(self.status, PortfolioStatus):
            raise TypeError(
                "status must be a PortfolioStatus"
            )

        if not isinstance(
            self.cash_account,
            CashAccount,
        ):
            raise TypeError(
                "cash_account must be a CashAccount"
            )

        if not isinstance(
            self.snapshot,
            PortfolioSnapshot,
        ):
            raise TypeError(
                "snapshot must be a PortfolioSnapshot"
            )

        Position._validate_datetime(
            self.created_at,
            "created_at",
        )
        Position._validate_datetime(
            self.updated_at,
            "updated_at",
        )

        if self.updated_at < self.created_at:
            raise ValueError(
                "updated_at must not be earlier than created_at"
            )

        if not isinstance(self.version, int):
            raise TypeError(
                "version must be an integer"
            )

        if self.version < 1:
            raise ValueError(
                "version must be greater than zero"
            )

        normalized_positions = tuple(self.positions)

        for position in normalized_positions:
            if not isinstance(position, Position):
                raise TypeError(
                    "every position must be a Position"
                )

        position_ids = [
            position.position_id
            for position in normalized_positions
        ]

        if len(set(position_ids)) != len(position_ids):
            raise ValueError(
                "position_id values must be unique"
            )

        open_position_keys = [
            (
                position.symbol,
                position.side,
            )
            for position in normalized_positions
            if position.status is PositionStatus.OPEN
        ]

        if len(set(open_position_keys)) != len(
            open_position_keys
        ):
            raise ValueError(
                "open symbol and side combinations must be unique"
            )

        if (
            self.cash_account.account_id
            != normalized_account_id
        ):
            raise ValueError(
                "cash account_id must match portfolio account_id"
            )

        if (
            self.snapshot.portfolio_id
            != normalized_portfolio_id
        ):
            raise ValueError(
                "snapshot portfolio_id must match portfolio_id"
            )

        if self.snapshot.captured_at > self.updated_at:
            raise ValueError(
                "snapshot captured_at must not be later "
                "than updated_at"
            )

        open_positions = tuple(
            position
            for position in normalized_positions
            if position.status is PositionStatus.OPEN
        )

        expected_long_value = sum(
            (
                position.market_value
                for position in open_positions
                if position.side is PositionSide.LONG
            ),
            _ZERO,
        )

        expected_short_value = sum(
            (
                position.market_value
                for position in open_positions
                if position.side is PositionSide.SHORT
            ),
            _ZERO,
        )

        expected_realized_pnl = sum(
            (
                position.realized_pnl
                for position in normalized_positions
            ),
            _ZERO,
        )

        expected_unrealized_pnl = sum(
            (
                position.unrealized_pnl
                for position in open_positions
            ),
            _ZERO,
        )

        if (
            self.snapshot.cash_balance
            != self.cash_account.cash_balance
        ):
            raise ValueError(
                "snapshot cash_balance must match cash account"
            )

        if (
            self.snapshot.long_market_value
            != expected_long_value
        ):
            raise ValueError(
                "snapshot long_market_value must match positions"
            )

        if (
            self.snapshot.short_market_value
            != expected_short_value
        ):
            raise ValueError(
                "snapshot short_market_value must match positions"
            )

        if (
            self.snapshot.realized_pnl
            != expected_realized_pnl
        ):
            raise ValueError(
                "snapshot realized_pnl must match positions"
            )

        if (
            self.snapshot.unrealized_pnl
            != expected_unrealized_pnl
        ):
            raise ValueError(
                "snapshot unrealized_pnl must match positions"
            )

        if self.snapshot.position_count != len(
            open_positions
        ):
            raise ValueError(
                "snapshot position_count must match open positions"
            )

        if self.status is PortfolioStatus.CLOSED:
            if open_positions:
                raise ValueError(
                    "closed portfolios must not contain "
                    "open positions"
                )

        normalized_metadata = Position._normalize_pairs(
            self.metadata,
            "metadata",
        )
        normalized_warnings = Position._normalize_warnings(
            self.warnings
        )

        object.__setattr__(
            self,
            "portfolio_id",
            normalized_portfolio_id,
        )
        object.__setattr__(
            self,
            "account_id",
            normalized_account_id,
        )
        object.__setattr__(
            self,
            "positions",
            normalized_positions,
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
    def open_positions(self) -> tuple[Position, ...]:
        return tuple(
            position
            for position in self.positions
            if position.status is PositionStatus.OPEN
        )

    @property
    def closed_positions(self) -> tuple[Position, ...]:
        return tuple(
            position
            for position in self.positions
            if position.status is PositionStatus.CLOSED
        )


@dataclass(frozen=True, slots=True)
class PortfolioReport:
    """Unified result produced by the portfolio manager."""

    status: PortfolioStatus
    decision: PortfolioDecision
    state: PortfolioState | None
    recommendation: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, PortfolioStatus):
            raise TypeError(
                "status must be a PortfolioStatus"
            )

        if not isinstance(
            self.decision,
            PortfolioDecision,
        ):
            raise TypeError(
                "decision must be a PortfolioDecision"
            )

        if (
            self.state is not None
            and not isinstance(
                self.state,
                PortfolioState,
            )
        ):
            raise TypeError(
                "state must be a PortfolioState or None"
            )

        normalized_recommendation = (
            Position._required_text(
                self.recommendation,
                "recommendation",
            )
        )

        normalized_error = Position._optional_text(
            self.error,
            "error",
        )

        if self.status is PortfolioStatus.FAILED:
            if normalized_error is None:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error is not None:
            raise ValueError(
                "only failed reports may include an error"
            )

        if (
            self.status is not PortfolioStatus.FAILED
            and self.state is None
        ):
            raise ValueError(
                "non-failed reports must include a state"
            )

        if self.state is not None:
            if self.state.status is not self.status:
                raise ValueError(
                    "report status must match portfolio state"
                )

        normalized_warnings = Position._normalize_warnings(
            self.warnings
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