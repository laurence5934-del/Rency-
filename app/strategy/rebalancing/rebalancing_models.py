from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")
_ONE = Decimal("1")


class RebalancingStatus(str, Enum):
    """Lifecycle status of a portfolio-rebalancing workflow."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RebalancingDecision(str, Enum):
    """Final decision produced by a rebalancing workflow."""

    APPROVE = "APPROVE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECT = "REJECT"


class RebalanceSide(str, Enum):
    """Direction of a rebalance instruction."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class PortfolioAllocation:
    """Immutable current and target allocation for one symbol."""

    symbol: str
    current_value: Decimal
    current_weight: Decimal
    target_weight: Decimal
    market_price: Decimal | None = None
    asset_class: str | None = None
    sector: str | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError(
                "symbol must not be empty"
            )

        for field_name in (
            "current_value",
            "current_weight",
            "target_weight",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.current_value < _ZERO:
            raise ValueError(
                "current_value must not be negative"
            )

        for field_name in (
            "current_weight",
            "target_weight",
        ):
            value = getattr(self, field_name)

            if not _ZERO <= value <= _ONE:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.market_price is not None:
            if not isinstance(
                self.market_price,
                Decimal,
            ):
                raise TypeError(
                    "market_price must be a Decimal or None"
                )

            if self.market_price <= _ZERO:
                raise ValueError(
                    "market_price must be greater than zero"
                )

        normalized_asset_class = self._normalize_optional_text(
            self.asset_class,
            "asset_class",
        )
        normalized_sector = self._normalize_optional_text(
            self.sector,
            "sector",
        )

        object.__setattr__(
            self,
            "symbol",
            normalized_symbol,
        )
        object.__setattr__(
            self,
            "asset_class",
            normalized_asset_class,
        )
        object.__setattr__(
            self,
            "sector",
            normalized_sector,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )

    @property
    def drift(self) -> Decimal:
        """Return target weight minus current weight."""

        return self.target_weight - self.current_weight

    @property
    def absolute_drift(self) -> Decimal:
        """Return the absolute allocation drift."""

        return abs(self.drift)

    @staticmethod
    def _normalize_optional_text(
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


@dataclass(frozen=True, slots=True)
class RebalanceInstruction:
    """Immutable buy, sell, or hold instruction."""

    instruction_id: str
    symbol: str
    side: RebalanceSide
    current_weight: Decimal
    target_weight: Decimal
    drift: Decimal
    quantity: Decimal
    estimated_price: Decimal | None
    estimated_trade_value: Decimal
    priority: int = 0
    reason: str = ""
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_instruction_id = (
            self.instruction_id.strip()
        )
        normalized_symbol = self.symbol.strip().upper()
        normalized_reason = self.reason.strip()

        if not normalized_instruction_id:
            raise ValueError(
                "instruction_id must not be empty"
            )

        if not normalized_symbol:
            raise ValueError(
                "symbol must not be empty"
            )

        if not isinstance(self.side, RebalanceSide):
            raise TypeError(
                "side must be a RebalanceSide"
            )

        for field_name in (
            "current_weight",
            "target_weight",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

            if not _ZERO <= value <= _ONE:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        for field_name in (
            "drift",
            "quantity",
            "estimated_trade_value",
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

        if self.estimated_trade_value < _ZERO:
            raise ValueError(
                "estimated_trade_value must not be negative"
            )

        if self.estimated_price is not None:
            if not isinstance(
                self.estimated_price,
                Decimal,
            ):
                raise TypeError(
                    "estimated_price must be a Decimal or None"
                )

            if self.estimated_price <= _ZERO:
                raise ValueError(
                    "estimated_price must be greater than zero"
                )

        expected_drift = (
            self.target_weight - self.current_weight
        )

        if self.drift != expected_drift:
            raise ValueError(
                "drift must equal target_weight minus current_weight"
            )

        if not isinstance(self.priority, int):
            raise TypeError(
                "priority must be an integer"
            )

        if self.priority < 0:
            raise ValueError(
                "priority must not be negative"
            )

        if not normalized_reason:
            raise ValueError(
                "reason must not be empty"
            )

        if self.side is RebalanceSide.BUY:
            if self.drift <= _ZERO:
                raise ValueError(
                    "buy instructions require positive drift"
                )

            self._validate_trade_instruction()

        elif self.side is RebalanceSide.SELL:
            if self.drift >= _ZERO:
                raise ValueError(
                    "sell instructions require negative drift"
                )

            self._validate_trade_instruction()

        else:
            if self.quantity != _ZERO:
                raise ValueError(
                    "hold instructions must have zero quantity"
                )

            if self.estimated_trade_value != _ZERO:
                raise ValueError(
                    "hold instructions must have zero trade value"
                )

        object.__setattr__(
            self,
            "instruction_id",
            normalized_instruction_id,
        )
        object.__setattr__(
            self,
            "symbol",
            normalized_symbol,
        )
        object.__setattr__(
            self,
            "reason",
            normalized_reason,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )

    def _validate_trade_instruction(self) -> None:
        if self.quantity <= _ZERO:
            raise ValueError(
                "buy and sell instructions require positive quantity"
            )

        if self.estimated_price is None:
            raise ValueError(
                "buy and sell instructions require estimated_price"
            )

        if self.estimated_trade_value <= _ZERO:
            raise ValueError(
                "buy and sell instructions require positive trade value"
            )

        expected_trade_value = (
            self.quantity * self.estimated_price
        )

        if self.estimated_trade_value != expected_trade_value:
            raise ValueError(
                "estimated_trade_value must equal quantity "
                "times estimated_price"
            )


@dataclass(frozen=True, slots=True)
class RebalancePlan:
    """Immutable execution-ready portfolio rebalance plan."""

    plan_id: str
    portfolio_value: Decimal
    available_cash: Decimal
    allocations: tuple[PortfolioAllocation, ...]
    instructions: tuple[RebalanceInstruction, ...]
    total_buy_value: Decimal
    total_sell_value: Decimal
    projected_cash: Decimal
    turnover_ratio: Decimal
    drift_threshold: Decimal
    minimum_trade_value: Decimal
    maximum_turnover: Decimal
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_plan_id = self.plan_id.strip()

        if not normalized_plan_id:
            raise ValueError(
                "plan_id must not be empty"
            )

        for field_name in (
            "portfolio_value",
            "available_cash",
            "total_buy_value",
            "total_sell_value",
            "projected_cash",
            "turnover_ratio",
            "drift_threshold",
            "minimum_trade_value",
            "maximum_turnover",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if self.portfolio_value <= _ZERO:
            raise ValueError(
                "portfolio_value must be greater than zero"
            )

        for field_name in (
            "available_cash",
            "total_buy_value",
            "total_sell_value",
            "projected_cash",
            "minimum_trade_value",
        ):
            value = getattr(self, field_name)

            if value < _ZERO:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        for field_name in (
            "turnover_ratio",
            "drift_threshold",
            "maximum_turnover",
        ):
            value = getattr(self, field_name)

            if not _ZERO <= value <= _ONE:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        normalized_allocations = tuple(self.allocations)
        normalized_instructions = tuple(self.instructions)

        for allocation in normalized_allocations:
            if not isinstance(
                allocation,
                PortfolioAllocation,
            ):
                raise TypeError(
                    "every allocation must be a PortfolioAllocation"
                )

        for instruction in normalized_instructions:
            if not isinstance(
                instruction,
                RebalanceInstruction,
            ):
                raise TypeError(
                    "every instruction must be a RebalanceInstruction"
                )

        allocation_symbols = [
            allocation.symbol
            for allocation in normalized_allocations
        ]

        if len(set(allocation_symbols)) != len(
            allocation_symbols
        ):
            raise ValueError(
                "allocation symbols must be unique"
            )

        instruction_ids = [
            instruction.instruction_id
            for instruction in normalized_instructions
        ]

        if len(set(instruction_ids)) != len(
            instruction_ids
        ):
            raise ValueError(
                "instruction_id values must be unique"
            )

        instruction_symbols = [
            instruction.symbol
            for instruction in normalized_instructions
        ]

        if len(set(instruction_symbols)) != len(
            instruction_symbols
        ):
            raise ValueError(
                "instruction symbols must be unique"
            )

        known_symbols = set(allocation_symbols)

        for instruction in normalized_instructions:
            if instruction.symbol not in known_symbols:
                raise ValueError(
                    "every instruction must reference an allocation"
                )

        target_weight_total = sum(
            (
                allocation.target_weight
                for allocation in normalized_allocations
            ),
            _ZERO,
        )

        if target_weight_total != _ONE:
            raise ValueError(
                "target allocation weights must sum to 1"
            )

        expected_buy_value = sum(
            (
                instruction.estimated_trade_value
                for instruction in normalized_instructions
                if instruction.side is RebalanceSide.BUY
            ),
            _ZERO,
        )

        expected_sell_value = sum(
            (
                instruction.estimated_trade_value
                for instruction in normalized_instructions
                if instruction.side is RebalanceSide.SELL
            ),
            _ZERO,
        )

        if self.total_buy_value != expected_buy_value:
            raise ValueError(
                "total_buy_value must equal buy instruction values"
            )

        if self.total_sell_value != expected_sell_value:
            raise ValueError(
                "total_sell_value must equal sell instruction values"
            )

        expected_projected_cash = (
            self.available_cash
            + self.total_sell_value
            - self.total_buy_value
        )

        if self.projected_cash != expected_projected_cash:
            raise ValueError(
                "projected_cash must equal available_cash plus "
                "sells minus buys"
            )

        expected_turnover = (
            self.total_buy_value + self.total_sell_value
        ) / self.portfolio_value

        if self.turnover_ratio != expected_turnover:
            raise ValueError(
                "turnover_ratio must equal total trade value "
                "divided by portfolio_value"
            )

        object.__setattr__(
            self,
            "plan_id",
            normalized_plan_id,
        )
        object.__setattr__(
            self,
            "allocations",
            normalized_allocations,
        )
        object.__setattr__(
            self,
            "instructions",
            normalized_instructions,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class RebalancingReport:
    """Unified result of a portfolio-rebalancing workflow."""

    status: RebalancingStatus
    decision: RebalancingDecision
    plan: RebalancePlan | None
    recommendation: str
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            RebalancingStatus,
        ):
            raise TypeError(
                "status must be a RebalancingStatus"
            )

        if not isinstance(
            self.decision,
            RebalancingDecision,
        ):
            raise TypeError(
                "decision must be a RebalancingDecision"
            )

        if (
            self.plan is not None
            and not isinstance(
                self.plan,
                RebalancePlan,
            )
        ):
            raise TypeError(
                "plan must be a RebalancePlan or None"
            )

        normalized_recommendation = (
            self.recommendation.strip()
        )

        if not normalized_recommendation:
            raise ValueError(
                "recommendation must not be empty"
            )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is RebalancingStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        if (
            self.status is RebalancingStatus.COMPLETED
            and self.plan is None
        ):
            raise ValueError(
                "completed reports must include a plan"
            )

        if (
            self.decision is RebalancingDecision.APPROVE
            and self.plan is not None
            and self.plan.projected_cash < _ZERO
        ):
            raise ValueError(
                "approved reports must not have negative projected cash"
            )

        if (
            self.decision is RebalancingDecision.REJECT
            and self.status is RebalancingStatus.COMPLETED
            and self.plan is None
        ):
            raise ValueError(
                "completed rejected reports must include a plan"
            )

        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )
        object.__setattr__(
            self,
            "error",
            normalized_error,
        )