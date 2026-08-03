from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Mapping

from .portfolio_models import (
    AssetClass,
    CashAccount,
    PortfolioDecision,
    PortfolioReport,
    PortfolioSnapshot,
    PortfolioState,
    PortfolioStatus,
    Position,
    PositionSide,
    PositionStatus,
)


Clock = Callable[[], datetime]

_ZERO = Decimal("0")


class EnterprisePortfolioEngine:
    """Maintains deterministic enterprise portfolio state."""

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

        self._states: dict[str, PortfolioState] = {}
        self._history: dict[
            str,
            list[PortfolioState],
        ] = {}
        self._reports: list[PortfolioReport] = []

        self._next_position_number = 1
        self._next_snapshot_number = 1

    @property
    def portfolio_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._states))

    @property
    def report_history(
        self,
    ) -> tuple[PortfolioReport, ...]:
        return tuple(self._reports)

    def create_portfolio(
        self,
        *,
        portfolio_id: str,
        account_id: str,
        initial_cash: Decimal,
        settled_cash: Decimal | None = None,
        margin_limit: Decimal = _ZERO,
        metadata: tuple[
            tuple[str, str],
            ...,
        ] = (),
    ) -> PortfolioReport:
        normalized_portfolio_id = self._normalize_identifier(
            portfolio_id,
            "portfolio_id",
        )
        normalized_account_id = self._normalize_identifier(
            account_id,
            "account_id",
        )

        if normalized_portfolio_id in self._states:
            raise ValueError(
                "portfolio_id is already registered"
            )

        self._require_decimal(
            initial_cash,
            "initial_cash",
        )
        self._require_decimal(
            margin_limit,
            "margin_limit",
        )

        if initial_cash < _ZERO:
            raise ValueError(
                "initial_cash must not be negative"
            )

        if margin_limit < _ZERO:
            raise ValueError(
                "margin_limit must not be negative"
            )

        effective_settled_cash = (
            initial_cash
            if settled_cash is None
            else settled_cash
        )

        self._require_decimal(
            effective_settled_cash,
            "settled_cash",
        )

        if effective_settled_cash < _ZERO:
            raise ValueError(
                "settled_cash must not be negative"
            )

        if effective_settled_cash > initial_cash:
            raise ValueError(
                "settled_cash must not exceed initial_cash"
            )

        now = self._current_time()

        cash_account = CashAccount(
            account_id=normalized_account_id,
            cash_balance=initial_cash,
            settled_cash=effective_settled_cash,
            reserved_cash=_ZERO,
            buying_power=initial_cash + margin_limit,
            margin_limit=margin_limit,
            margin_used=_ZERO,
            updated_at=now,
        )

        snapshot = self._build_snapshot(
            portfolio_id=normalized_portfolio_id,
            cash_account=cash_account,
            positions=(),
            captured_at=now,
        )

        state = PortfolioState(
            portfolio_id=normalized_portfolio_id,
            account_id=normalized_account_id,
            status=PortfolioStatus.ACTIVE,
            cash_account=cash_account,
            positions=(),
            snapshot=snapshot,
            created_at=now,
            updated_at=now,
            version=1,
            metadata=metadata,
        )

        self._store_state(state)

        return self._record_report(
            status=PortfolioStatus.ACTIVE,
            decision=PortfolioDecision.APPROVE,
            state=state,
            recommendation=(
                "Portfolio created successfully."
            ),
        )

    def get_state(
        self,
        portfolio_id: str,
    ) -> PortfolioState:
        normalized_portfolio_id = self._normalize_identifier(
            portfolio_id,
            "portfolio_id",
        )

        try:
            return self._states[
                normalized_portfolio_id
            ]
        except KeyError as exc:
            raise KeyError(
                "portfolio not found: "
                f"{normalized_portfolio_id}"
            ) from exc

    def get_position(
        self,
        portfolio_id: str,
        *,
        symbol: str,
        side: PositionSide,
    ) -> Position:
        if not isinstance(side, PositionSide):
            raise TypeError(
                "side must be a PositionSide"
            )

        normalized_symbol = self._normalize_identifier(
            symbol,
            "symbol",
        ).upper()

        state = self.get_state(portfolio_id)

        for position in state.positions:
            if (
                position.status is PositionStatus.OPEN
                and position.symbol == normalized_symbol
                and position.side is side
            ):
                return position

        raise KeyError(
            "open position not found: "
            f"{normalized_symbol}/{side.value}"
        )

    def states_for_portfolio(
        self,
        portfolio_id: str,
    ) -> tuple[PortfolioState, ...]:
        normalized_portfolio_id = self._normalize_identifier(
            portfolio_id,
            "portfolio_id",
        )

        if normalized_portfolio_id not in self._history:
            raise KeyError(
                "portfolio not found: "
                f"{normalized_portfolio_id}"
            )

        return tuple(
            self._history[normalized_portfolio_id]
        )

    def reports_for_portfolio(
        self,
        portfolio_id: str,
    ) -> tuple[PortfolioReport, ...]:
        normalized_portfolio_id = self._normalize_identifier(
            portfolio_id,
            "portfolio_id",
        )

        return tuple(
            report
            for report in self._reports
            if (
                report.state is not None
                and report.state.portfolio_id
                == normalized_portfolio_id
            )
        )

    def open_position(
        self,
        portfolio_id: str,
        *,
        symbol: str,
        asset_class: AssetClass,
        side: PositionSide,
        quantity: Decimal,
        price: Decimal,
        strategy_id: str | None = None,
        metadata: tuple[
            tuple[str, str],
            ...,
        ] = (),
    ) -> PortfolioReport:
        state = self._active_state(portfolio_id)

        normalized_symbol = self._normalize_identifier(
            symbol,
            "symbol",
        ).upper()

        if not isinstance(asset_class, AssetClass):
            raise TypeError(
                "asset_class must be an AssetClass"
            )

        if not isinstance(side, PositionSide):
            raise TypeError(
                "side must be a PositionSide"
            )

        self._validate_trade_values(
            quantity=quantity,
            price=price,
        )

        self._ensure_no_open_position(
            state=state,
            symbol=normalized_symbol,
            side=side,
        )

        trade_value = quantity * price

        if side is PositionSide.LONG:
            if trade_value > state.cash_account.buying_power:
                return self._rejected_report(
                    state=state,
                    recommendation=(
                        "Reduce the order size or add "
                        "available buying power."
                    ),
                    warning=(
                        "Insufficient buying power for "
                        "the requested long position."
                    ),
                )

            updated_cash = self._cash_after_long_purchase(
                state.cash_account,
                trade_value=trade_value,
            )
        else:
            updated_cash = self._cash_after_short_open(
                state.cash_account,
                trade_value=trade_value,
            )

        now = self._current_time()

        position = Position(
            position_id=self._next_position_id(),
            symbol=normalized_symbol,
            asset_class=asset_class,
            side=side,
            status=PositionStatus.OPEN,
            quantity=quantity,
            average_cost=price,
            market_price=price,
            market_value=trade_value,
            cost_basis=trade_value,
            realized_pnl=_ZERO,
            unrealized_pnl=_ZERO,
            opened_at=now,
            updated_at=now,
            strategy_id=strategy_id,
            metadata=metadata,
        )

        positions = state.positions + (position,)

        updated_state = self._next_state(
            state=state,
            cash_account=replace(
                updated_cash,
                updated_at=now,
            ),
            positions=positions,
            updated_at=now,
        )

        self._store_state(updated_state)

        return self._record_report(
            status=PortfolioStatus.ACTIVE,
            decision=PortfolioDecision.APPROVE,
            state=updated_state,
            recommendation=(
                f"{normalized_symbol} position opened "
                "successfully."
            ),
        )

    def add_to_position(
        self,
        portfolio_id: str,
        *,
        symbol: str,
        side: PositionSide,
        quantity: Decimal,
        price: Decimal,
    ) -> PortfolioReport:
        state = self._active_state(portfolio_id)
        position = self.get_position(
            portfolio_id,
            symbol=symbol,
            side=side,
        )

        self._validate_trade_values(
            quantity=quantity,
            price=price,
        )

        added_value = quantity * price

        if side is PositionSide.LONG:
            if added_value > state.cash_account.buying_power:
                return self._rejected_report(
                    state=state,
                    recommendation=(
                        "Reduce the order size or add "
                        "available buying power."
                    ),
                    warning=(
                        "Insufficient buying power to "
                        "increase the position."
                    ),
                )

            updated_cash = self._cash_after_long_purchase(
                state.cash_account,
                trade_value=added_value,
            )
        else:
            updated_cash = self._cash_after_short_open(
                state.cash_account,
                trade_value=added_value,
            )

        new_quantity = position.quantity + quantity
        new_cost_basis = (
            position.cost_basis + added_value
        )
        new_average_cost = (
            new_cost_basis / new_quantity
        )

        now = self._current_time()

        updated_position = replace(
            position,
            quantity=new_quantity,
            average_cost=new_average_cost,
            market_price=price,
            market_value=new_quantity * price,
            cost_basis=(
                new_quantity * new_average_cost
            ),
            unrealized_pnl=self._unrealized_pnl(
                side=side,
                quantity=new_quantity,
                average_cost=new_average_cost,
                market_price=price,
            ),
            updated_at=now,
        )

        positions = self._replace_position(
            state.positions,
            updated_position,
        )

        updated_state = self._next_state(
            state=state,
            cash_account=replace(
                updated_cash,
                updated_at=now,
            ),
            positions=positions,
            updated_at=now,
        )

        self._store_state(updated_state)

        return self._record_report(
            status=PortfolioStatus.ACTIVE,
            decision=PortfolioDecision.APPROVE,
            state=updated_state,
            recommendation=(
                f"{updated_position.symbol} position "
                "increased successfully."
            ),
        )

    def update_market_price(
        self,
        portfolio_id: str,
        *,
        symbol: str,
        side: PositionSide,
        market_price: Decimal,
    ) -> PortfolioReport:
        state = self._active_state(portfolio_id)
        position = self.get_position(
            portfolio_id,
            symbol=symbol,
            side=side,
        )

        self._require_decimal(
            market_price,
            "market_price",
        )

        if market_price <= _ZERO:
            raise ValueError(
                "market_price must be greater than zero"
            )

        now = self._current_time()

        updated_position = replace(
            position,
            market_price=market_price,
            market_value=(
                position.quantity * market_price
            ),
            unrealized_pnl=self._unrealized_pnl(
                side=position.side,
                quantity=position.quantity,
                average_cost=position.average_cost,
                market_price=market_price,
            ),
            updated_at=now,
        )

        positions = self._replace_position(
            state.positions,
            updated_position,
        )

        updated_state = self._next_state(
            state=state,
            cash_account=replace(
                state.cash_account,
                updated_at=now,
            ),
            positions=positions,
            updated_at=now,
        )

        self._store_state(updated_state)

        return self._record_report(
            status=PortfolioStatus.ACTIVE,
            decision=PortfolioDecision.NO_ACTION,
            state=updated_state,
            recommendation=(
                f"{updated_position.symbol} market price "
                "updated successfully."
            ),
        )

    def suspend_portfolio(
        self,
        portfolio_id: str,
        *,
        reason: str,
    ) -> PortfolioReport:
        state = self._active_state(portfolio_id)

        normalized_reason = self._normalize_identifier(
            reason,
            "reason",
        )

        now = self._current_time()

        updated_state = self._next_state(
            state=state,
            status=PortfolioStatus.SUSPENDED,
            cash_account=replace(
                state.cash_account,
                updated_at=now,
            ),
            positions=state.positions,
            updated_at=now,
            warnings=state.warnings
            + (
                normalized_reason,
            ),
        )

        self._store_state(updated_state)

        return self._record_report(
            status=PortfolioStatus.SUSPENDED,
            decision=PortfolioDecision.REVIEW_REQUIRED,
            state=updated_state,
            recommendation=(
                "Review the suspension reason before "
                "reactivating the portfolio."
            ),
            warnings=(normalized_reason,),
        )

    def reactivate_portfolio(
        self,
        portfolio_id: str,
    ) -> PortfolioReport:
        state = self.get_state(portfolio_id)

        if state.status is not PortfolioStatus.SUSPENDED:
            raise RuntimeError(
                "only suspended portfolios may be reactivated"
            )

        now = self._current_time()

        updated_state = self._next_state(
            state=state,
            status=PortfolioStatus.ACTIVE,
            cash_account=replace(
                state.cash_account,
                updated_at=now,
            ),
            positions=state.positions,
            updated_at=now,
        )

        self._store_state(updated_state)

        return self._record_report(
            status=PortfolioStatus.ACTIVE,
            decision=PortfolioDecision.APPROVE,
            state=updated_state,
            recommendation=(
                "Portfolio reactivated successfully."
            ),
        )

    def _next_state(
        self,
        *,
        state: PortfolioState,
        cash_account: CashAccount,
        positions: tuple[Position, ...],
        updated_at: datetime,
        status: PortfolioStatus | None = None,
        warnings: tuple[str, ...] | None = None,
    ) -> PortfolioState:
        effective_status = (
            state.status
            if status is None
            else status
        )

        snapshot = self._build_snapshot(
            portfolio_id=state.portfolio_id,
            cash_account=cash_account,
            positions=positions,
            captured_at=updated_at,
        )

        return PortfolioState(
            portfolio_id=state.portfolio_id,
            account_id=state.account_id,
            status=effective_status,
            cash_account=cash_account,
            positions=positions,
            snapshot=snapshot,
            created_at=state.created_at,
            updated_at=updated_at,
            version=state.version + 1,
            metadata=state.metadata,
            warnings=(
                state.warnings
                if warnings is None
                else warnings
            ),
        )

    def _build_snapshot(
        self,
        *,
        portfolio_id: str,
        cash_account: CashAccount,
        positions: tuple[Position, ...],
        captured_at: datetime,
    ) -> PortfolioSnapshot:
        open_positions = tuple(
            position
            for position in positions
            if position.status is PositionStatus.OPEN
        )

        long_value = sum(
            (
                position.market_value
                for position in open_positions
                if position.side is PositionSide.LONG
            ),
            _ZERO,
        )

        short_value = sum(
            (
                position.market_value
                for position in open_positions
                if position.side is PositionSide.SHORT
            ),
            _ZERO,
        )

        realized_pnl = sum(
            (
                position.realized_pnl
                for position in positions
            ),
            _ZERO,
        )

        unrealized_pnl = sum(
            (
                position.unrealized_pnl
                for position in open_positions
            ),
            _ZERO,
        )

        return PortfolioSnapshot(
            snapshot_id=self._next_snapshot_id(),
            portfolio_id=portfolio_id,
            captured_at=captured_at,
            cash_balance=cash_account.cash_balance,
            long_market_value=long_value,
            short_market_value=short_value,
            gross_exposure=long_value + short_value,
            net_exposure=long_value - short_value,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            equity=(
                cash_account.cash_balance
                + long_value
                - short_value
            ),
            position_count=len(open_positions),
        )

    @staticmethod
    def _cash_after_long_purchase(
        cash_account: CashAccount,
        *,
        trade_value: Decimal,
    ) -> CashAccount:
        available_cash = cash_account.available_cash

        cash_used = min(
            available_cash,
            trade_value,
        )
        margin_required = trade_value - cash_used

        if (
            margin_required
            > cash_account.available_margin
        ):
            raise ValueError(
                "trade requires more margin than available"
            )

        new_cash_balance = (
            cash_account.cash_balance - cash_used
        )
        new_settled_cash = max(
            _ZERO,
            cash_account.settled_cash - cash_used,
        )
        new_margin_used = (
            cash_account.margin_used
            + margin_required
        )

        return CashAccount(
            account_id=cash_account.account_id,
            cash_balance=new_cash_balance,
            settled_cash=new_settled_cash,
            reserved_cash=min(
                cash_account.reserved_cash,
                new_cash_balance,
            ),
            buying_power=(
                new_cash_balance
                - min(
                    cash_account.reserved_cash,
                    new_cash_balance,
                )
                + cash_account.margin_limit
                - new_margin_used
            ),
            margin_limit=cash_account.margin_limit,
            margin_used=new_margin_used,
            updated_at=cash_account.updated_at,
            currency=cash_account.currency,
            warnings=cash_account.warnings,
        )

    @staticmethod
    def _cash_after_short_open(
        cash_account: CashAccount,
        *,
        trade_value: Decimal,
    ) -> CashAccount:
        new_cash_balance = (
            cash_account.cash_balance + trade_value
        )

        return CashAccount(
            account_id=cash_account.account_id,
            cash_balance=new_cash_balance,
            settled_cash=cash_account.settled_cash,
            reserved_cash=cash_account.reserved_cash,
            buying_power=(
                new_cash_balance
                - cash_account.reserved_cash
                + cash_account.margin_limit
                - cash_account.margin_used
            ),
            margin_limit=cash_account.margin_limit,
            margin_used=cash_account.margin_used,
            updated_at=cash_account.updated_at,
            currency=cash_account.currency,
            warnings=cash_account.warnings,
        )

    @staticmethod
    def _unrealized_pnl(
        *,
        side: PositionSide,
        quantity: Decimal,
        average_cost: Decimal,
        market_price: Decimal,
    ) -> Decimal:
        price_difference = (
            market_price - average_cost
        )

        if side is PositionSide.LONG:
            return price_difference * quantity

        return -price_difference * quantity

    @staticmethod
    def _replace_position(
        positions: tuple[Position, ...],
        replacement: Position,
    ) -> tuple[Position, ...]:
        return tuple(
            replacement
            if position.position_id
            == replacement.position_id
            else position
            for position in positions
        )

    @staticmethod
    def _ensure_no_open_position(
        *,
        state: PortfolioState,
        symbol: str,
        side: PositionSide,
    ) -> None:
        for position in state.positions:
            if (
                position.status is PositionStatus.OPEN
                and position.symbol == symbol
                and position.side is side
            ):
                raise ValueError(
                    "an open position already exists for "
                    "the symbol and side"
                )

    def _active_state(
        self,
        portfolio_id: str,
    ) -> PortfolioState:
        state = self.get_state(portfolio_id)

        if state.status is not PortfolioStatus.ACTIVE:
            raise RuntimeError(
                "portfolio must be active"
            )

        return state

    def _store_state(
        self,
        state: PortfolioState,
    ) -> None:
        self._states[state.portfolio_id] = state
        self._history.setdefault(
            state.portfolio_id,
            [],
        ).append(state)

    def _record_report(
        self,
        *,
        status: PortfolioStatus,
        decision: PortfolioDecision,
        state: PortfolioState,
        recommendation: str,
        warnings: tuple[str, ...] = (),
    ) -> PortfolioReport:
        report = PortfolioReport(
            status=status,
            decision=decision,
            state=state,
            recommendation=recommendation,
            warnings=warnings,
        )

        self._reports.append(report)

        return report

    def _rejected_report(
        self,
        *,
        state: PortfolioState,
        recommendation: str,
        warning: str,
    ) -> PortfolioReport:
        report = PortfolioReport(
            status=state.status,
            decision=PortfolioDecision.REJECT,
            state=state,
            recommendation=recommendation,
            warnings=(warning,),
        )

        self._reports.append(report)

        return report

    def _next_position_id(self) -> str:
        value = (
            f"position-"
            f"{self._next_position_number:06d}"
        )
        self._next_position_number += 1
        return value

    def _next_snapshot_id(self) -> str:
        value = (
            f"snapshot-"
            f"{self._next_snapshot_number:06d}"
        )
        self._next_snapshot_number += 1
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
    def _validate_trade_values(
        *,
        quantity: Decimal,
        price: Decimal,
    ) -> None:
        EnterprisePortfolioEngine._require_decimal(
            quantity,
            "quantity",
        )
        EnterprisePortfolioEngine._require_decimal(
            price,
            "price",
        )

        if quantity <= _ZERO:
            raise ValueError(
                "quantity must be greater than zero"
            )

        if price <= _ZERO:
            raise ValueError(
                "price must be greater than zero"
            )

    @staticmethod
    def _require_decimal(
        value: Decimal,
        field_name: str,
    ) -> None:
        if not isinstance(value, Decimal):
            raise TypeError(
                f"{field_name} must be a Decimal"
            )

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

    def reduce_position(
        self,
        portfolio_id: str,
        *,
        symbol: str,
        side: PositionSide,
        quantity: Decimal,
        price: Decimal,
    ) -> PortfolioReport:
        state = self._active_state(portfolio_id)

        position = self.get_position(
            portfolio_id,
            symbol=symbol,
            side=side,
        )

        self._validate_trade_values(
            quantity=quantity,
            price=price,
        )

        if quantity > position.quantity:
            raise ValueError(
                "reduction quantity must not exceed "
                "the open position quantity"
            )

        now = self._current_time()
        remaining_quantity = (
            position.quantity - quantity
        )

        realized_increment = self._realized_pnl(
            side=position.side,
            quantity=quantity,
            average_cost=position.average_cost,
            execution_price=price,
        )

        updated_realized_pnl = (
            position.realized_pnl
            + realized_increment
        )

        trade_value = quantity * price

        if position.side is PositionSide.LONG:
            updated_cash = self._cash_after_long_sale(
                state.cash_account,
                trade_value=trade_value,
            )
        else:
            updated_cash = self._cash_after_short_cover(
                state.cash_account,
                trade_value=trade_value,
            )

        if remaining_quantity == _ZERO:
            updated_position = replace(
                position,
                status=PositionStatus.CLOSED,
                quantity=_ZERO,
                market_price=price,
                market_value=_ZERO,
                cost_basis=_ZERO,
                realized_pnl=updated_realized_pnl,
                unrealized_pnl=_ZERO,
                updated_at=now,
                closed_at=now,
            )

            action = "closed"
        else:
            updated_position = replace(
                position,
                quantity=remaining_quantity,
                market_price=price,
                market_value=(
                    remaining_quantity * price
                ),
                cost_basis=(
                    remaining_quantity
                    * position.average_cost
                ),
                realized_pnl=updated_realized_pnl,
                unrealized_pnl=self._unrealized_pnl(
                    side=position.side,
                    quantity=remaining_quantity,
                    average_cost=position.average_cost,
                    market_price=price,
                ),
                updated_at=now,
            )

            action = "reduced"

        positions = self._replace_position(
            state.positions,
            updated_position,
        )

        updated_state = self._next_state(
            state=state,
            cash_account=replace(
                updated_cash,
                updated_at=now,
            ),
            positions=positions,
            updated_at=now,
        )

        self._store_state(updated_state)

        return self._record_report(
            status=PortfolioStatus.ACTIVE,
            decision=PortfolioDecision.APPROVE,
            state=updated_state,
            recommendation=(
                f"{updated_position.symbol} position "
                f"{action} successfully."
            ),
        )

    def close_position(
        self,
        portfolio_id: str,
        *,
        symbol: str,
        side: PositionSide,
        price: Decimal,
    ) -> PortfolioReport:
        position = self.get_position(
            portfolio_id,
            symbol=symbol,
            side=side,
        )

        return self.reduce_position(
            portfolio_id,
            symbol=position.symbol,
            side=position.side,
            quantity=position.quantity,
            price=price,
        )

    def close_portfolio(
        self,
        portfolio_id: str,
    ) -> PortfolioReport:
        state = self._active_state(portfolio_id)

        open_positions = tuple(
            position
            for position in state.positions
            if position.status is PositionStatus.OPEN
        )

        if open_positions:
            raise RuntimeError(
                "portfolio cannot be closed while "
                "positions remain open"
            )

        now = self._current_time()

        updated_state = self._next_state(
            state=state,
            status=PortfolioStatus.CLOSED,
            cash_account=replace(
                state.cash_account,
                updated_at=now,
            ),
            positions=state.positions,
            updated_at=now,
        )

        self._store_state(updated_state)

        return self._record_report(
            status=PortfolioStatus.CLOSED,
            decision=PortfolioDecision.NO_ACTION,
            state=updated_state,
            recommendation=(
                "Portfolio closed successfully."
            ),
        )

    @staticmethod
    def _realized_pnl(
        *,
        side: PositionSide,
        quantity: Decimal,
        average_cost: Decimal,
        execution_price: Decimal,
    ) -> Decimal:
        if side is PositionSide.LONG:
            return (
                execution_price - average_cost
            ) * quantity

        return (
            average_cost - execution_price
        ) * quantity

    @staticmethod
    def _cash_after_long_sale(
        cash_account: CashAccount,
        *,
        trade_value: Decimal,
    ) -> CashAccount:
        new_cash_balance = (
            cash_account.cash_balance
            + trade_value
        )

        new_settled_cash = (
            cash_account.settled_cash
            + trade_value
        )

        return CashAccount(
            account_id=cash_account.account_id,
            cash_balance=new_cash_balance,
            settled_cash=new_settled_cash,
            reserved_cash=cash_account.reserved_cash,
            buying_power=(
                new_cash_balance
                - cash_account.reserved_cash
                + cash_account.margin_limit
                - cash_account.margin_used
            ),
            margin_limit=cash_account.margin_limit,
            margin_used=cash_account.margin_used,
            updated_at=cash_account.updated_at,
            currency=cash_account.currency,
            warnings=cash_account.warnings,
        )

    @staticmethod
    def _cash_after_short_cover(
        cash_account: CashAccount,
        *,
        trade_value: Decimal,
    ) -> CashAccount:
        if trade_value > cash_account.buying_power:
            raise ValueError(
                "insufficient buying power to cover "
                "the short position"
            )

        available_cash = (
            cash_account.available_cash
        )

        cash_used = min(
            available_cash,
            trade_value,
        )

        margin_required = (
            trade_value - cash_used
        )

        if (
            margin_required
            > cash_account.available_margin
        ):
            raise ValueError(
                "short cover requires more margin "
                "than available"
            )

        new_cash_balance = (
            cash_account.cash_balance
            - cash_used
        )

        new_settled_cash = max(
            _ZERO,
            cash_account.settled_cash
            - cash_used,
        )

        new_margin_used = (
            cash_account.margin_used
            + margin_required
        )

        effective_reserved_cash = min(
            cash_account.reserved_cash,
            new_cash_balance,
        )

        return CashAccount(
            account_id=cash_account.account_id,
            cash_balance=new_cash_balance,
            settled_cash=new_settled_cash,
            reserved_cash=effective_reserved_cash,
            buying_power=(
                new_cash_balance
                - effective_reserved_cash
                + cash_account.margin_limit
                - new_margin_used
            ),
            margin_limit=cash_account.margin_limit,
            margin_used=new_margin_used,
            updated_at=cash_account.updated_at,
            currency=cash_account.currency,
            warnings=cash_account.warnings,
        )