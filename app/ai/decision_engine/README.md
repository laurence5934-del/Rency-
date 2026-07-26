# Version 10.1.1.7 - Enterprise Decision Engine

The Enterprise Decision Engine converts validated signals, AI consensus,
confidence, risk output, portfolio state, position state, and strategy intent
into a final explainable trading decision.

## Capabilities

- BUY, SELL, HOLD, SCALE_IN, SCALE_OUT, CLOSE_POSITION
- CANCEL, DEFER, and ESCALATE_REVIEW
- hard policy gates
- weighted decision scoring
- strategy-to-position-state transformation
- risk-engine enforcement
- conflict resolution
- explainable decisions
- immutable decision reports
- bounded in-memory audit log
- metrics and dashboard API
- correlation ID support

## Compile

```powershell
python -m compileall app/ai/decision_engine
```

## Smoke test

```powershell
$env:PYTHONPATH = $PWD
python tests/test_enterprise_decision_engine_smoke.py
echo $LASTEXITCODE
```

Expected result: `0`
