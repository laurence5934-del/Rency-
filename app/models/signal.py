from typing import Optional
from pydantic import BaseModel

class TradingViewSignal(BaseModel):
    symbol: str
    timeframe: str = "5"
    signal: str = "LONG"
    price: float
    gap_pct: float = 0
    relative_volume: float = 0
    rsi: float = 0
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    vwap: Optional[float] = None
    trend_4h: Optional[str] = None
    trend_1h: Optional[str] = None
    orb_breakout: Optional[str] = None
    atr: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
