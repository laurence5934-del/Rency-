from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


_ZERO = Decimal("0")


class OrchestratorStatus(str, Enum):
    """Lifecycle status of a paper-trading workflow."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TradeApproval(str, Enum):
    """Final approval state assigned by the orchestrator."""

    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"


class PaperTradeSide(str, Enum):
    """Supported paper-order directions."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class PaperTradeRequest:
    """Immutable request submitted to the paper-trading workflow."""

    request_id: str
    symbol: str
    side: PaperTradeSide
    quantity: Decimal
    strategy_id: str
    submitted_at: datetime
    limit_price: Decimal | None = None
    metadata: tuple[tuple[str, str], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_request_id = self.request_id.strip()
        normalized_symbol = self.symbol.strip().upper()
        normalized_strategy_id = self.strategy_id.strip()

        if not normalized_request_id:
            raise ValueError(
                "request_id must not be empty"
            )

        if not normalized_symbol:
            raise ValueError(
                "symbol must not be empty"
            )

        if not normalized_strategy_id:
            raise ValueError(
                "strategy_id must not be empty"
            )

        if not isinstance(self.side, PaperTradeSide):
            raise TypeError(
                "side must be a PaperTradeSide"
            )

        if not isinstance(self.quantity, Decimal):
            raise TypeError(
                "quantity must be a Decimal"
            )

        if self.quantity <= _ZERO:
            raise ValueError(
                "quantity must be greater than zero"
            )

        if not isinstance(self.submitted_at, datetime):
            raise TypeError(
                "submitted_at must be a datetime"
            )

        if self.submitted_at.tzinfo is None:
            raise ValueError(
                "submitted_at must be timezone-aware"
            )

        if self.limit_price is not None:
            if not isinstance(self.limit_price, Decimal):
                raise TypeError(
                    "limit_price must be a Decimal or None"
                )

            if self.limit_price <= _ZERO:
                raise ValueError(
                    "limit_price must be greater than zero"
                )

        normalized_metadata: list[
            tuple[str, str]
        ] = []

        for item in self.metadata:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "each metadata item must be a two-item tuple"
                )

            name, value = item
            normalized_name = str(name).strip()
            normalized_value = str(value).strip()

            if not normalized_name:
                raise ValueError(
                    "metadata names must not be empty"
                )

            normalized_metadata.append(
                (
                    normalized_name,
                    normalized_value,
                )
            )

        object.__setattr__(
            self,
            "request_id",
            normalized_request_id,
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
            tuple(normalized_metadata),
        )


@dataclass(frozen=True, slots=True)
class PaperTradeResult:
    """Final paper-execution outcome."""

    request_id: str
    approval: TradeApproval
    submitted: bool
    reason: str
    order_id: str | None = None
    execution_price: Decimal | None = None
    executed_quantity: Decimal = _ZERO
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        normalized_request_id = self.request_id.strip()
        normalized_reason = self.reason.strip()

        if not normalized_request_id:
            raise ValueError(
                "request_id must not be empty"
            )

        if not isinstance(
            self.approval,
            TradeApproval,
        ):
            raise TypeError(
                "approval must be a TradeApproval"
            )

        if not isinstance(self.submitted, bool):
            raise TypeError(
                "submitted must be a bool"
            )

        if not normalized_reason:
            raise ValueError(
                "reason must not be empty"
            )

        normalized_order_id = (
            self.order_id.strip()
            if self.order_id is not None
            else None
        )

        if self.submitted and not normalized_order_id:
            raise ValueError(
                "submitted results must include an order_id"
            )

        if not self.submitted and normalized_order_id:
            raise ValueError(
                "non-submitted results must not include an order_id"
            )

        if (
            self.approval
            is not TradeApproval.APPROVED
            and self.submitted
        ):
            raise ValueError(
                "only approved results may be submitted"
            )

        if self.execution_price is not None:
            if not isinstance(
                self.execution_price,
                Decimal,
            ):
                raise TypeError(
                    "execution_price must be a Decimal or None"
                )

            if self.execution_price <= _ZERO:
                raise ValueError(
                    "execution_price must be greater than zero"
                )

        if not isinstance(
            self.executed_quantity,
            Decimal,
        ):
            raise TypeError(
                "executed_quantity must be a Decimal"
            )

        if self.executed_quantity < _ZERO:
            raise ValueError(
                "executed_quantity must not be negative"
            )

        if (
            not self.submitted
            and self.executed_quantity != _ZERO
        ):
            raise ValueError(
                "non-submitted results must have zero "
                "executed_quantity"
            )

        object.__setattr__(
            self,
            "request_id",
            normalized_request_id,
        )
        object.__setattr__(
            self,
            "reason",
            normalized_reason,
        )
        object.__setattr__(
            self,
            "order_id",
            normalized_order_id,
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(self.warnings),
        )


@dataclass(frozen=True, slots=True)
class OrchestratorReport:
    """Unified report from a paper-trading orchestration run."""

    status: OrchestratorStatus
    request: PaperTradeRequest
    approval: TradeApproval
    result: PaperTradeResult
    decision_summary: str
    risk_summary: str
    regime_summary: str
    completed_at: datetime | None = None
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.status,
            OrchestratorStatus,
        ):
            raise TypeError(
                "status must be an OrchestratorStatus"
            )

        if not isinstance(
            self.request,
            PaperTradeRequest,
        ):
            raise TypeError(
                "request must be a PaperTradeRequest"
            )

        if not isinstance(
            self.approval,
            TradeApproval,
        ):
            raise TypeError(
                "approval must be a TradeApproval"
            )

        if not isinstance(
            self.result,
            PaperTradeResult,
        ):
            raise TypeError(
                "result must be a PaperTradeResult"
            )

        if (
            self.request.request_id
            != self.result.request_id
        ):
            raise ValueError(
                "request and result request_id values "
                "must match"
            )

        if self.approval is not self.result.approval:
            raise ValueError(
                "report and result approval values must match"
            )

        normalized_decision_summary = (
            self.decision_summary.strip()
        )
        normalized_risk_summary = (
            self.risk_summary.strip()
        )
        normalized_regime_summary = (
            self.regime_summary.strip()
        )

        if not normalized_decision_summary:
            raise ValueError(
                "decision_summary must not be empty"
            )

        if not normalized_risk_summary:
            raise ValueError(
                "risk_summary must not be empty"
            )

        if not normalized_regime_summary:
            raise ValueError(
                "regime_summary must not be empty"
            )

        if self.completed_at is not None:
            if not isinstance(
                self.completed_at,
                datetime,
            ):
                raise TypeError(
                    "completed_at must be a datetime or None"
                )

            if self.completed_at.tzinfo is None:
                raise ValueError(
                    "completed_at must be timezone-aware"
                )

        normalized_error = (
            self.error.strip()
            if self.error is not None
            else None
        )

        if self.status is OrchestratorStatus.FAILED:
            if not normalized_error:
                raise ValueError(
                    "failed reports must include an error"
                )
        elif normalized_error:
            raise ValueError(
                "only failed reports may include an error"
            )

        if (
            self.status
            is OrchestratorStatus.COMPLETED
            and self.completed_at is None
        ):
            raise ValueError(
                "completed reports must include completed_at"
            )

        object.__setattr__(
            self,
            "decision_summary",
            normalized_decision_summary,
        )
        object.__setattr__(
            self,
            "risk_summary",
            normalized_risk_summary,
        )
        object.__setattr__(
            self,
            "regime_summary",
            normalized_regime_summary,
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