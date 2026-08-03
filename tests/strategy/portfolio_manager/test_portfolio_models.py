from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.strategy.portfolio_manager.portfolio_models import (
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


NOW = datetime(
    2026,
    8,
    3,
    19,
    0,
    tzinfo=timezone.utc,
)


def long_position(
    *,
    position_id: str = "position-001",
    symbol: str = "AAPL",
    quantity: str = "10",
    average_cost: str = "100",
    market_price: str = "120",
    realized_pnl: str = "0",
) -> Position:
    quantity_value = Decimal(quantity)
    average_cost_value = Decimal(average_cost)
    market_price_value = Decimal(market_price)

    return Position(
        position_id=position_id,
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        side=PositionSide.LONG,
        status=PositionStatus.OPEN,
        quantity=quantity_value,
        average_cost=average_cost_value,
        market_price=market_price_value,
        market_value=quantity_value * market_price_value,
        cost_basis=quantity_value * average_cost_value,
        realized_pnl=Decimal(realized_pnl),
        unrealized_pnl=(
            market_price_value - average_cost_value
        ) * quantity_value,
        opened_at=NOW,
        updated_at=NOW + timedelta(minutes=1),
        strategy_id="momentum-001",
    )


def short_position(
    *,
    position_id: str = "position-002",
    symbol: str = "TSLA",
    quantity: str = "5",
    average_cost: str = "200",
    market_price: str = "180",
    realized_pnl: str = "0",
) -> Position:
    quantity_value = Decimal(quantity)
    average_cost_value = Decimal(average_cost)
    market_price_value = Decimal(market_price)

    return Position(
        position_id=position_id,
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        side=PositionSide.SHORT,
        status=PositionStatus.OPEN,
        quantity=quantity_value,
        average_cost=average_cost_value,
        market_price=market_price_value,
        market_value=quantity_value * market_price_value,
        cost_basis=quantity_value * average_cost_value,
        realized_pnl=Decimal(realized_pnl),
        unrealized_pnl=(
            average_cost_value - market_price_value
        ) * quantity_value,
        opened_at=NOW,
        updated_at=NOW + timedelta(minutes=1),
    )


def closed_position() -> Position:
    return Position(
        position_id="position-closed-001",
        symbol="MSFT",
        asset_class=AssetClass.EQUITY,
        side=PositionSide.LONG,
        status=PositionStatus.CLOSED,
        quantity=Decimal("0"),
        average_cost=Decimal("100"),
        market_price=Decimal("110"),
        market_value=Decimal("0"),
        cost_basis=Decimal("0"),
        realized_pnl=Decimal("100"),
        unrealized_pnl=Decimal("0"),
        opened_at=NOW,
        updated_at=NOW + timedelta(minutes=1),
        closed_at=NOW + timedelta(minutes=2),
    )


def cash_account() -> CashAccount:
    return CashAccount(
        account_id="account-001",
        cash_balance=Decimal("10000"),
        settled_cash=Decimal("9000"),
        reserved_cash=Decimal("1000"),
        buying_power=Decimal("14000"),
        margin_limit=Decimal("6000"),
        margin_used=Decimal("1000"),
        updated_at=NOW + timedelta(minutes=2),
    )


def portfolio_snapshot(
    *,
    positions: tuple[Position, ...] | None = None,
    cash: CashAccount | None = None,
) -> PortfolioSnapshot:
    position_values = (
        positions
        if positions is not None
        else (
            long_position(),
            short_position(),
            closed_position(),
        )
    )

    cash_value = (
        cash
        if cash is not None
        else cash_account()
    )

    open_positions = tuple(
        position
        for position in position_values
        if position.status is PositionStatus.OPEN
    )

    long_value = sum(
        (
            position.market_value
            for position in open_positions
            if position.side is PositionSide.LONG
        ),
        Decimal("0"),
    )

    short_value = sum(
        (
            position.market_value
            for position in open_positions
            if position.side is PositionSide.SHORT
        ),
        Decimal("0"),
    )

    realized_pnl = sum(
        (
            position.realized_pnl
            for position in position_values
        ),
        Decimal("0"),
    )

    unrealized_pnl = sum(
        (
            position.unrealized_pnl
            for position in open_positions
        ),
        Decimal("0"),
    )

    return PortfolioSnapshot(
        snapshot_id="snapshot-001",
        portfolio_id="portfolio-001",
        captured_at=NOW + timedelta(minutes=2),
        cash_balance=cash_value.cash_balance,
        long_market_value=long_value,
        short_market_value=short_value,
        gross_exposure=long_value + short_value,
        net_exposure=long_value - short_value,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        equity=(
            cash_value.cash_balance
            + long_value
            - short_value
        ),
        position_count=len(open_positions),
    )


def portfolio_state() -> PortfolioState:
    positions = (
        long_position(),
        short_position(),
        closed_position(),
    )
    cash = cash_account()

    return PortfolioState(
        portfolio_id="portfolio-001",
        account_id="account-001",
        status=PortfolioStatus.ACTIVE,
        cash_account=cash,
        positions=positions,
        snapshot=portfolio_snapshot(
            positions=positions,
            cash=cash,
        ),
        created_at=NOW,
        updated_at=NOW + timedelta(minutes=3),
        version=1,
    )


def test_long_position() -> None:
    value = long_position()

    assert value.symbol == "AAPL"
    assert value.side is PositionSide.LONG
    assert value.market_value == Decimal("1200")
    assert value.cost_basis == Decimal("1000")
    assert value.unrealized_pnl == Decimal("200")


def test_short_position() -> None:
    value = short_position()

    assert value.side is PositionSide.SHORT
    assert value.market_value == Decimal("900")
    assert value.cost_basis == Decimal("1000")
    assert value.unrealized_pnl == Decimal("100")


def test_position_text_is_normalized() -> None:
    value = long_position(
        position_id="  position-001  ",
        symbol="  aapl  ",
    )

    assert value.position_id == "position-001"
    assert value.symbol == "AAPL"
    assert value.strategy_id == "momentum-001"


def test_position_properties() -> None:
    long_value = long_position()
    short_value = short_position()

    assert long_value.is_open is True
    assert long_value.is_closed is False
    assert long_value.signed_quantity == Decimal("10")
    assert long_value.signed_market_value == Decimal("1200")

    assert short_value.signed_quantity == Decimal("-5")
    assert short_value.signed_market_value == Decimal("-900")


@pytest.mark.parametrize(
    "field_name",
    [
        "position_id",
        "symbol",
    ],
)
def test_position_required_text_must_not_be_empty(
    field_name: str,
) -> None:
    arguments = {
        "position_id": "position-001",
        "symbol": "AAPL",
        "asset_class": AssetClass.EQUITY,
        "side": PositionSide.LONG,
        "status": PositionStatus.OPEN,
        "quantity": Decimal("10"),
        "average_cost": Decimal("100"),
        "market_price": Decimal("120"),
        "market_value": Decimal("1200"),
        "cost_basis": Decimal("1000"),
        "realized_pnl": Decimal("0"),
        "unrealized_pnl": Decimal("200"),
        "opened_at": NOW,
        "updated_at": NOW,
    }
    arguments[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be empty",
    ):
        Position(**arguments)


@pytest.mark.parametrize(
    "field_name",
    [
        "quantity",
        "average_cost",
        "market_price",
        "market_value",
        "cost_basis",
        "realized_pnl",
        "unrealized_pnl",
    ],
)
def test_position_financial_fields_require_decimal(
    field_name: str,
) -> None:
    arguments = {
        "position_id": "position-001",
        "symbol": "AAPL",
        "asset_class": AssetClass.EQUITY,
        "side": PositionSide.LONG,
        "status": PositionStatus.OPEN,
        "quantity": Decimal("10"),
        "average_cost": Decimal("100"),
        "market_price": Decimal("120"),
        "market_value": Decimal("1200"),
        "cost_basis": Decimal("1000"),
        "realized_pnl": Decimal("0"),
        "unrealized_pnl": Decimal("200"),
        "opened_at": NOW,
        "updated_at": NOW,
    }
    arguments[field_name] = 1

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a Decimal",
    ):
        Position(**arguments)


