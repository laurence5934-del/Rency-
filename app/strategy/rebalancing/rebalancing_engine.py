from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from .rebalancing_models import (
    PortfolioAllocation,
    RebalanceInstruction,
    RebalancePlan,
    RebalanceSide,
    RebalancingDecision,
    RebalancingReport,
    RebalancingStatus,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")


class PortfolioRebalancingEngine:
    """Builds deterministic portfolio rebalance plans."""

    def build_plan(
        self,
        *,
        plan_id: str,
        portfolio_value: Decimal,
        available_cash: Decimal,
        allocations: Iterable[PortfolioAllocation],
        drift_threshold: Decimal = Decimal("0.02"),
        minimum_trade_value: Decimal = Decimal("100"),
        maximum_turnover: Decimal = Decimal("0.30"),
    ) -> RebalancingReport:
        self._validate_configuration(
            plan_id=plan_id,
            portfolio_value=portfolio_value,
            available_cash=available_cash,
            drift_threshold=drift_threshold,
            minimum_trade_value=minimum_trade_value,
            maximum_turnover=maximum_turnover,
        )

        try:
            allocation_list = tuple(allocations)
        except TypeError as exc:
            raise TypeError(
                "allocations must be iterable"
            ) from exc

        valid_allocations: list[PortfolioAllocation] = []

        try:
            for allocation in allocation_list:
                if not isinstance(
                    allocation,
                    PortfolioAllocation,
                ):
                    raise TypeError(
                        "every allocation must be a "
                        "PortfolioAllocation"
                    )

                valid_allocations.append(allocation)

            self._validate_allocations(
                allocations=valid_allocations,
                portfolio_value=portfolio_value,
            )

            desired_instructions = (
                self._build_desired_instructions(
                    allocations=valid_allocations,
                    portfolio_value=portfolio_value,
                    drift_threshold=drift_threshold,
                    minimum_trade_value=minimum_trade_value,
                )
            )

            missing_price_symbols = tuple(
                instruction.symbol
                for instruction in desired_instructions
                if (
                    instruction.side is RebalanceSide.HOLD
                    and "Market price is unavailable."
                    in instruction.warnings
                )
            )

            cash_adjusted_instructions, cash_limited_symbols = (
                self._apply_cash_constraint(
                    instructions=desired_instructions,
                    available_cash=available_cash,
                )
            )

            ordered_instructions = self._order_instructions(
                cash_adjusted_instructions
            )

            total_buy_value = sum(
                (
                    instruction.estimated_trade_value
                    for instruction in ordered_instructions
                    if instruction.side is RebalanceSide.BUY
                ),
                _ZERO,
            )

            total_sell_value = sum(
                (
                    instruction.estimated_trade_value
                    for instruction in ordered_instructions
                    if instruction.side is RebalanceSide.SELL
                ),
                _ZERO,
            )

            projected_cash = (
                available_cash
                + total_sell_value
                - total_buy_value
            )

            turnover_ratio = (
                total_buy_value + total_sell_value
            ) / portfolio_value

            warnings = self._build_warnings(
                allocations=valid_allocations,
                missing_price_symbols=missing_price_symbols,
                cash_limited_symbols=cash_limited_symbols,
                turnover_ratio=turnover_ratio,
                maximum_turnover=maximum_turnover,
            )

            plan = RebalancePlan(
                plan_id=plan_id,
                portfolio_value=portfolio_value,
                available_cash=available_cash,
                allocations=tuple(valid_allocations),
                instructions=ordered_instructions,
                total_buy_value=total_buy_value,
                total_sell_value=total_sell_value,
                projected_cash=projected_cash,
                turnover_ratio=turnover_ratio,
                drift_threshold=drift_threshold,
                minimum_trade_value=minimum_trade_value,
                maximum_turnover=maximum_turnover,
                warnings=warnings,
            )

            decision = self._decision(
                missing_price_symbols=missing_price_symbols,
                cash_limited_symbols=cash_limited_symbols,
                turnover_ratio=turnover_ratio,
                maximum_turnover=maximum_turnover,
            )

            return RebalancingReport(
                status=RebalancingStatus.COMPLETED,
                decision=decision,
                plan=plan,
                recommendation=self._recommendation(
                    decision=decision,
                    instructions=ordered_instructions,
                ),
                warnings=warnings,
            )

        except Exception as exc:
            return RebalancingReport(
                status=RebalancingStatus.FAILED,
                decision=RebalancingDecision.REJECT,
                plan=None,
                recommendation=(
                    "Correct the portfolio inputs before "
                    "attempting another rebalance."
                ),
                warnings=(
                    "Portfolio rebalancing failed.",
                ),
                error=str(exc),
            )

    @classmethod
    def _build_desired_instructions(
        cls,
        *,
        allocations: Iterable[PortfolioAllocation],
        portfolio_value: Decimal,
        drift_threshold: Decimal,
        minimum_trade_value: Decimal,
    ) -> tuple[RebalanceInstruction, ...]:
        instructions: list[RebalanceInstruction] = []

        for allocation in allocations:
            drift = allocation.drift
            absolute_drift = allocation.absolute_drift

            if absolute_drift < drift_threshold:
                instructions.append(
                    cls._hold_instruction(
                        allocation=allocation,
                        reason=(
                            "Allocation drift is below the "
                            "configured threshold."
                        ),
                    )
                )
                continue

            desired_trade_value = (
                absolute_drift * portfolio_value
            )

            if desired_trade_value < minimum_trade_value:
                instructions.append(
                    cls._hold_instruction(
                        allocation=allocation,
                        reason=(
                            "Required trade value is below the "
                            "configured minimum."
                        ),
                        warnings=(
                            "Trade was suppressed by the "
                            "minimum-trade filter.",
                        ),
                    )
                )
                continue

            if allocation.market_price is None:
                instructions.append(
                    cls._hold_instruction(
                        allocation=allocation,
                        reason=(
                            "A market price is required before "
                            "the allocation can be rebalanced."
                        ),
                        warnings=(
                            "Market price is unavailable.",
                        ),
                    )
                )
                continue

            quantity = (
                desired_trade_value
                / allocation.market_price
            )

            side = (
                RebalanceSide.BUY
                if drift > _ZERO
                else RebalanceSide.SELL
            )

            priority = (
                1
                if side is RebalanceSide.BUY
                else 0
            )

            instructions.append(
                RebalanceInstruction(
                    instruction_id=(
                        f"rebalance-{allocation.symbol.lower()}"
                    ),
                    symbol=allocation.symbol,
                    side=side,
                    current_weight=allocation.current_weight,
                    target_weight=allocation.target_weight,
                    drift=drift,
                    quantity=quantity,
                    estimated_price=allocation.market_price,
                    estimated_trade_value=desired_trade_value,
                    priority=priority,
                    reason=(
                        f"{side.value.title()} {allocation.symbol} "
                        "to move toward its target allocation."
                    ),
                    warnings=allocation.warnings,
                )
            )

        return tuple(instructions)

    @classmethod
    def _apply_cash_constraint(
        cls,
        *,
        instructions: Iterable[RebalanceInstruction],
        available_cash: Decimal,
    ) -> tuple[
        tuple[RebalanceInstruction, ...],
        tuple[str, ...],
    ]:
        instruction_list = tuple(instructions)

        sell_value = sum(
            (
                instruction.estimated_trade_value
                for instruction in instruction_list
                if instruction.side is RebalanceSide.SELL
            ),
            _ZERO,
        )

        buying_power = available_cash + sell_value
        adjusted: list[RebalanceInstruction] = []
        cash_limited_symbols: list[str] = []

        for instruction in cls._order_instructions(
            instruction_list
        ):
            if instruction.side is not RebalanceSide.BUY:
                adjusted.append(instruction)
                continue

            if (
                instruction.estimated_trade_value
                <= buying_power
            ):
                adjusted.append(instruction)
                buying_power -= (
                    instruction.estimated_trade_value
                )
                continue

            cash_limited_symbols.append(
                instruction.symbol
            )

            adjusted.append(
                RebalanceInstruction(
                    instruction_id=instruction.instruction_id,
                    symbol=instruction.symbol,
                    side=RebalanceSide.HOLD,
                    current_weight=instruction.current_weight,
                    target_weight=instruction.target_weight,
                    drift=instruction.drift,
                    quantity=_ZERO,
                    estimated_price=None,
                    estimated_trade_value=_ZERO,
                    priority=2,
                    reason=(
                        "Insufficient projected cash is available "
                        "for this buy instruction."
                    ),
                    warnings=(
                        tuple(instruction.warnings)
                        + (
                            "Buy instruction requires manual "
                            "funding review.",
                        )
                    ),
                )
            )

        return (
            tuple(adjusted),
            tuple(cash_limited_symbols),
        )

    @staticmethod
    def _hold_instruction(
        *,
        allocation: PortfolioAllocation,
        reason: str,
        warnings: tuple[str, ...] = (),
    ) -> RebalanceInstruction:
        return RebalanceInstruction(
            instruction_id=(
                f"rebalance-{allocation.symbol.lower()}"
            ),
            symbol=allocation.symbol,
            side=RebalanceSide.HOLD,
            current_weight=allocation.current_weight,
            target_weight=allocation.target_weight,
            drift=allocation.drift,
            quantity=_ZERO,
            estimated_price=None,
            estimated_trade_value=_ZERO,
            priority=2,
            reason=reason,
            warnings=(
                tuple(allocation.warnings)
                + tuple(warnings)
            ),
        )

    @staticmethod
    def _order_instructions(
        instructions: Iterable[RebalanceInstruction],
    ) -> tuple[RebalanceInstruction, ...]:
        return tuple(
            sorted(
                instructions,
                key=lambda instruction: (
                    instruction.priority,
                    instruction.symbol,
                ),
            )
        )

    @staticmethod
    def _decision(
        *,
        missing_price_symbols: tuple[str, ...],
        cash_limited_symbols: tuple[str, ...],
        turnover_ratio: Decimal,
        maximum_turnover: Decimal,
    ) -> RebalancingDecision:
        if turnover_ratio > maximum_turnover:
            return RebalancingDecision.REJECT

        if missing_price_symbols or cash_limited_symbols:
            return RebalancingDecision.REVIEW_REQUIRED

        return RebalancingDecision.APPROVE

    @staticmethod
    def _recommendation(
        *,
        decision: RebalancingDecision,
        instructions: Iterable[RebalanceInstruction],
    ) -> str:
        instruction_list = tuple(instructions)

        trade_count = sum(
            1
            for instruction in instruction_list
            if instruction.side in {
                RebalanceSide.BUY,
                RebalanceSide.SELL,
            }
        )

        if decision is RebalancingDecision.REJECT:
            return (
                "Reduce the proposed portfolio turnover before "
                "executing the rebalance."
            )

        if decision is RebalancingDecision.REVIEW_REQUIRED:
            return (
                "Resolve missing prices or cash constraints "
                "before executing the rebalance."
            )

        if trade_count == 0:
            return (
                "No meaningful portfolio drift requires "
                "rebalancing at this time."
            )

        return (
            "Execute the approved rebalance instructions "
            "in sell-before-buy order."
        )

    @staticmethod
    def _build_warnings(
        *,
        allocations: Iterable[PortfolioAllocation],
        missing_price_symbols: tuple[str, ...],
        cash_limited_symbols: tuple[str, ...],
        turnover_ratio: Decimal,
        maximum_turnover: Decimal,
    ) -> tuple[str, ...]:
        warnings = [
            warning
            for allocation in allocations
            for warning in allocation.warnings
        ]

        if missing_price_symbols:
            warnings.append(
                "Missing market prices prevent complete "
                "rebalance sizing for: "
                + ", ".join(missing_price_symbols)
                + "."
            )

        if cash_limited_symbols:
            warnings.append(
                "Available cash is insufficient for: "
                + ", ".join(cash_limited_symbols)
                + "."
            )

        if turnover_ratio > maximum_turnover:
            warnings.append(
                "Proposed turnover exceeds the configured "
                "maximum."
            )

        return tuple(warnings)

    @staticmethod
    def _validate_allocations(
        *,
        allocations: Iterable[PortfolioAllocation],
        portfolio_value: Decimal,
    ) -> None:
        allocation_list = tuple(allocations)

        if not allocation_list:
            raise ValueError(
                "allocations must not be empty"
            )

        symbols = [
            allocation.symbol
            for allocation in allocation_list
        ]

        if len(set(symbols)) != len(symbols):
            raise ValueError(
                "allocation symbols must be unique"
            )

        target_total = sum(
            (
                allocation.target_weight
                for allocation in allocation_list
            ),
            _ZERO,
        )

        if target_total != _ONE:
            raise ValueError(
                "target allocation weights must sum to 1"
            )

        current_value_total = sum(
            (
                allocation.current_value
                for allocation in allocation_list
            ),
            _ZERO,
        )

        if current_value_total > portfolio_value:
            raise ValueError(
                "allocation current values must not exceed "
                "portfolio_value"
            )

    @staticmethod
    def _validate_configuration(
        *,
        plan_id: str,
        portfolio_value: Decimal,
        available_cash: Decimal,
        drift_threshold: Decimal,
        minimum_trade_value: Decimal,
        maximum_turnover: Decimal,
    ) -> None:
        if not isinstance(plan_id, str):
            raise TypeError(
                "plan_id must be a string"
            )

        if not plan_id.strip():
            raise ValueError(
                "plan_id must not be empty"
            )

        for field_name, value in (
            ("portfolio_value", portfolio_value),
            ("available_cash", available_cash),
            ("drift_threshold", drift_threshold),
            ("minimum_trade_value", minimum_trade_value),
            ("maximum_turnover", maximum_turnover),
        ):
            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )

        if portfolio_value <= _ZERO:
            raise ValueError(
                "portfolio_value must be greater than zero"
            )

        if available_cash < _ZERO:
            raise ValueError(
                "available_cash must not be negative"
            )

        if minimum_trade_value < _ZERO:
            raise ValueError(
                "minimum_trade_value must not be negative"
            )

        for field_name, value in (
            ("drift_threshold", drift_threshold),
            ("maximum_turnover", maximum_turnover),
        ):
            if not _ZERO <= value <= _ONE:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )