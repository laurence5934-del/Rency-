from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping, Protocol, Sequence


class OrchestratorState(str, Enum):
    CREATED = "CREATED"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class CycleStatus(str, Enum):
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class MarketEvent:
    symbol: str
    timestamp_utc: str
    price: float
    volume: float = 0.0
    features: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol cannot be empty")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")
        object.__setattr__(self, "symbol", symbol)


@dataclass(frozen=True, slots=True)
class StageResult:
    stage: str
    started_at_utc: str
    finished_at_utc: str
    duration_ms: float
    success: bool
    output: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TradingCycleResult:
    cycle_id: str
    symbol: str
    status: CycleStatus
    started_at_utc: str
    finished_at_utc: str
    duration_ms: float
    stages: tuple[StageResult, ...]
    final_decision: Any = None
    execution_result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "symbol": self.symbol,
            "status": self.status.value,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "duration_ms": self.duration_ms,
            "stages": [stage.to_dict() for stage in self.stages],
            "final_decision": self.final_decision,
            "execution_result": self.execution_result,
            "error": self.error,
        }


@dataclass(slots=True)
class OrchestratorConfig:
    continue_on_optional_stage_error: bool = True
    maximum_cycle_latency_ms: float = 5_000.0
    minimum_event_interval_ms: float = 0.0
    enable_execution: bool = True
    enable_learning: bool = True
    enable_logging: bool = True

    def __post_init__(self) -> None:
        if self.maximum_cycle_latency_ms <= 0:
            raise ValueError("maximum_cycle_latency_ms must be positive")
        if self.minimum_event_interval_ms < 0:
            raise ValueError("minimum_event_interval_ms cannot be negative")


class Initializable(Protocol):
    def initialize(self) -> None: ...


class Startable(Protocol):
    def start(self) -> None: ...


class Stoppable(Protocol):
    def stop(self) -> None: ...


class HealthCheckable(Protocol):
    def health_check(self) -> Mapping[str, Any]: ...


class MarketRegimeDetector(Protocol):
    def detect(self, event: MarketEvent) -> Any: ...


class StrategyRunner(Protocol):
    def generate_signals(self, event: MarketEvent, regime: Any) -> Sequence[Any]: ...


class StrategySelector(Protocol):
    def select(
        self,
        *,
        event: MarketEvent,
        regime: Any,
        signals: Sequence[Any],
    ) -> Any: ...


class ConfidenceEngine(Protocol):
    def evaluate(
        self,
        *,
        event: MarketEvent,
        regime: Any,
        selection: Any,
        signals: Sequence[Any],
    ) -> Any: ...


class RiskManager(Protocol):
    def assess(
        self,
        *,
        event: MarketEvent,
        regime: Any,
        selection: Any,
        confidence: Any,
        portfolio_state: Any,
    ) -> Any: ...


class PortfolioOptimizer(Protocol):
    def optimize(
        self,
        *,
        event: MarketEvent,
        regime: Any,
        selection: Any,
        confidence: Any,
        risk: Any,
        portfolio_state: Any,
    ) -> Any: ...


class DecisionEngine(Protocol):
    def decide(
        self,
        *,
        event: MarketEvent,
        regime: Any,
        selection: Any,
        confidence: Any,
        risk: Any,
        portfolio_plan: Any,
    ) -> Any: ...


class ExecutionEngine(Protocol):
    def execute(self, decision: Any, event: MarketEvent) -> Any: ...


class DecisionLogger(Protocol):
    def log_cycle(self, result: TradingCycleResult) -> Any: ...


class LearningFramework(Protocol):
    def learn(
        self,
        *,
        event: MarketEvent,
        cycle_result: TradingCycleResult,
    ) -> Any: ...


class PortfolioProvider(Protocol):
    def snapshot(self) -> Any: ...


