# Version 10.1.1.5 - Enterprise Confidence Engine

The Confidence Engine converts validated consensus output into an explainable
confidence score for downstream risk and decision systems.

## Capabilities

- weighted confidence factors
- consensus and agreement scoring
- contributor reputation input
- validation quality input
- data completeness checks
- signal freshness and stability
- volatility and uncertainty penalties
- confidence bands
- TRUST / REVIEW / REJECT decisions
- metrics, health, and dashboard API

## Compile

```powershell
python -m compileall app/ai/confidence_engine
```

## Smoke test

```powershell
$env:PYTHONPATH = $PWD
python tests/test_confidence_engine_smoke.py
echo $LASTEXITCODE
```

Successful result: `0`
