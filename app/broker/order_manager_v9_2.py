"""
OMS Order Manager
AI Trading Platform Version 9.2

Coordinates validated paper-order submission through the
persistent OMS repository and the IBKR broker adapter.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.broker.ibkr_official import submit_prepared_paper_order
from app.broker.order_state_machine import normalize_ibkr_status
from app.db.order_repository import OrderRepository
from app.models.order_models import ManagedOrder, OrderState
from app.models.portfolio_risk_models import PortfolioSnapshot
from app.risk.portfolio_risk_manager import evaluate_portfolio_risk

BrokerSubmitter = Callable[..., dict[str, Any]]
RiskEvaluator = Callable[..., Any]


class OrderManager:
    """
    Persistent paper-order submission coordinator.

    The manager records the order before calling IBKR so that
    attempted submissions remain auditable even if the broker
    connection fails.
    """

    def __init__(
        self,
        repository: OrderRepository | None = None,
        *,
        broker_submitter: BrokerSubmitter | None = None,
        risk_evaluator: RiskEvaluator | None = None,
    ) -> None:
        self.repository = (
            repository if repository is not None else OrderRepository()
        )
        self.broker_submitter = (
            broker_submitter
            if broker_submitter is not None
            else submit_prepared_paper_order
        )
        self.risk_evaluator = (
            risk_evaluator
            if risk_evaluator is not None
            else evaluate_portfolio_risk
        )

    @staticmethod
    def _latest_status(
        broker_result: dict[str, Any],
    ) -> dict[str, Any] | None:
        statuses = broker_result.get("statuses", [])

        if not isinstance(statuses, list):
            return None

        for item in reversed(statuses):
            if isinstance(item, dict):
                return item

        return None

    @staticmethod
    def _extract_execution_values(
        broker_result: dict[str, Any],
    ) -> dict[str, float]:
        latest = OrderManager._latest_status(broker_result) or {}

        filled = float(
            latest.get(
                "filled",
                broker_result.get("filled", 0),
            )
            or 0
        )
        remaining = float(
            latest.get(
                "remaining",
                broker_result.get("remaining", 0),
            )
            or 0
        )
        average_fill_price = float(
            latest.get(
                "avgFillPrice",
                latest.get(
                    "average_fill_price",
                    broker_result.get("average_fill_price", 0),
                ),
            )
            or 0
        )
        last_fill_price = float(
            latest.get(
                "lastFillPrice",
                latest.get(
                    "last_fill_price",
                    broker_result.get("last_fill_price", 0),
                ),
            )
            or 0
        )

        return {
            "filled": max(filled, 0.0),
            "remaining": max(remaining, 0.0),
            "average_fill_price": max(average_fill_price, 0.0),
            "last_fill_price": max(last_fill_price, 0.0),
        }

    @staticmethod
    def _risk_payload(risk: Any) -> dict[str, Any]:
        to_dict = getattr(risk, "to_dict", None)
        if callable(to_dict):
            payload = to_dict()
            if isinstance(payload, dict):
                return payload

        def enum_value(value: Any) -> Any:
            return getattr(value, "value", value)

        return {
            "approved": bool(getattr(risk, "approved", False)),
            "decision": enum_value(getattr(risk, "decision", None)),
            "symbol": getattr(risk, "symbol", ""),
            "action": getattr(risk, "action", ""),
            "quantity": getattr(risk, "quantity", 0),
            "entry_price": getattr(risk, "entry_price", 0.0),
            "order_value": getattr(risk, "order_value", 0.0),
            "projected_symbol_value": getattr(
                risk, "projected_symbol_value", 0.0
            ),
            "projected_portfolio_value": getattr(
                risk, "projected_portfolio_value", 0.0
            ),
            "projected_exposure_percent": getattr(
                risk, "projected_exposure_percent", 0.0
            ),
            "errors": list(getattr(risk, "errors", ())),
            "warnings": list(getattr(risk, "warnings", ())),
            "codes": [
                enum_value(code)
                for code in getattr(risk, "codes", ())
            ],
        }

    @staticmethod
    def _failure_state(status: str) -> OrderState:
        normalized = str(status or "").strip().upper()

        if normalized in {"CANCELLED", "APICANCELLED"}:
            return OrderState.CANCELLED

        if normalized == "INACTIVE":
            return OrderState.INACTIVE

        if normalized in {
            "LIVE_TRADING_BLOCKED",
            "PAPER_CONFIRMATION_REQUIRED",
            "NON_PAPER_ORDER_BLOCKED",
            "UNSAFE_PREVIEW_PACKAGE",
        }:
            return OrderState.REJECTED

        return OrderState.ERROR

    def _transition_initial_lifecycle(
        self,
        local_order_id: int,
    ) -> ManagedOrder:
        self.repository.transition_order(
            local_order_id,
            OrderState.VALIDATED,
            source="ORDER_MANAGER",
            message="Prepared order package passed OMS validation.",
        )

        self.repository.transition_order(
            local_order_id,
            OrderState.APPROVED,
            source="ORDER_MANAGER",
            message="Prepared paper order approved for submission.",
        )

        return self.repository.transition_order(
            local_order_id,
            OrderState.SUBMITTING,
            source="ORDER_MANAGER",
            message="IBKR paper-order submission started.",
        )

    def submit_prepared_order(
        self,
        order_request: dict[str, Any],
        *,
        paper_account_confirmed: bool,
        candidate_id: int | None = None,
        strategy: str | None = None,
        wait_seconds: float = 5.0,
    ) -> dict[str, Any]:
        """Persist and submit one prepared paper-order package."""

        local_order: ManagedOrder | None = None

        if bool(order_request.get("transmit", True)):
            return {
                "submitted": False,
                "local_order_id": None,
                "broker_order_id": None,
                "state": OrderState.REJECTED.value,
                "message": (
                    "Unsafe preview package blocked. "
                    "Prepared orders must contain transmit=False."
                ),
            }

        if not bool(order_request.get("paper_only", False)):
            return {
                "submitted": False,
                "local_order_id": None,
                "broker_order_id": None,
                "state": OrderState.REJECTED.value,
                "message": "OMS accepts paper-only prepared orders.",
            }

        try:
            local_order = self.repository.create_order(
                order_request,
                candidate_id=candidate_id,
                strategy=strategy,
                prevent_duplicate=True,
            )
            local_order_id = int(local_order.local_order_id)

            portfolio = PortfolioSnapshot(
                net_liquidation=100_000.0,
                buying_power=50_000.0,
                total_position_value=0.0,
                open_position_count=0,
                daily_realized_pnl=0.0,
                daily_unrealized_pnl=0.0,
                drawdown_percent=0.0,
                symbol_position_values={},
            )

            entry_price = float(
                order_request.get("limit_price")
                or order_request.get("price")
                or 0.0
            )

            candidate = {
                "symbol": str(order_request.get("symbol", "")),
                "action": str(order_request.get("action", "")),
                "quantity": int(order_request.get("quantity", 0) or 0),
                "entry_price": entry_price,
            }

            risk = self.risk_evaluator(
                candidate=candidate,
                portfolio=portfolio,
                paper_trading_only=bool(
                    order_request.get("paper_only", True)
                ),
                emergency_lock_active=False,
            )
            risk_payload = self._risk_payload(risk)

            if not bool(getattr(risk, "approved", False)):
                risk_errors = list(getattr(risk, "errors", ()))
                self.repository.transition_order(
                    local_order_id,
                    OrderState.REJECTED,
                    source="PORTFOLIO_RISK_MANAGER",
                    message=(
                        "; ".join(str(error) for error in risk_errors)
                        or "Portfolio risk evaluation rejected the order."
                    ),
                    broker_payload=risk_payload,
                )

                rejected_order = self.repository.get_order(local_order_id)

                return {
                    "submitted": False,
                    "local_order_id": local_order_id,
                    "broker_order_id": None,
                    "state": OrderState.REJECTED.value,
                    "order": (
                        rejected_order.to_dict()
                        if rejected_order is not None
                        else None
                    ),
                    "risk": risk_payload,
                    "events": [
                        event.to_dict()
                        for event in self.repository.list_order_events(
                            local_order_id
                        )
                    ],
                }

            self._transition_initial_lifecycle(local_order_id)

            broker_result = self.broker_submitter(
                order_request,
                paper_account_confirmed=paper_account_confirmed,
                wait_seconds=wait_seconds,
            )

            if not isinstance(broker_result, dict):
                raise TypeError(
                    "IBKR submission result must be a dictionary."
                )

            broker_order_id = broker_result.get("order_id")
            if broker_order_id is not None:
                self.repository.set_broker_order_id(
                    local_order_id,
                    int(broker_order_id),
                )

            broker_status = str(
                broker_result.get("status", "AWAITING_STATUS")
            ).strip()
            submitted = bool(broker_result.get("submitted", False))
            execution = self._extract_execution_values(broker_result)

            if submitted:
                current = self.repository.get_order(local_order_id)
                if current is None:
                    raise RuntimeError(
                        "Managed order disappeared during broker submission."
                    )

                if execution["filled"] > 0:
                    self.repository.update_execution(
                        local_order_id,
                        filled_quantity=execution["filled"],
                        remaining_quantity=execution["remaining"],
                        average_fill_price=execution[
                            "average_fill_price"
                        ],
                        last_fill_price=execution["last_fill_price"],
                        source="IBKR",
                        broker_payload=broker_result,
                    )
                else:
                    if broker_status.upper() == "AWAITING_STATUS":
                        new_state = OrderState.SUBMITTED
                    else:
                        new_state = normalize_ibkr_status(
                            broker_status,
                            filled=0,
                            remaining=execution["remaining"],
                        )
                        if new_state == OrderState.ERROR:
                            new_state = OrderState.SUBMITTED

                    if new_state != current.state:
                        self.repository.transition_order(
                            local_order_id,
                            new_state,
                            source="IBKR",
                            message=(
                                "Initial broker submission status "
                                f"received: {broker_status}."
                            ),
                            broker_payload=broker_result,
                        )
            else:
                failure_state = self._failure_state(broker_status)
                self.repository.transition_order(
                    local_order_id,
                    failure_state,
                    source="IBKR",
                    message=(
                        "IBKR paper-order submission failed: "
                        f"{broker_status}."
                    ),
                    broker_payload=broker_result,
                )

            final_order = self.repository.get_order(local_order_id)
            if final_order is None:
                raise RuntimeError(
                    "Managed order could not be loaded after submission."
                )

            return {
                "submitted": submitted,
                "local_order_id": final_order.local_order_id,
                "broker_order_id": final_order.broker_order_id,
                "state": final_order.state.value,
                "order": final_order.to_dict(),
                "broker_result": broker_result,
                "risk": risk_payload,
                "events": [
                    event.to_dict()
                    for event in self.repository.list_order_events(
                        local_order_id
                    )
                ],
            }

        except Exception as exc:
            if (
                local_order is not None
                and local_order.local_order_id is not None
            ):
                current = self.repository.get_order(
                    local_order.local_order_id
                )

                if current is not None and not current.is_terminal:
                    try:
                        self.repository.transition_order(
                            current.local_order_id,
                            OrderState.ERROR,
                            source="ORDER_MANAGER",
                            message=str(exc),
                            broker_payload={
                                "exception_type": type(exc).__name__,
                            },
                        )
                    except Exception:
                        pass

            return {
                "submitted": False,
                "local_order_id": (
                    local_order.local_order_id
                    if local_order is not None
                    else None
                ),
                "broker_order_id": None,
                "state": OrderState.ERROR.value,
                "message": str(exc),
            }
