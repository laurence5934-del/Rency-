from app.ai.openai_scorer import score_signal
from app.models.signal import TradingViewSignal

signal = TradingViewSignal(
    symbol="NVDA", timeframe="5", signal="LONG", price=125.5,
    gap_pct=3.8, relative_volume=2.5, rsi=62,
    ema20=124.2, ema50=121.8, vwap=125,
    trend_4h="BULLISH", trend_1h="BULLISH", orb_breakout="YES",
    atr=2.1, stop_loss=123.4, take_profit=129.7
)

print(score_signal(signal))
