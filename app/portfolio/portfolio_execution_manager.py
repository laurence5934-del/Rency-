from __future__ import annotations

import math
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Mapping, Protocol, Sequence


class RebalanceMode(str, Enum):
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"
    CASH_ONLY = "CASH_ONLY"
    REDUCE_ONLY = "REDUCE_ONLY"


class ExecutionPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class ExecutionPlanStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ExecutionInstructionStatus(str, Enum):
    PLANNED = "PLANNED"
    SKIPPED = "SKIPPED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    symbol: str
    quantity: float
    market_price: float
    average_price: float = 0.0
    asset_class: str = "EQUITY"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")
        if self.market_price <= 0:
            raise ValueError("market_price must be positive")
        if self.average_price < 0:
            raise ValueError("average_price cannot be negative")

    @property
    def market_value(self) -> float:
        return self.quantity * self.market_price


@dataclass(frozen=True, slots=True)
class TargetAllocation:
    symbol: str
    target_weight: float
    market_price: float
    asset_class: str = "EQUITY"
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    min_trade_notional: float | None = None
    max_trade_notional: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if not 0 <= self.target_weight <= 1:
            raise ValueError("target_weight must be between 0 and 1")
        if self.market_price <= 0:
            raise ValueError("market_price must be positive")
        if self.min_trade_notional is not None and self.min_trade_notional < 0:
            raise ValueError("min_trade_notional cannot be negative")
        if self.max_trade_notional is not None and self.max_trade_notional <= 0:
            raise ValueError("max_trade_notional must be positive")


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    portfolio_id: str
    cash: float
    buying_power: float
    positions: tuple[PortfolioPosition, ...]
    timestamp_utc: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id cannot be empty")
        if self.cash < 0:
            raise ValueError("cash cannot be negative")
        if self.buying_power < 0:
            raise ValueError("buying_power cannot be negative")

    @property
    def invested_value(self) -> float:
        return sum(position.market_value for position in self.positions)

    @property
    def total_equity(self) -> float:
        return self.cash + self.invested_value

    def position_map(self) -> dict[str, PortfolioPosition]:
        return {position.symbol.upper(): position for position in self.positions}


@dataclass(frozen=True, slots=True)
class ExecutionConstraint:
    min_order_notional: float = 10.0
    max_order_notional: float | None = None
    max_symbol_weight: float = 0.35
    max_turnover_ratio: float = 1.0
    cash_reserve_ratio: float = 0.02
    allow_fractional_shares: bool = False
    allow_short_selling: bool = False
    allow_partial_rebalance: bool = True
    max_orders_per_plan: int = 100
    quantity_precision: int = 6

    def __post_init__(self) -> None:
        if self.min_order_notional < 0:
            raise ValueError("min_order_notional cannot be negative")
        if self.max_order_notional is not None and self.max_order_notional <= 0:
            raise ValueError("max_order_notional must be positive")
        if not 0 < self.max_symbol_weight <= 1:
            raise ValueError("max_symbol_weight must be between 0 and 1")
        if self.max_turnover_ratio <= 0:
            raise ValueError("max_turnover_ratio must be positive")
        if not 0 <= self.cash_reserve_ratio < 1:
            raise ValueError("cash_reserve_ratio must be between 0 and 1")
        if self.max_orders_per_plan < 1:
            raise ValueError("max_orders_per_plan must be positive")
        if self.quantity_precision < 0:
            raise ValueError("quantity_precision cannot be negative")


