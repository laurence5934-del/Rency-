from app.utils.config import MIN_AI_SCORE, MAX_SHARES_PER_TRADE, MANUAL_APPROVAL_REQUIRED, AUTO_SUBMIT_PAPER_ORDERS


def calculate_quantity(signal) -> int:
    # Conservative starter quantity. Later this can use equity and stop-loss risk.
    return max(0, min(MAX_SHARES_PER_TRADE, int(MAX_SHARES_PER_TRADE)))


def evaluate_trade(signal, ai_result: dict) -> dict:
    score = int(ai_result.get("score", 0))
    decision = str(ai_result.get("decision", "REJECT")).upper()
    quantity = calculate_quantity(signal)

    if score < MIN_AI_SCORE or decision != "BUY":
        return {"final_action": "NO_TRADE", "quantity": 0, "note": "AI score or decision did not pass threshold"}

    if quantity <= 0:
        return {"final_action": "NO_TRADE", "quantity": 0, "note": "Quantity is zero"}

    if MANUAL_APPROVAL_REQUIRED:
        return {"final_action": "MANUAL_REVIEW", "quantity": quantity, "note": "Manual approval required by safety setting"}

    if AUTO_SUBMIT_PAPER_ORDERS:
        return {"final_action": "PAPER_BUY", "quantity": quantity, "note": "Eligible for paper order submission"}

    return {"final_action": "MANUAL_REVIEW", "quantity": quantity, "note": "Auto paper orders disabled"}
