import json
from openai import OpenAI
from app.utils.config import OPENAI_API_KEY, OPENAI_MODEL


def score_signal(signal) -> dict:
    if not OPENAI_API_KEY:
        return {"score": 0, "decision": "REJECT", "risk": "HIGH", "reason": "OPENAI_API_KEY not set"}

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
You are a conservative trading risk analyst for paper day trading.
Return ONLY valid JSON with exactly these keys:
score: integer 1-100
decision: BUY, WATCH, or REJECT
risk: LOW, MEDIUM, or HIGH
reason: short explanation under 30 words

Use strict standards. Reject weak volume, conflicting trend, unclear breakout, or poor risk/reward.

Signal JSON:
{signal.model_dump_json()}
"""
    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            temperature=0,
        )
        text = response.output_text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return {
            "score": int(data.get("score", 0)),
            "decision": str(data.get("decision", "REJECT")).upper(),
            "risk": str(data.get("risk", "HIGH")).upper(),
            "reason": str(data.get("reason", "")),
        }
    except Exception as exc:
        return {"score": 0, "decision": "REJECT", "risk": "HIGH", "reason": f"AI scoring failed: {exc}"}
