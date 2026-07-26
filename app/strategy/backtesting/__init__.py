"""AITradingOS Enterprise Backtesting Framework, Version 10.1.3.2 Sprint 2."""

from .audit_log import AuditEvent, BacktestAuditLog
from .backtest_engine import BacktestEngine, BacktestValidationError
from .commission_model import (
    CommissionModel,
    CommissionModelError,
    FlatCommission,
    NoCommission,
    PercentageCommission,
    PerShareCommission,
)
from .execution_simulator import (
    ExecutionError,
    ExecutionReport,
    ExecutionSimulator,
    SimulatedOrder,
)

from .metrics import BacktestMetrics, BacktestMetricsSnapshot
from .models import (
    BacktestConfig,
    BacktestResult,
    BacktestStatus,
    PortfolioSnapshot,
    Position,
    Timeframe,
    Trade,
)
from .simulation_engine import (
    HistoricalBar,
    MarketEvent,
    SimulationEngine,
    SimulationError,
)
from .slippage_model import (
    FixedSlippage,
    NoSlippage,
    OrderSide,
    PercentageSlippage,
    SlippageModel,
    SlippageModelError,
)
from .portfolio_engine import (
    DuplicateTradeError,
    InsufficientBuyingPowerError,
    InsufficientPositionError,
    PortfolioEngine,
    PortfolioError,
    UnsupportedTradeSideError,
)

__all__ = [
    "AuditEvent",
    "BacktestAuditLog",
    "BacktestConfig",
    "BacktestEngine",
    "BacktestMetrics",
    "BacktestMetricsSnapshot",
    "BacktestResult",
    "BacktestStatus",
    "BacktestValidationError",
    "CommissionModel",
    "CommissionModelError",
    "ExecutionError",
    "ExecutionSimulator",
    "FixedSlippage",
    "FlatCommission",
    "HistoricalBar",
    "MarketEvent",
    "NoCommission",
    "NoSlippage",
    "OrderSide",
    "PercentageCommission",
    "PercentageSlippage",
    "PerShareCommission",
    "PortfolioSnapshot",
    "Position",
    "SimulationEngine",
    "SimulationError",
    "SlippageModel",
    "SlippageModelError",
    "Timeframe",
    "Trade",
    "DuplicateTradeError",
    "InsufficientBuyingPowerError",
    "InsufficientPositionError",
    "PortfolioEngine",
    "PortfolioError",
    "UnsupportedTradeSideError",
]