@dataclass(frozen=True, slots=True)
class ExecutionInstruction:
    instruction_id: str
    symbol: str
    action: TradeAction
    quantity: float
    estimated_price: float
    estimated_notional: float
    target_weight: float
    current_weight: float
    priority: ExecutionPriority
    sequence: int
    status: ExecutionInstructionStatus = ExecutionInstructionStatus.PLANNED
    reason: str | None = None
    external_order_id: str | None = None
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.instruction_id.strip():
            raise ValueError("instruction_id cannot be empty")
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")
        if self.estimated_price <= 0:
            raise ValueError("estimated_price must be positive")
        if self.estimated_notional < 0:
            raise ValueError("estimated_notional cannot be negative")
        if self.sequence < 1:
            raise ValueError("sequence must be positive")
        if self.filled_quantity < 0 or self.filled_quantity > self.quantity:
            raise ValueError("filled_quantity is outside valid range")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    plan_id: str
    portfolio_id: str
    mode: RebalanceMode
    status: ExecutionPlanStatus
    created_at_utc: str
    updated_at_utc: str
    instructions: tuple[ExecutionInstruction, ...]
    starting_equity: float
    target_cash_reserve: float
    estimated_turnover: float
    rejection_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.plan_id.strip() or not self.portfolio_id.strip():
            raise ValueError("plan_id and portfolio_id cannot be empty")
        if self.starting_equity < 0:
            raise ValueError("starting_equity cannot be negative")
        if self.target_cash_reserve < 0:
            raise ValueError("target_cash_reserve cannot be negative")
        if self.estimated_turnover < 0:
            raise ValueError("estimated_turnover cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value
        data["status"] = self.status.value
        data["instructions"] = [item.to_dict() for item in self.instructions]
        return data


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    plan_id: str
    status: ExecutionPlanStatus
    submitted_orders: int
    completed_orders: int
    failed_orders: int
    total_filled_notional: float
    started_at_utc: str
    completed_at_utc: str
    errors: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class OrderExecutor(Protocol):
    def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Any: ...


class PortfolioRiskValidator(Protocol):
    def validate_plan(
        self,
        plan: ExecutionPlan,
        snapshot: PortfolioSnapshot,
    ) -> tuple[bool, str | None]: ...


class EventPublisher(Protocol):
    def publish_event(
        self,
        event_type: str,
        payload: Any = None,
        *,
        source: str = "unknown",
        **kwargs: Any,
    ) -> Any: ...


@dataclass(slots=True)
class PortfolioExecutionManagerConfig:
    auto_execute: bool = False
    stop_on_first_failure: bool = True
    publish_events: bool = True
    net_trades: bool = True
    sell_before_buy: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.auto_execute, bool):
            raise TypeError("auto_execute must be bool")