def test_open_position_requires_positive_quantity() -> None:
    with pytest.raises(
        ValueError,
        match="open positions require positive quantity",
    ):
        Position(
            position_id="position-001",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            quantity=Decimal("0"),
            average_cost=Decimal("100"),
            market_price=Decimal("120"),
            market_value=Decimal("0"),
            cost_basis=Decimal("0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            opened_at=NOW,
            updated_at=NOW,
        )


def test_market_value_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "market_value must equal quantity "
            "times market_price"
        ),
    ):
        Position(
            position_id="position-001",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            market_price=Decimal("120"),
            market_value=Decimal("1199"),
            cost_basis=Decimal("1000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("200"),
            opened_at=NOW,
            updated_at=NOW,
        )


def test_cost_basis_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cost_basis must equal quantity "
            "times average_cost"
        ),
    ):
        Position(
            position_id="position-001",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            market_price=Decimal("120"),
            market_value=Decimal("1200"),
            cost_basis=Decimal("999"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("200"),
            opened_at=NOW,
            updated_at=NOW,
        )


def test_long_unrealized_pnl_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unrealized_pnl must match position valuation"
        ),
    ):
        Position(
            position_id="position-001",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            market_price=Decimal("120"),
            market_value=Decimal("1200"),
            cost_basis=Decimal("1000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("199"),
            opened_at=NOW,
            updated_at=NOW,
        )


def test_short_unrealized_pnl_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unrealized_pnl must match position valuation"
        ),
    ):
        Position(
            position_id="position-002",
            symbol="TSLA",
            asset_class=AssetClass.EQUITY,
            side=PositionSide.SHORT,
            status=PositionStatus.OPEN,
            quantity=Decimal("5"),
            average_cost=Decimal("200"),
            market_price=Decimal("180"),
            market_value=Decimal("900"),
            cost_basis=Decimal("1000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("-100"),
            opened_at=NOW,
            updated_at=NOW,
        )


def test_closed_position() -> None:
    value = closed_position()

    assert value.is_closed is True
    assert value.quantity == Decimal("0")
    assert value.realized_pnl == Decimal("100")
    assert value.closed_at is not None


def test_closed_position_requires_closed_at() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "closed positions must include closed_at"
        ),
    ):
        Position(
            position_id="position-001",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            side=PositionSide.LONG,
            status=PositionStatus.CLOSED,
            quantity=Decimal("0"),
            average_cost=Decimal("100"),
            market_price=Decimal("120"),
            market_value=Decimal("0"),
            cost_basis=Decimal("0"),
            realized_pnl=Decimal("200"),
            unrealized_pnl=Decimal("0"),
            opened_at=NOW,
            updated_at=NOW,
            closed_at=None,
        )


