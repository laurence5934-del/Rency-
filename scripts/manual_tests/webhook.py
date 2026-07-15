import requests

url = "http://127.0.0.1:8000/webhook/tradingview"
payload = {
    "symbol": "NVDA",
    "timeframe": "5",
    "signal": "LONG",
    "price": 125.50,
    "gap_pct": 3.8,
    "relative_volume": 2.5,
    "rsi": 62.0,
    "ema20": 124.20,
    "ema50": 121.80,
    "vwap": 125.00,
    "trend_4h": "BULLISH",
    "trend_1h": "BULLISH",
    "orb_breakout": "YES",
    "atr": 2.10,
    "stop_loss": 123.40,
    "take_profit": 129.70,
}
response = requests.post(url, json=payload, timeout=30)
print("Status Code:", response.status_code)
print("Response:", response.text)
