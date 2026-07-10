from fastapi import FastAPI
from app.models.signal import TradingViewSignal
from app.ai.openai_scorer import score_signal
from app.risk.risk_manager import evaluate_trade
from app.db.database import init_db, log_signal
from app.broker.ibkr_official import place_paper_buy

app = FastAPI(title="AI Trading Platform V4 Pro")
init_db()

@app.get("/")
def root():
    return {"status": "AI Trading Platform V4 Pro running", "mode": "paper/manual-first"}

@app.post("/webhook/tradingview")
def tradingview_webhook(signal: TradingViewSignal):
    ai_result = score_signal(signal)
    decision = evaluate_trade(signal, ai_result)
    ibkr_result = None

    if decision.get("final_action") == "PAPER_BUY":
        ibkr_result = place_paper_buy(signal.symbol, int(decision.get("quantity", 0)))

    log_signal(signal, ai_result, decision, ibkr_result)

    return {
        "received": True,
        "symbol": signal.symbol,
        "ai": ai_result,
        "final_action": decision.get("final_action"),
        "quantity": decision.get("quantity", 0),
        "note": decision.get("note"),
        "ibkr": ibkr_result,
    }