def test_position_timestamps_must_be_ordered() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "updated_at must not be earlier than opened_at"
        ),
    ):
        Position(
            position_id="position-001",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            side=PositionSide.LONG,
            status=PositionStatus.OPEN,
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            market_price=Decimal("120"),
            market_value=Decimal("1200"),
            cost_basis=Decimal("1000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("200"),
            opened_at=NOW,
            updated_at=NOW - timedelta(seconds=1),
        )


def test_position_metadata_is_normalized() -> None:
    value = Position(
        position_id="position-001",
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        side=PositionSide.LONG,
        status=PositionStatus.OPEN,
        quantity=Decimal("10"),
        average_cost=Decimal("100"),
        market_price=Decimal("120"),
        market_value=Decimal("1200"),
        cost_basis=Decimal("1000"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("200"),
        opened_at=NOW,
        updated_at=NOW,
        metadata=[
            ("  source  ", "  broker  "),
        ],
        warnings=["  Position warning.  "],
    )

    assert value.metadata == (("source", "broker"),)
    assert value.warnings == ("Position warning.",)


def test_cash_account() -> None:
    value = cash_account()

    assert value.available_cash == Decimal("9000")
    assert value.available_margin == Decimal("5000")
    assert value.buying_power == Decimal("14000")


def test_cash_account_currency_is_normalized() -> None:
    value = CashAccount(
        account_id="  account-001  ",
        cash_balance=Decimal("1000"),
        settled_cash=Decimal("1000"),
        reserved_cash=Decimal("0"),
        buying_power=Decimal("1000"),
        margin_limit=Decimal("0"),
        margin_used=Decimal("0"),
        updated_at=NOW,
        currency="  usd  ",
    )

    assert value.account_id == "account-001"
    assert value.currency == "USD"

def test_settled_cash_cannot_exceed_balance() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "settled_cash must not exceed cash_balance"
        ),
    ):
        CashAccount(
            account_id="account-001",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1001"),
            reserved_cash=Decimal("0"),
            buying_power=Decimal("1000"),
            margin_limit=Decimal("0"),
            margin_used=Decimal("0"),
            updated_at=NOW,
        )


