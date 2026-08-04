from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Callable

from app.strategy.order_manager import OrderSide

from .risk_models import (
    RiskDecision,
    RiskEvaluationRequest,
    RiskEvaluationResult,
    RiskEvaluationStatus,
    RiskGatewayReport,
    RiskPolicy,
    RiskRuleType,
    RiskSeverity,
    RiskViolation,
)


Clock = Callable[[], datetime]

_ZERO = Decimal("0")
_ONE = Decimal("1")


class EnterpriseRiskGateway:
    """Evaluates orders against an immutable pre-trade risk policy."""

    def __init__(
        self,
        *,
        policy: RiskPolicy,
        clock: Clock | None = None,
    ) -> None:
        if not isinstance(policy, RiskPolicy):
            raise TypeError(
                "policy must be a RiskPolicy"
            )

        if clock is not None and not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._policy = policy
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._results: dict[
            str,
            RiskEvaluationResult,
        ] = {}

        self._reports: dict[
            str,
            RiskGatewayReport,
        ] = {}

        self._report_history: list[
            RiskGatewayReport
        ] = []

        self._order_evaluations: dict[
            str,
            list[str],
        ] = {}

        self._kill_switch_active = False
        self._kill_switch_reason: str | None = None

        self._next_violation_number = 1
        self._next_report_number = 1

    @property
    def policy(self) -> RiskPolicy:
        return self._policy

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch_active

    @property
    def kill_switch_reason(self) -> str | None:
        return self._kill_switch_reason

    @property
    def evaluation_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._results)
        )

    @property
    def report_history(
        self,
    ) -> tuple[RiskGatewayReport, ...]:
        return tuple(self._report_history)

    def replace_policy(
        self,
        policy: RiskPolicy,
    ) -> RiskPolicy:
        if not isinstance(policy, RiskPolicy):
            raise TypeError(
                "policy must be a RiskPolicy"
            )

        self._policy = policy
        return policy

    def activate_kill_switch(
        self,
        *,
        reason: str,
    ) -> None:
        normalized_reason = self._normalize_identifier(
            reason,
            "reason",
        )

        if self._kill_switch_active:
            raise RuntimeError(
                "kill switch is already active"
            )

        self._kill_switch_active = True
        self._kill_switch_reason = normalized_reason

    def deactivate_kill_switch(self) -> None:
        if not self._kill_switch_active:
            raise RuntimeError(
                "kill switch is not active"
            )

        self._kill_switch_active = False
        self._kill_switch_reason = None

    def evaluate(
        self,
        request: RiskEvaluationRequest,
    ) -> RiskGatewayReport:
        if not isinstance(
            request,
            RiskEvaluationRequest,
        ):
            raise TypeError(
                "request must be a RiskEvaluationRequest"
            )

        existing_report = self._reports.get(
            request.evaluation_id
        )

        if existing_report is not None:
            return existing_report

        evaluated_at = self._current_time()

        if evaluated_at < request.requested_at:
            raise ValueError(
                "evaluation time must not be earlier "
                "than request requested_at"
            )

        if not self._policy.enabled:
            result = RiskEvaluationResult(
                evaluation_id=request.evaluation_id,
                status=RiskEvaluationStatus.COMPLETED,
                decision=RiskDecision.HOLD,
                evaluated_at=evaluated_at,
                order_id=request.request.order_id,
                portfolio_id=request.portfolio_id,
                requested_quantity=request.request.quantity,
                approved_quantity=_ZERO,
                requested_notional=request.order_notional,
                approved_notional=_ZERO,
                recommendation=(
                    "Risk policy is disabled. Hold the order "
                    "for manual review."
                ),
                warnings=(
                    "The active risk policy is disabled.",
                ),
            )

            return self._store_report(
                request=request,
                result=result,
                message=(
                    "Pre-trade risk evaluation was placed "
                    "on hold."
                ),
            )

        violations = self._collect_violations(
            request=request,
            evaluated_at=evaluated_at,
        )

        decision, approved_quantity = (
            self._determine_decision(
                request=request,
                violations=violations,
            )
        )

        approved_notional = (
            approved_quantity * request.market_price
        )

        recommendation = self._recommendation_for(
            decision
        )

        result = RiskEvaluationResult(
            evaluation_id=request.evaluation_id,
            status=RiskEvaluationStatus.COMPLETED,
            decision=decision,
            evaluated_at=evaluated_at,
            order_id=request.request.order_id,
            portfolio_id=request.portfolio_id,
            requested_quantity=request.request.quantity,
            approved_quantity=approved_quantity,
            requested_notional=request.order_notional,
            approved_notional=approved_notional,
            violations=tuple(violations),
            recommendation=recommendation,
            warnings=self._warnings_for(
                violations
            ),
        )

        return self._store_report(
            request=request,
            result=result,
            message=(
                "Pre-trade risk evaluation completed."
            ),
        )

    def get_result(
        self,
        evaluation_id: str,
    ) -> RiskEvaluationResult:
        normalized_evaluation_id = (
            self._normalize_identifier(
                evaluation_id,
                "evaluation_id",
            )
        )

        try:
            return self._results[
                normalized_evaluation_id
            ]
        except KeyError as exc:
            raise KeyError(
                "risk evaluation not found: "
                f"{normalized_evaluation_id}"
            ) from exc

    def get_report(
        self,
        evaluation_id: str,
    ) -> RiskGatewayReport:
        normalized_evaluation_id = (
            self._normalize_identifier(
                evaluation_id,
                "evaluation_id",
            )
        )

        try:
            return self._reports[
                normalized_evaluation_id
            ]
        except KeyError as exc:
            raise KeyError(
                "risk report not found: "
                f"{normalized_evaluation_id}"
            ) from exc

    def reports_for_order(
        self,
        order_id: str,
    ) -> tuple[RiskGatewayReport, ...]:
        normalized_order_id = (
            self._normalize_identifier(
                order_id,
                "order_id",
            )
        )

        evaluation_ids = self._order_evaluations.get(
            normalized_order_id,
            (),
        )

        return tuple(
            self._reports[evaluation_id]
            for evaluation_id in evaluation_ids
        )

    def violations_for_evaluation(
        self,
        evaluation_id: str,
    ) -> tuple[RiskViolation, ...]:
        return self.get_result(
            evaluation_id
        ).violations

    def _collect_violations(
        self,
        *,
        request: RiskEvaluationRequest,
        evaluated_at: datetime,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []

        effective_kill_switch = (
            self._kill_switch_active
            or request.kill_switch_active
        )

        if effective_kill_switch:
            violations.append(
                self._violation(
                    request=request,
                    rule_type=RiskRuleType.KILL_SWITCH,
                    severity=RiskSeverity.CRITICAL,
                    message=(
                        self._kill_switch_reason
                        or "Emergency kill switch is active."
                    ),
                    observed_value=_ONE,
                    limit_value=_ZERO,
                    occurred_at=evaluated_at,
                )
            )

        if (
            not request.trading_session_allowed
            and not self._policy.allow_trading_outside_session
        ):
            violations.append(
                self._violation(
                    request=request,
                    rule_type=RiskRuleType.TRADING_SESSION,
                    severity=RiskSeverity.CRITICAL,
                    message=(
                        "Trading is not allowed during the "
                        "current market session."
                    ),
                    observed_value=_ONE,
                    limit_value=_ZERO,
                    occurred_at=evaluated_at,
                )
            )

        if (
            request.request.side is OrderSide.SELL_SHORT
            and (
                not self._policy.allow_short_selling
                or not request.short_selling_allowed
            )
        ):
            violations.append(
                self._violation(
                    request=request,
                    rule_type=RiskRuleType.SHORT_SELLING,
                    severity=RiskSeverity.CRITICAL,
                    message=(
                        "Short selling is not permitted."
                    ),
                    observed_value=request.request.quantity,
                    limit_value=_ZERO,
                    occurred_at=evaluated_at,
                )
            )

        self._append_limit_violation(
            violations=violations,
            request=request,
            rule_type=RiskRuleType.MAX_ORDER_QUANTITY,
            observed=request.request.quantity,
            limit=self._policy.max_order_quantity,
            message="Maximum order quantity exceeded.",
            occurred_at=evaluated_at,
        )

        self._append_limit_violation(
            violations=violations,
            request=request,
            rule_type=RiskRuleType.MAX_ORDER_NOTIONAL,
            observed=request.order_notional,
            limit=self._policy.max_order_notional,
            message="Maximum order notional exceeded.",
            occurred_at=evaluated_at,
        )

        projected_position_quantity = (
            request.projected_position_quantity
        )

        self._append_limit_violation(
            violations=violations,
            request=request,
            rule_type=RiskRuleType.MAX_POSITION_QUANTITY,
            observed=projected_position_quantity,
            limit=self._policy.max_position_quantity,
            message="Maximum position quantity exceeded.",
            occurred_at=evaluated_at,
        )

        projected_position_notional = (
            self._projected_position_notional(
                request
            )
        )

        self._append_limit_violation(
            violations=violations,
            request=request,
            rule_type=RiskRuleType.MAX_POSITION_NOTIONAL,
            observed=projected_position_notional,
            limit=self._policy.max_position_notional,
            message="Maximum position notional exceeded.",
            occurred_at=evaluated_at,
        )

        projected_gross_exposure = (
            request.gross_exposure
            + request.order_notional
        )

        self._append_limit_violation(
            violations=violations,
            request=request,
            rule_type=RiskRuleType.MAX_GROSS_EXPOSURE,
            observed=projected_gross_exposure,
            limit=self._policy.max_gross_exposure,
            message="Maximum gross exposure exceeded.",
            occurred_at=evaluated_at,
        )

        projected_net_exposure = abs(
            self._projected_net_exposure(
                request
            )
        )

        self._append_limit_violation(
            violations=violations,
            request=request,
            rule_type=RiskRuleType.MAX_NET_EXPOSURE,
            observed=projected_net_exposure,
            limit=self._policy.max_net_exposure,
            message="Maximum net exposure exceeded.",
            occurred_at=evaluated_at,
        )

        if (
            request.order_notional
            > request.available_buying_power
        ):
            violations.append(
                self._violation(
                    request=request,
                    rule_type=RiskRuleType.BUYING_POWER,
                    severity=RiskSeverity.WARNING,
                    message=(
                        "Order notional exceeds available "
                        "buying power."
                    ),
                    observed_value=request.order_notional,
                    limit_value=(
                        request.available_buying_power
                    ),
                    occurred_at=evaluated_at,
                )
            )

        if (
            request.available_buying_power
            < self._policy.minimum_buying_power
        ):
            violations.append(
                self._violation(
                    request=request,
                    rule_type=RiskRuleType.BUYING_POWER,
                    severity=RiskSeverity.CRITICAL,
                    message=(
                        "Available buying power is below "
                        "the policy minimum."
                    ),
                    observed_value=(
                        self._policy.minimum_buying_power
                    ),
                    limit_value=(
                        request.available_buying_power
                    ),
                    occurred_at=evaluated_at,
                )
            )

        if (
            request.available_margin
            < self._policy.minimum_available_margin
        ):
            violations.append(
                self._violation(
                    request=request,
                    rule_type=RiskRuleType.MARGIN,
                    severity=RiskSeverity.CRITICAL,
                    message=(
                        "Available margin is below the "
                        "policy minimum."
                    ),
                    observed_value=(
                        self._policy.minimum_available_margin
                    ),
                    limit_value=request.available_margin,
                    occurred_at=evaluated_at,
                )
            )

        daily_loss = max(
            _ZERO,
            -request.projected_daily_pnl,
        )

        if daily_loss > self._policy.daily_loss_limit:
            violations.append(
                self._violation(
                    request=request,
                    rule_type=RiskRuleType.DAILY_LOSS,
                    severity=RiskSeverity.CRITICAL,
                    message=(
                        "Daily loss limit has been exceeded."
                    ),
                    observed_value=daily_loss,
                    limit_value=(
                        self._policy.daily_loss_limit
                    ),
                    occurred_at=evaluated_at,
                )
            )

        return violations

    def _append_limit_violation(
        self,
        *,
        violations: list[RiskViolation],
        request: RiskEvaluationRequest,
        rule_type: RiskRuleType,
        observed: Decimal,
        limit: Decimal,
        message: str,
        occurred_at: datetime,
    ) -> None:
        if observed <= limit:
            return

        severity = (
            RiskSeverity.WARNING
            if self._policy.reduction_allowed
            else RiskSeverity.CRITICAL
        )

        violations.append(
            self._violation(
                request=request,
                rule_type=rule_type,
                severity=severity,
                message=message,
                observed_value=observed,
                limit_value=limit,
                occurred_at=occurred_at,
            )
        )

    def _determine_decision(
        self,
        *,
        request: RiskEvaluationRequest,
        violations: list[RiskViolation],
    ) -> tuple[RiskDecision, Decimal]:
        if not violations:
            return (
                RiskDecision.APPROVE,
                request.request.quantity,
            )

        if any(
            violation.severity
            is RiskSeverity.CRITICAL
            for violation in violations
        ):
            return RiskDecision.REJECT, _ZERO

        if not self._policy.reduction_allowed:
            return RiskDecision.REJECT, _ZERO

        reduced_quantity = self._maximum_safe_quantity(
            request
        )

        if reduced_quantity <= _ZERO:
            return RiskDecision.REJECT, _ZERO

        if reduced_quantity >= request.request.quantity:
            # A non-quantity warning cannot safely be cleared
            # through order reduction.
            return RiskDecision.REJECT, _ZERO

        return (
            RiskDecision.REDUCE,
            reduced_quantity,
        )

    def _maximum_safe_quantity(
        self,
        request: RiskEvaluationRequest,
    ) -> Decimal:
        market_price = request.market_price

        quantity_limits: list[Decimal] = [
            self._policy.max_order_quantity,
            (
                self._policy.max_order_notional
                / market_price
            ),
            (
                request.available_buying_power
                / market_price
            ),
        ]

        remaining_position_quantity = max(
            _ZERO,
            self._policy.max_position_quantity
            - request.current_position_quantity,
        )

        remaining_position_notional = max(
            _ZERO,
            self._policy.max_position_notional
            - request.current_position_notional,
        )

        remaining_gross_exposure = max(
            _ZERO,
            self._policy.max_gross_exposure
            - request.gross_exposure,
        )

        quantity_limits.extend(
            [
                remaining_position_quantity,
                (
                    remaining_position_notional
                    / market_price
                ),
                (
                    remaining_gross_exposure
                    / market_price
                ),
            ]
        )

        net_capacity = self._net_exposure_capacity(
            request
        )

        quantity_limits.append(
            net_capacity / market_price
        )

        safe_quantity = min(
            request.request.quantity,
            *quantity_limits,
        )

        return safe_quantity.quantize(
            Decimal("0.00000001"),
            rounding=ROUND_DOWN,
        )

    def _projected_position_notional(
        self,
        request: RiskEvaluationRequest,
    ) -> Decimal:
        if request.request.side in {
            OrderSide.BUY,
            OrderSide.SELL_SHORT,
        }:
            return (
                request.current_position_notional
                + request.order_notional
            )

        return max(
            _ZERO,
            request.current_position_notional
            - request.order_notional,
        )

    @staticmethod
    def _projected_net_exposure(
        request: RiskEvaluationRequest,
    ) -> Decimal:
        if request.request.side in {
            OrderSide.BUY,
            OrderSide.BUY_TO_COVER,
        }:
            return (
                request.net_exposure
                + request.order_notional
            )

        return (
            request.net_exposure
            - request.order_notional
        )

    def _net_exposure_capacity(
        self,
        request: RiskEvaluationRequest,
    ) -> Decimal:
        max_net = self._policy.max_net_exposure

        if request.request.side in {
            OrderSide.BUY,
            OrderSide.BUY_TO_COVER,
        }:
            return max(
                _ZERO,
                max_net - request.net_exposure,
            )

        return max(
            _ZERO,
            max_net + request.net_exposure,
        )

    def _violation(
        self,
        *,
        request: RiskEvaluationRequest,
        rule_type: RiskRuleType,
        severity: RiskSeverity,
        message: str,
        observed_value: Decimal,
        limit_value: Decimal,
        occurred_at: datetime,
    ) -> RiskViolation:
        return RiskViolation(
            violation_id=self._next_violation_id(),
            evaluation_id=request.evaluation_id,
            rule_type=rule_type,
            severity=severity,
            message=message,
            observed_value=observed_value,
            limit_value=limit_value,
            occurred_at=occurred_at,
            symbol=request.request.symbol,
            rule_id=(
                f"{self._policy.policy_id}:"
                f"{rule_type.value}"
            ),
            metadata=(
                (
                    "policy_id",
                    self._policy.policy_id,
                ),
            ),
        )

    def _store_report(
        self,
        *,
        request: RiskEvaluationRequest,
        result: RiskEvaluationResult,
        message: str,
    ) -> RiskGatewayReport:
        report = RiskGatewayReport(
            report_id=self._next_report_id(),
            request=request,
            result=result,
            reported_at=result.evaluated_at,
            message=message,
            metadata=(
                (
                    "policy_id",
                    self._policy.policy_id,
                ),
            ),
            warnings=result.warnings,
        )

        self._results[
            request.evaluation_id
        ] = result

        self._reports[
            request.evaluation_id
        ] = report

        self._report_history.append(report)

        self._order_evaluations.setdefault(
            request.request.order_id,
            [],
        ).append(request.evaluation_id)

        return report

    @staticmethod
    def _recommendation_for(
        decision: RiskDecision,
    ) -> str:
        recommendations = {
            RiskDecision.APPROVE: (
                "Order may proceed to the broker gateway."
            ),
            RiskDecision.REDUCE: (
                "Reduce the order to the approved quantity "
                "before submission."
            ),
            RiskDecision.HOLD: (
                "Hold the order for manual risk review."
            ),
            RiskDecision.REJECT: (
                "Do not submit the order."
            ),
        }

        return recommendations[decision]

    @staticmethod
    def _warnings_for(
        violations: list[RiskViolation],
    ) -> tuple[str, ...]:
        return tuple(
            violation.message
            for violation in violations
            if violation.severity
            is RiskSeverity.WARNING
        )

    def _next_violation_id(self) -> str:
        value = (
            f"violation-"
            f"{self._next_violation_number:06d}"
        )
        self._next_violation_number += 1
        return value

    def _next_report_id(self) -> str:
        value = (
            f"risk-report-"
            f"{self._next_report_number:06d}"
        )
        self._next_report_number += 1
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