@dataclass(slots=True)
class OrchestratorDependencies:
    market_regime_detector: MarketRegimeDetector
    strategy_runner: StrategyRunner
    strategy_selector: StrategySelector
    confidence_engine: ConfidenceEngine
    risk_manager: RiskManager
    portfolio_optimizer: PortfolioOptimizer
    decision_engine: DecisionEngine
    portfolio_provider: PortfolioProvider
    execution_engine: ExecutionEngine | None = None
    decision_logger: DecisionLogger | None = None
    learning_framework: LearningFramework | None = None

    def named_components(self) -> dict[str, Any]:
        return {
            "market_regime_detector": self.market_regime_detector,
            "strategy_runner": self.strategy_runner,
            "strategy_selector": self.strategy_selector,
            "confidence_engine": self.confidence_engine,
            "risk_manager": self.risk_manager,
            "portfolio_optimizer": self.portfolio_optimizer,
            "decision_engine": self.decision_engine,
            "portfolio_provider": self.portfolio_provider,
            "execution_engine": self.execution_engine,
            "decision_logger": self.decision_logger,
            "learning_framework": self.learning_framework,
        }


class AIMasterOrchestrator:
    """
    Version 10.0.1 - AI Master Orchestrator.

    Coordinates the full trading workflow:

    market event
      -> market regime
      -> strategy signals
      -> strategy selection
      -> confidence evaluation
      -> portfolio snapshot
      -> risk assessment
      -> portfolio optimization
      -> final decision
      -> execution
      -> audit logging
      -> learning feedback

    The orchestrator uses dependency injection and protocol-based interfaces so
    concrete modules can be replaced without changing the orchestration logic.
    """

    def __init__(
        self,
        dependencies: OrchestratorDependencies,
        config: OrchestratorConfig | None = None,
    ) -> None:
        self.dependencies = dependencies
        self.config = config or OrchestratorConfig()
        self._state = OrchestratorState.CREATED
        self._lock = RLock()
        self._history: list[TradingCycleResult] = []
        self._last_event_time_by_symbol: dict[str, float] = {}

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @property
    def state(self) -> OrchestratorState:
        return self._state

    @property
    def history(self) -> tuple[TradingCycleResult, ...]:
        return tuple(self._history)

    def initialize(self) -> None:
        with self._lock:
            if self._state not in {
                OrchestratorState.CREATED,
                OrchestratorState.STOPPED,
            }:
                raise RuntimeError(
                    f"cannot initialize from state {self._state.value}"
                )

            initialized: list[Any] = []
            try:
                for component in self.dependencies.named_components().values():
                    if component is None:
                        continue
                    initializer = getattr(component, "initialize", None)
                    if callable(initializer):
                        initializer()
                    initialized.append(component)
                self._state = OrchestratorState.INITIALIZED
            except Exception:
                self._state = OrchestratorState.FAILED
                for component in reversed(initialized):
                    stopper = getattr(component, "stop", None)
                    if callable(stopper):
                        try:
                            stopper()
                        except Exception:
                            pass
                raise

    def start(self) -> None:
        with self._lock:
            if self._state == OrchestratorState.CREATED:
                self.initialize()
            if self._state not in {
                OrchestratorState.INITIALIZED,
                OrchestratorState.PAUSED,
            }:
                raise RuntimeError(f"cannot start from state {self._state.value}")

            try:
                for component in self.dependencies.named_components().values():
                    if component is None:
                        continue
                    starter = getattr(component, "start", None)
                    if callable(starter):
                        starter()
                self._state = OrchestratorState.RUNNING
            except Exception:
                self._state = OrchestratorState.FAILED
                raise

    def pause(self) -> None:
        with self._lock:
            if self._state != OrchestratorState.RUNNING:
                raise RuntimeError("orchestrator must be running to pause")
            self._state = OrchestratorState.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self._state != OrchestratorState.PAUSED:
                raise RuntimeError("orchestrator must be paused to resume")
            self._state = OrchestratorState.RUNNING

    def stop(self) -> None:
        with self._lock:
            errors: list[str] = []
            for name, component in reversed(
                list(self.dependencies.named_components().items())
            ):
                if component is None:
                    continue
                stopper = getattr(component, "stop", None)
                if callable(stopper):
                    try:
                        stopper()
                    except Exception as exc:
                        errors.append(f"{name}: {exc}")
            self._state = (
                OrchestratorState.FAILED
                if errors
                else OrchestratorState.STOPPED
            )
            if errors:
                raise RuntimeError("; ".join(errors))

    def health_check(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "state": self._state.value,
            "healthy": self._state
            not in {OrchestratorState.FAILED, OrchestratorState.STOPPED},
            "components": {},
        }
        for name, component in self.dependencies.named_components().items():
            if component is None:
                report["components"][name] = {
                    "available": False,
                    "healthy": True,
                    "optional": True,
                }
                continue

            checker = getattr(component, "health_check", None)
            if callable(checker):
                try:
                    component_report = dict(checker())
                    component_report.setdefault("healthy", True)
                    report["components"][name] = component_report
                except Exception as exc:
                    report["components"][name] = {
                        "healthy": False,
                        "error": str(exc),
                    }
                    report["healthy"] = False
            else:
                report["components"][name] = {
                    "available": True,
                    "healthy": True,
                }
        return report

    def process_market_event(self, event: MarketEvent) -> TradingCycleResult:
        with self._lock:
            if self._state != OrchestratorState.RUNNING:
                raise RuntimeError("orchestrator is not running")

            cycle_id = str(uuid.uuid4())
            cycle_started_wall = time.perf_counter()
            cycle_started_utc = self._utc_now()
            stages: list[StageResult] = []

            if self._should_throttle(event):
                result = TradingCycleResult(
                    cycle_id=cycle_id,
                    symbol=event.symbol,
                    status=CycleStatus.SKIPPED,
                    started_at_utc=cycle_started_utc,
                    finished_at_utc=self._utc_now(),
                    duration_ms=(time.perf_counter() - cycle_started_wall) * 1000,
                    stages=tuple(),
                    error="minimum event interval not reached",
                )
                self._history.append(result)
                return result

            context: dict[str, Any] = {"event": event}

            try:
                context["regime"] = self._run_stage(
                    stages,
                    "market_regime_detection",
                    lambda: self.dependencies.market_regime_detector.detect(event),
                )
                context["signals"] = self._run_stage(
                    stages,
                    "strategy_signal_generation",
                    lambda: self.dependencies.strategy_runner.generate_signals(
                        event, context["regime"]
                    ),
                )
                context["selection"] = self._run_stage(
                    stages,
                    "strategy_selection",
                    lambda: self.dependencies.strategy_selector.select(
                        event=event,
                        regime=context["regime"],
                        signals=context["signals"],
                    ),
                )
                context["confidence"] = self._run_stage(
                    stages,
                    "confidence_evaluation",
                    lambda: self.dependencies.confidence_engine.evaluate(
                        event=event,
                        regime=context["regime"],
                        selection=context["selection"],
                        signals=context["signals"],
                    ),
                )
                context["portfolio_state"] = self._run_stage(
                    stages,
                    "portfolio_snapshot",
                    self.dependencies.portfolio_provider.snapshot,
                )
                context["risk"] = self._run_stage(
                    stages,
                    "risk_assessment",
                    lambda: self.dependencies.risk_manager.assess(
                        event=event,
                        regime=context["regime"],
                        selection=context["selection"],
                        confidence=context["confidence"],
                        portfolio_state=context["portfolio_state"],
                    ),
                )
                context["portfolio_plan"] = self._run_stage(
                    stages,
                    "portfolio_optimization",
                    lambda: self.dependencies.portfolio_optimizer.optimize(
                        event=event,
                        regime=context["regime"],
                        selection=context["selection"],
                        confidence=context["confidence"],
                        risk=context["risk"],
                        portfolio_state=context["portfolio_state"],
                    ),
                )
                context["decision"] = self._run_stage(
                    stages,
                    "final_decision",
                    lambda: self.dependencies.decision_engine.decide(
                        event=event,
                        regime=context["regime"],
                        selection=context["selection"],
                        confidence=context["confidence"],
                        risk=context["risk"],
                        portfolio_plan=context["portfolio_plan"],
                    ),
                )

                execution_result = None
                if (
                    self.config.enable_execution
                    and self.dependencies.execution_engine is not None
                ):
                    execution_result = self._run_stage(
                        stages,
                        "execution",
                        lambda: self.dependencies.execution_engine.execute(
                            context["decision"], event
                        ),
                    )

                result = TradingCycleResult(
                    cycle_id=cycle_id,
                    symbol=event.symbol,
                    status=CycleStatus.COMPLETED,
                    started_at_utc=cycle_started_utc,
                    finished_at_utc=self._utc_now(),
                    duration_ms=(time.perf_counter() - cycle_started_wall) * 1000,
                    stages=tuple(stages),
                    final_decision=context["decision"],
                    execution_result=execution_result,
                )

                if (
                    self.config.enable_logging
                    and self.dependencies.decision_logger is not None
                ):
                    self._run_optional_stage(
                        stages,
                        "decision_logging",
                        lambda: self.dependencies.decision_logger.log_cycle(result),
                    )

                if (
                    self.config.enable_learning
                    and self.dependencies.learning_framework is not None
                ):
                    self._run_optional_stage(
                        stages,
                        "learning_feedback",
                        lambda: self.dependencies.learning_framework.learn(
                            event=event,
                            cycle_result=result,
                        ),
                    )

                result = TradingCycleResult(
                    cycle_id=result.cycle_id,
                    symbol=result.symbol,
                    status=result.status,
                    started_at_utc=result.started_at_utc,
                    finished_at_utc=self._utc_now(),
                    duration_ms=(time.perf_counter() - cycle_started_wall) * 1000,
                    stages=tuple(stages),
                    final_decision=result.final_decision,
                    execution_result=result.execution_result,
                    error=result.error,
                )

            except Exception as exc:
                self._state = OrchestratorState.FAILED
                result = TradingCycleResult(
                    cycle_id=cycle_id,
                    symbol=event.symbol,
                    status=CycleStatus.FAILED,
                    started_at_utc=cycle_started_utc,
                    finished_at_utc=self._utc_now(),
                    duration_ms=(time.perf_counter() - cycle_started_wall) * 1000,
                    stages=tuple(stages),
                    final_decision=context.get("decision"),
                    execution_result=context.get("execution_result"),
                    error=str(exc),
                )

            self._history.append(result)
            self._last_event_time_by_symbol[event.symbol] = time.monotonic()
            return result

    def _run_stage(
        self,
        stages: list[StageResult],
        name: str,
        action: Callable[[], Any],
    ) -> Any:
        started_wall = time.perf_counter()
        started_utc = self._utc_now()
        try:
            output = action()
            finished_utc = self._utc_now()
            duration_ms = (time.perf_counter() - started_wall) * 1000
            stages.append(
                StageResult(
                    stage=name,
                    started_at_utc=started_utc,
                    finished_at_utc=finished_utc,
                    duration_ms=duration_ms,
                    success=True,
                    output=output,
                )
            )
            if duration_ms > self.config.maximum_cycle_latency_ms:
                raise TimeoutError(
                    f"stage {name} exceeded latency limit: {duration_ms:.2f} ms"
                )
            return output
        except Exception as exc:
            stages.append(
                StageResult(
                    stage=name,
                    started_at_utc=started_utc,
                    finished_at_utc=self._utc_now(),
                    duration_ms=(time.perf_counter() - started_wall) * 1000,
                    success=False,
                    error=str(exc),
                )
            )
            raise

    def _run_optional_stage(
        self,
        stages: list[StageResult],
        name: str,
        action: Callable[[], Any],
    ) -> Any:
        try:
            return self._run_stage(stages, name, action)
        except Exception:
            if not self.config.continue_on_optional_stage_error:
                raise
            return None

    def _should_throttle(self, event: MarketEvent) -> bool:
        if self.config.minimum_event_interval_ms <= 0:
            return False
        previous = self._last_event_time_by_symbol.get(event.symbol)
        if previous is None:
            return False
        elapsed_ms = (time.monotonic() - previous) * 1000
        return elapsed_ms < self.config.minimum_event_interval_ms

    def latest_result(self) -> TradingCycleResult | None:
        return self._history[-1] if self._history else None

    def reset_history(self) -> None:
        with self._lock:
            self._history.clear()
            self._last_event_time_by_symbol.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "config": asdict(self.config),
            "health": self.health_check(),
            "history": [result.to_dict() for result in self._history],
        }