def test_reserved_cash_cannot_exceed_balance() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "reserved_cash must not exceed cash_balance"
        ),
    ):
        CashAccount(
            account_id="account-001",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1000"),
            reserved_cash=Decimal("1001"),
            buying_power=Decimal("0"),
            margin_limit=Decimal("0"),
            margin_used=Decimal("0"),
            updated_at=NOW,
        )


def test_margin_used_cannot_exceed_limit() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "margin_used must not exceed margin_limit"
        ),
    ):
        CashAccount(
            account_id="account-001",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1000"),
            reserved_cash=Decimal("0"),
            buying_power=Decimal("1000"),
            margin_limit=Decimal("500"),
            margin_used=Decimal("501"),
            updated_at=NOW,
        )


def test_buying_power_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match="buying_power must equal",
    ):
        CashAccount(
            account_id="account-001",
            cash_balance=Decimal("1000"),
            settled_cash=Decimal("1000"),
            reserved_cash=Decimal("100"),
            buying_power=Decimal("999"),
            margin_limit=Decimal("500"),
            margin_used=Decimal("100"),
            updated_at=NOW,
        )


def test_portfolio_snapshot() -> None:
    value = portfolio_snapshot()

    assert value.long_market_value == Decimal("1200")
    assert value.short_market_value == Decimal("900")
    assert value.gross_exposure == Decimal("2100")
    assert value.net_exposure == Decimal("300")
    assert value.equity == Decimal("10300")
    assert value.position_count == 2


def test_snapshot_gross_exposure_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match="gross_exposure must equal",
    ):
        PortfolioSnapshot(
            snapshot_id="snapshot-001",
            portfolio_id="portfolio-001",
            captured_at=NOW,
            cash_balance=Decimal("10000"),
            long_market_value=Decimal("1200"),
            short_market_value=Decimal("900"),
            gross_exposure=Decimal("2000"),
            net_exposure=Decimal("300"),
            realized_pnl=Decimal("100"),
            unrealized_pnl=Decimal("300"),
            equity=Decimal("10300"),
            position_count=2,
        )


def test_snapshot_net_exposure_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match="net_exposure must equal",
    ):
        PortfolioSnapshot(
            snapshot_id="snapshot-001",
            portfolio_id="portfolio-001",
            captured_at=NOW,
            cash_balance=Decimal("10000"),
            long_market_value=Decimal("1200"),
            short_market_value=Decimal("900"),
            gross_exposure=Decimal("2100"),
            net_exposure=Decimal("301"),
            realized_pnl=Decimal("100"),
            unrealized_pnl=Decimal("300"),
            equity=Decimal("10300"),
            position_count=2,
        )


def test_snapshot_equity_must_reconcile() -> None:
    with pytest.raises(
        ValueError,
        match="equity must equal",
    ):
        PortfolioSnapshot(
            snapshot_id="snapshot-001",
            portfolio_id="portfolio-001",
            captured_at=NOW,
            cash_balance=Decimal("10000"),
            long_market_value=Decimal("1200"),
            short_market_value=Decimal("900"),
            gross_exposure=Decimal("2100"),
            net_exposure=Decimal("300"),
            realized_pnl=Decimal("100"),
            unrealized_pnl=Decimal("300"),
            equity=Decimal("10299"),
            position_count=2,
        )


def test_portfolio_state() -> None:
    value = portfolio_state()

    assert value.status is PortfolioStatus.ACTIVE
    assert len(value.positions) == 3
    assert len(value.open_positions) == 2
    assert len(value.closed_positions) == 1


def test_position_ids_must_be_unique() -> None:
    duplicate = long_position()

    with pytest.raises(
        ValueError,
        match="position_id values must be unique",
    ):
        PortfolioState(
            portfolio_id="portfolio-001",
            account_id="account-001",
            status=PortfolioStatus.ACTIVE,
            cash_account=cash_account(),
            positions=(duplicate, duplicate),
            snapshot=portfolio_snapshot(
                positions=(duplicate, duplicate),
            ),
            created_at=NOW,
            updated_at=NOW + timedelta(minutes=3),
        )


