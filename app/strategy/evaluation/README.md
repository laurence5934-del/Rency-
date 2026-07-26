# Enterprise Strategy Evaluation Engine — Version 10.1.3.1

A deterministic, explainable, read-only strategy scoring subsystem for AITradingOS Enterprise.

## Capabilities

- Weighted performance, risk, consistency, confidence, and operational scoring
- Configurable evaluation weights with strict validation
- Explainable recommendation outcomes
- Strategy ranking and leaderboard output
- Immutable evidence and evaluation records
- Thread-safe result storage, metrics, and audit events
- Dashboard-ready dictionaries and JSON reports
- No broker connectivity, order placement, or live-trading side effects

## Default weights

- Performance: 40%
- Risk: 25%
- Consistency: 20%
- Confidence: 10%
- Operational: 5%

## Verification

```powershell
python -m compileall app/strategy/evaluation
$env:PYTHONPATH = $PWD
python tests/test_enterprise_strategy_evaluation_smoke.py
python -m pytest -q tests/test_enterprise_strategy_evaluation.py
```