class PortfolioExecutionManager:
    """
    Version 10.0.6 - Portfolio Execution Manager.

    Converts target portfolio allocations into validated, sequenced,
    broker-neutral execution instructions and coordinates their submission.
    """

    def __init__(
        self,
        *,
        order_executor: OrderExecutor,
        risk_validator: PortfolioRiskValidator | None = None,
        event_publisher: EventPublisher | None = None,
        config: PortfolioExecutionManagerConfig | None = None,
        constraints: ExecutionConstraint | None = None,
    ) -> None:
        self.order_executor = order_executor
        self.risk_validator = risk_validator
        self.event_publisher = event_publisher
        self.config = config or PortfolioExecutionManagerConfig()
        self.constraints = constraints or ExecutionConstraint()
        self._lock = RLock()
        self._plans: dict[str, ExecutionPlan] = {}
        self._metrics: dict[str, int | float] = {
            "plans_created": 0,
            "plans_rejected": 0,
            "plans_completed": 0,
            "plans_failed": 0,
            "orders_submitted": 0,
            "orders_failed": 0,
            "instructions_skipped": 0,
            "total_planned_notional": 0.0,
            "total_filled_notional": 0.0,
        }

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_rebalance_plan(
        self,
        *,
        snapshot: PortfolioSnapshot,
        targets: Sequence[TargetAllocation],
        mode: RebalanceMode = RebalanceMode.FULL,
        metadata: Mapping[str, Any] | None = None,
    ) -> ExecutionPlan:
        self._validate_targets(targets)
        now = self._utc_now()
        plan_id = str(uuid.uuid4())

        if snapshot.total_equity <= 0:
            plan = ExecutionPlan(
                plan_id=plan_id,
                portfolio_id=snapshot.portfolio_id,
                mode=mode,
                status=ExecutionPlanStatus.REJECTED,
                created_at_utc=now,
                updated_at_utc=now,
                instructions=(),
                starting_equity=snapshot.total_equity,
                target_cash_reserve=0.0,
                estimated_turnover=0.0,
                rejection_reason="portfolio equity must be positive",
                metadata=metadata or {},
            )
            self._store_plan(plan)
            self._metrics["plans_rejected"] += 1
            return plan

        target_cash_reserve = snapshot.total_equity * self.constraints.cash_reserve_ratio
        investable_equity = max(0.0, snapshot.total_equity - target_cash_reserve)
        current_positions = snapshot.position_map()
        target_map = {target.symbol.upper(): target for target in targets}

        symbols = set(current_positions) | set(target_map)
        provisional: list[ExecutionInstruction] = []

        for symbol in sorted(symbols):
            current = current_positions.get(symbol)
            target = target_map.get(symbol)

            current_value = current.market_value if current else 0.0
            current_weight = (
                current_value / snapshot.total_equity
                if snapshot.total_equity > 0
                else 0.0
            )
            target_weight = target.target_weight if target else 0.0
            market_price = (
                target.market_price if target else current.market_price
            )

            desired_value = investable_equity * target_weight
            delta_value = desired_value - current_value

            if mode == RebalanceMode.CASH_ONLY and delta_value < 0:
                continue
            if mode == RebalanceMode.REDUCE_ONLY and delta_value > 0:
                continue

            instruction = self._build_instruction(
                symbol=symbol,
                current_weight=current_weight,
                target_weight=target_weight,
                delta_value=delta_value,
                market_price=market_price,
                target=target,
                sequence=1,
            )
            if instruction is not None:
                provisional.append(instruction)

        if self.config.net_trades:
            provisional = self._net_instructions(provisional)

        sequenced = self._sequence_instructions(provisional)
        estimated_turnover = sum(
            item.estimated_notional for item in sequenced
        ) / snapshot.total_equity

        rejection_reason = self._validate_plan_constraints(
            snapshot=snapshot,
            instructions=sequenced,
            estimated_turnover=estimated_turnover,
        )

        status = (
            ExecutionPlanStatus.REJECTED
            if rejection_reason
            else ExecutionPlanStatus.READY
        )

        plan = ExecutionPlan(
            plan_id=plan_id,
            portfolio_id=snapshot.portfolio_id,
            mode=mode,
            status=status,
            created_at_utc=now,
            updated_at_utc=now,
            instructions=tuple(sequenced),
            starting_equity=snapshot.total_equity,
            target_cash_reserve=target_cash_reserve,
            estimated_turnover=estimated_turnover,
            rejection_reason=rejection_reason,
            metadata=metadata or {},
        )

        if status == ExecutionPlanStatus.READY and self.risk_validator is not None:
            accepted, reason = self.risk_validator.validate_plan(plan, snapshot)
            if not accepted:
                plan = self._replace_plan(
                    plan,
                    status=ExecutionPlanStatus.REJECTED,
                    rejection_reason=reason or "portfolio risk validation failed",
                )

        self._store_plan(plan)
        self._metrics["plans_created"] += 1
        self._metrics["total_planned_notional"] += sum(
            item.estimated_notional for item in plan.instructions
        )

        if plan.status == ExecutionPlanStatus.REJECTED:
            self._metrics["plans_rejected"] += 1
            self._publish("portfolio_execution.plan_rejected", plan.to_dict())
        else:
            self._publish("portfolio_execution.plan_ready", plan.to_dict())

        if self.config.auto_execute and plan.status == ExecutionPlanStatus.READY:
            self.execute_plan(plan.plan_id)

        return plan

    def execute_plan(self, plan_id: str) -> ExecutionReport:
        with self._lock:
            plan = self._require_plan(plan_id)
            if plan.status != ExecutionPlanStatus.READY:
                raise RuntimeError(
                    f"plan cannot execute from status {plan.status.value}"
                )
            plan = self._replace_plan(
                plan,
                status=ExecutionPlanStatus.EXECUTING,
            )
            self._plans[plan_id] = plan

        started_at = self._utc_now()
        errors: list[str] = []
        submitted = 0
        completed = 0
        failed = 0
        filled_notional = 0.0
        updated_instructions: list[ExecutionInstruction] = []

        for instruction in plan.instructions:
            if instruction.action == TradeAction.HOLD:
                updated_instructions.append(
                    self._replace_instruction(
                        instruction,
                        status=ExecutionInstructionStatus.SKIPPED,
                        reason=instruction.reason or "hold instruction",
                    )
                )
                self._metrics["instructions_skipped"] += 1
                continue

            try:
                response = self.order_executor.submit_order(
                    symbol=instruction.symbol,
                    side=instruction.action.value,
                    quantity=instruction.quantity,
                    client_order_id=instruction.instruction_id,
                    metadata={
                        "plan_id": plan.plan_id,
                        "portfolio_id": plan.portfolio_id,
                        **dict(instruction.metadata),
                    },
                )
                submitted += 1
                self._metrics["orders_submitted"] += 1

                external_order_id = self._extract_order_id(response)
                status, filled_quantity, average_fill_price = (
                    self._extract_execution_state(response, instruction)
                )

                if status == ExecutionInstructionStatus.FILLED:
                    completed += 1
                    filled_notional += filled_quantity * (
                        average_fill_price or instruction.estimated_price
                    )

                updated_instructions.append(
                    self._replace_instruction(
                        instruction,
                        status=status,
                        external_order_id=external_order_id,
                        filled_quantity=filled_quantity,
                        average_fill_price=average_fill_price,
                    )
                )
                self._publish(
                    "portfolio_execution.instruction_submitted",
                    updated_instructions[-1].to_dict(),
                )
            except Exception as exc:
                failed += 1
                self._metrics["orders_failed"] += 1
                message = f"{instruction.symbol}: {exc}"
                errors.append(message)
                updated_instructions.append(
                    self._replace_instruction(
                        instruction,
                        status=ExecutionInstructionStatus.FAILED,
                        reason=str(exc),
                    )
                )
                self._publish(
                    "portfolio_execution.instruction_failed",
                    updated_instructions[-1].to_dict(),
                )
                if self.config.stop_on_first_failure:
                    remaining = plan.instructions[len(updated_instructions):]
                    updated_instructions.extend(remaining)
                    break

        final_status = self._derive_plan_status(updated_instructions, failed)
        completed_at = self._utc_now()

        with self._lock:
            final_plan = self._replace_plan(
                plan,
                status=final_status,
                instructions=tuple(updated_instructions),
            )
            self._plans[plan_id] = final_plan

        self._metrics["total_filled_notional"] += filled_notional
        if final_status == ExecutionPlanStatus.COMPLETED:
            self._metrics["plans_completed"] += 1
        elif final_status == ExecutionPlanStatus.FAILED:
            self._metrics["plans_failed"] += 1

        report = ExecutionReport(
            plan_id=plan_id,
            status=final_status,
            submitted_orders=submitted,
            completed_orders=completed,
            failed_orders=failed,
            total_filled_notional=filled_notional,
            started_at_utc=started_at,
            completed_at_utc=completed_at,
            errors=tuple(errors),
        )
        self._publish("portfolio_execution.plan_finished", report.to_dict())
        return report

    def cancel_plan(self, plan_id: str, *, reason: str | None = None) -> ExecutionPlan:
        with self._lock:
            plan = self._require_plan(plan_id)
            if plan.status in {
                ExecutionPlanStatus.COMPLETED,
                ExecutionPlanStatus.CANCELLED,
                ExecutionPlanStatus.REJECTED,
                ExecutionPlanStatus.FAILED,
            }:
                raise RuntimeError(
                    f"plan cannot be cancelled from {plan.status.value}"
                )
            cancelled = self._replace_plan(
                plan,
                status=ExecutionPlanStatus.CANCELLED,
                rejection_reason=reason,
            )
            self._plans[plan_id] = cancelled
        self._publish("portfolio_execution.plan_cancelled", cancelled.to_dict())
        return cancelled

    def get_plan(self, plan_id: str) -> ExecutionPlan:
        with self._lock:
            return self._require_plan(plan_id)

    def list_plans(
        self,
        *,
        portfolio_id: str | None = None,
        status: ExecutionPlanStatus | None = None,
    ) -> tuple[ExecutionPlan, ...]:
        with self._lock:
            plans = tuple(self._plans.values())
        if portfolio_id is not None:
            plans = tuple(
                plan for plan in plans if plan.portfolio_id == portfolio_id
            )
        if status is not None:
            plans = tuple(plan for plan in plans if plan.status == status)
        return tuple(sorted(plans, key=lambda item: item.created_at_utc))

    def metrics(self) -> dict[str, int | float]:
        with self._lock:
            return dict(self._metrics)

    def health_check(self) -> dict[str, Any]:
        with self._lock:
            active = sum(
                1
                for plan in self._plans.values()
                if plan.status in {
                    ExecutionPlanStatus.READY,
                    ExecutionPlanStatus.EXECUTING,
                    ExecutionPlanStatus.PARTIALLY_EXECUTED,
                }
            )
            return {
                "healthy": True,
                "registered_plans": len(self._plans),
                "active_plans": active,
                "metrics": dict(self._metrics),
            }

    def _validate_targets(self, targets: Sequence[TargetAllocation]) -> None:
        if not targets:
            raise ValueError("targets cannot be empty")
        symbols = [target.symbol.upper() for target in targets]
        if len(symbols) != len(set(symbols)):
            raise ValueError("duplicate target symbols are not allowed")
        total_weight = sum(target.target_weight for target in targets)
        max_allowed = 1.0 - self.constraints.cash_reserve_ratio
        if total_weight > max_allowed + 1e-9:
            raise ValueError(
                f"target weights {total_weight:.6f} exceed investable limit "
                f"{max_allowed:.6f}"
            )
        for target in targets:
            if target.target_weight > self.constraints.max_symbol_weight:
                raise ValueError(
                    f"{target.symbol} target weight exceeds max_symbol_weight"
                )

    def _build_instruction(
        self,
        *,
        symbol: str,
        current_weight: float,
        target_weight: float,
        delta_value: float,
        market_price: float,
        target: TargetAllocation | None,
        sequence: int,
    ) -> ExecutionInstruction | None:
        action = TradeAction.BUY if delta_value > 0 else TradeAction.SELL
        notional = abs(delta_value)

        min_notional = self.constraints.min_order_notional
        if target and target.min_trade_notional is not None:
            min_notional = max(min_notional, target.min_trade_notional)

        max_notional = self.constraints.max_order_notional
        if target and target.max_trade_notional is not None:
            max_notional = (
                target.max_trade_notional
                if max_notional is None
                else min(max_notional, target.max_trade_notional)
            )

        if max_notional is not None:
            notional = min(notional, max_notional)

        if notional < min_notional:
            return None

        quantity = notional / market_price
        if self.constraints.allow_fractional_shares:
            quantity = round(quantity, self.constraints.quantity_precision)
        else:
            quantity = math.floor(quantity)

        if quantity <= 0:
            return None

        estimated_notional = quantity * market_price
        priority = target.priority if target else ExecutionPriority.NORMAL

        return ExecutionInstruction(
            instruction_id=str(uuid.uuid4()),
            symbol=symbol.upper(),
            action=action,
            quantity=quantity,
            estimated_price=market_price,
            estimated_notional=estimated_notional,
            target_weight=target_weight,
            current_weight=current_weight,
            priority=priority,
            sequence=sequence,
            metadata=target.metadata if target else {},
        )

    def _net_instructions(
        self,
        instructions: Sequence[ExecutionInstruction],
    ) -> list[ExecutionInstruction]:
        by_symbol: dict[str, ExecutionInstruction] = {}
        for instruction in instructions:
            existing = by_symbol.get(instruction.symbol)
            if existing is None:
                by_symbol[instruction.symbol] = instruction
                continue

            signed_existing = (
                existing.quantity
                if existing.action == TradeAction.BUY
                else -existing.quantity
            )
            signed_new = (
                instruction.quantity
                if instruction.action == TradeAction.BUY
                else -instruction.quantity
            )
            net_quantity = signed_existing + signed_new

            if abs(net_quantity) < 1e-12:
                by_symbol.pop(instruction.symbol, None)
                continue

            action = TradeAction.BUY if net_quantity > 0 else TradeAction.SELL
            quantity = abs(net_quantity)
            by_symbol[instruction.symbol] = self._replace_instruction(
                instruction,
                action=action,
                quantity=quantity,
                estimated_notional=quantity * instruction.estimated_price,
            )

        return list(by_symbol.values())

    def _sequence_instructions(
        self,
        instructions: Sequence[ExecutionInstruction],
    ) -> list[ExecutionInstruction]:
        priority_rank = {
            ExecutionPriority.CRITICAL: 0,
            ExecutionPriority.HIGH: 1,
            ExecutionPriority.NORMAL: 2,
            ExecutionPriority.LOW: 3,
        }

        def sort_key(item: ExecutionInstruction) -> tuple[int, int, float, str]:
            action_rank = (
                0
                if self.config.sell_before_buy and item.action == TradeAction.SELL
                else 1
            )
            return (
                action_rank,
                priority_rank[item.priority],
                -item.estimated_notional,
                item.symbol,
            )

        ordered = sorted(instructions, key=sort_key)
        return [
            self._replace_instruction(item, sequence=index)
            for index, item in enumerate(ordered, start=1)
        ]

    def _validate_plan_constraints(
        self,
        *,
        snapshot: PortfolioSnapshot,
        instructions: Sequence[ExecutionInstruction],
        estimated_turnover: float,
    ) -> str | None:
        if len(instructions) > self.constraints.max_orders_per_plan:
            return "plan exceeds maximum number of orders"
        if estimated_turnover > self.constraints.max_turnover_ratio:
            return "plan exceeds maximum turnover ratio"

        buy_notional = sum(
            item.estimated_notional
            for item in instructions
            if item.action == TradeAction.BUY
        )
        sell_notional = sum(
            item.estimated_notional
            for item in instructions
            if item.action == TradeAction.SELL
        )
        available = snapshot.buying_power + sell_notional

        if buy_notional > available + 1e-9:
            if not self.constraints.allow_partial_rebalance:
                return "insufficient buying power for rebalance plan"

        return None

    def _derive_plan_status(
        self,
        instructions: Sequence[ExecutionInstruction],
        failures: int,
    ) -> ExecutionPlanStatus:
        statuses = {item.status for item in instructions}
        if failures and all(
            status in {
                ExecutionInstructionStatus.FAILED,
                ExecutionInstructionStatus.PLANNED,
            }
            for status in statuses
        ):
            return ExecutionPlanStatus.FAILED
        if failures:
            return ExecutionPlanStatus.PARTIALLY_EXECUTED
        if statuses <= {
            ExecutionInstructionStatus.FILLED,
            ExecutionInstructionStatus.SKIPPED,
        }:
            return ExecutionPlanStatus.COMPLETED
        return ExecutionPlanStatus.PARTIALLY_EXECUTED

    @staticmethod
    def _extract_order_id(response: Any) -> str | None:
        if response is None:
            return None
        for name in ("broker_order_id", "order_id", "id"):
            value = getattr(response, name, None)
            if value is not None:
                return str(value)
            if isinstance(response, Mapping) and response.get(name) is not None:
                return str(response[name])
        return None

    @staticmethod
    def _extract_execution_state(
        response: Any,
        instruction: ExecutionInstruction,
    ) -> tuple[ExecutionInstructionStatus, float, float | None]:
        status_value = None
        filled_quantity = 0.0
        average_fill_price = None

        if isinstance(response, Mapping):
            status_value = response.get("status")
            filled_quantity = float(response.get("filled_quantity", 0.0) or 0.0)
            average_fill_price = response.get("average_fill_price")
        else:
            status_value = getattr(response, "status", None)
            filled_quantity = float(
                getattr(response, "filled_quantity", 0.0) or 0.0
            )
            average_fill_price = getattr(response, "average_fill_price", None)

        normalized = (
            getattr(status_value, "value", status_value) or ""
        ).upper()

        mapping = {
            "FILLED": ExecutionInstructionStatus.FILLED,
            "PARTIALLY_FILLED": ExecutionInstructionStatus.PARTIALLY_FILLED,
            "ACKNOWLEDGED": ExecutionInstructionStatus.ACKNOWLEDGED,
            "SUBMITTED": ExecutionInstructionStatus.SUBMITTED,
            "REJECTED": ExecutionInstructionStatus.REJECTED,
            "CANCELLED": ExecutionInstructionStatus.CANCELLED,
            "ERROR": ExecutionInstructionStatus.FAILED,
        }
        status = mapping.get(
            normalized,
            ExecutionInstructionStatus.SUBMITTED,
        )

        if status == ExecutionInstructionStatus.FILLED and filled_quantity == 0:
            filled_quantity = instruction.quantity
        if average_fill_price is not None:
            average_fill_price = float(average_fill_price)

        return status, filled_quantity, average_fill_price

    def _store_plan(self, plan: ExecutionPlan) -> None:
        with self._lock:
            self._plans[plan.plan_id] = plan

    def _require_plan(self, plan_id: str) -> ExecutionPlan:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise KeyError(f"unknown plan: {plan_id}")
        return plan

    def _publish(self, event_type: str, payload: Any) -> None:
        if self.config.publish_events and self.event_publisher is not None:
            self.event_publisher.publish_event(
                event_type,
                payload,
                source="portfolio_execution_manager",
            )

    @staticmethod
    def _replace_instruction(
        instruction: ExecutionInstruction,
        **changes: Any,
    ) -> ExecutionInstruction:
        values = {
            field_name: getattr(instruction, field_name)
            for field_name in instruction.__dataclass_fields__
        }
        values.update(changes)
        return ExecutionInstruction(**values)

    @staticmethod
    def _replace_plan(
        plan: ExecutionPlan,
        **changes: Any,
    ) -> ExecutionPlan:
        values = {
            field_name: getattr(plan, field_name)
            for field_name in plan.__dataclass_fields__
        }
        values["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        values.update(changes)
        return ExecutionPlan(**values)


class InMemoryOrderExecutor:
    """
    Deterministic executor for unit tests and integration tests.
    It immediately returns a filled order response.
    """

    def __init__(self, *, commission_per_order: float = 0.0) -> None:
        self.commission_per_order = commission_per_order
        self.orders: list[dict[str, Any]] = []

    def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        order = {
            "order_id": str(uuid.uuid4()),
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "filled_quantity": quantity,
            "average_fill_price": (metadata or {}).get("estimated_price"),
            "commission": self.commission_per_order,
            "status": "FILLED",
            "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
            "metadata": dict(metadata or {}),
        }
        self.orders.append(order)
        return order