def test_open_symbol_and_side_must_be_unique() -> None:
    first = long_position(
        position_id="position-001",
    )
    second = long_position(
        position_id="position-002",
    )

    with pytest.raises(
        ValueError,
        match=(
            "open symbol and side combinations "
            "must be unique"
        ),
    ):
        PortfolioState(
            portfolio_id="portfolio-001",
            account_id="account-001",
            status=PortfolioStatus.ACTIVE,
            cash_account=cash_account(),
            positions=(first, second),
            snapshot=portfolio_snapshot(
                positions=(first, second),
            ),
            created_at=NOW,
            updated_at=NOW + timedelta(minutes=3),
        )


def test_cash_account_id_must_match_state() -> None:
    cash = CashAccount(
        account_id="different-account",
        cash_balance=Decimal("10000"),
        settled_cash=Decimal("9000"),
        reserved_cash=Decimal("1000"),
        buying_power=Decimal("14000"),
        margin_limit=Decimal("6000"),
        margin_used=Decimal("1000"),
        updated_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match=(
            "cash account_id must match "
            "portfolio account_id"
        ),
    ):
        PortfolioState(
            portfolio_id="portfolio-001",
            account_id="account-001",
            status=PortfolioStatus.ACTIVE,
            cash_account=cash,
            positions=(),
            snapshot=portfolio_snapshot(
                positions=(),
                cash=cash,
            ),
            created_at=NOW,
            updated_at=NOW + timedelta(minutes=3),
        )


def test_snapshot_position_count_must_match() -> None:
    positions = (long_position(),)
    cash = cash_account()

    bad_snapshot = PortfolioSnapshot(
        snapshot_id="snapshot-001",
        portfolio_id="portfolio-001",
        captured_at=NOW,
        cash_balance=cash.cash_balance,
        long_market_value=Decimal("1200"),
        short_market_value=Decimal("0"),
        gross_exposure=Decimal("1200"),
        net_exposure=Decimal("1200"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("200"),
        equity=Decimal("11200"),
        position_count=0,
    )

    with pytest.raises(
        ValueError,
        match=(
            "snapshot position_count must match "
            "open positions"
        ),
    ):
        PortfolioState(
            portfolio_id="portfolio-001",
            account_id="account-001",
            status=PortfolioStatus.ACTIVE,
            cash_account=cash,
            positions=positions,
            snapshot=bad_snapshot,
            created_at=NOW,
            updated_at=NOW + timedelta(minutes=3),
        )


def test_closed_portfolio_rejects_open_positions() -> None:
    positions = (long_position(),)
    cash = cash_account()

    with pytest.raises(
        ValueError,
        match=(
            "closed portfolios must not contain "
            "open positions"
        ),
    ):
        PortfolioState(
            portfolio_id="portfolio-001",
            account_id="account-001",
            status=PortfolioStatus.CLOSED,
            cash_account=cash,
            positions=positions,
            snapshot=portfolio_snapshot(
                positions=positions,
                cash=cash,
            ),
            created_at=NOW,
            updated_at=NOW + timedelta(minutes=3),
        )


def test_portfolio_report() -> None:
    state = portfolio_state()

    report = PortfolioReport(
        status=PortfolioStatus.ACTIVE,
        decision=PortfolioDecision.APPROVE,
        state=state,
        recommendation="Portfolio state is valid.",
    )

    assert report.state == state
    assert report.error is None


def test_failed_report_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed reports must include an error",
    ):
        PortfolioReport(
            status=PortfolioStatus.FAILED,
            decision=PortfolioDecision.REJECT,
            state=None,
            recommendation="Portfolio validation failed.",
        )


def test_non_failed_report_requires_state() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "non-failed reports must include a state"
        ),
    ):
        PortfolioReport(
            status=PortfolioStatus.ACTIVE,
            decision=PortfolioDecision.APPROVE,
            state=None,
            recommendation="Portfolio is active.",
        )


def test_report_status_must_match_state() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "report status must match portfolio state"
        ),
    ):
        PortfolioReport(
            status=PortfolioStatus.SUSPENDED,
            decision=PortfolioDecision.REVIEW_REQUIRED,
            state=portfolio_state(),
            recommendation="Review portfolio.",
        )


def test_models_are_immutable() -> None:
    value = long_position()

    with pytest.raises(FrozenInstanceError):
        value.quantity = Decimal("20")