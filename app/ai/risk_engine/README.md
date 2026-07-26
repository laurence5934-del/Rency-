# Version 10.1.1.6 - Enterprise Risk Engine

Capabilities: portfolio and trade risk scoring, position sizing, leverage and loss limits, drawdown protection, sector exposure, liquidity and market controls, dynamic stops and targets, VaR/CVaR, metrics, health, and dashboard API.

Compile:
```powershell
python -m compileall app/ai/risk_engine
```

Smoke test:
```powershell
$env:PYTHONPATH = $PWD
python tests/test_enterprise_risk_engine_smoke.py
echo $LASTEXITCODE
```
Expected result: `0`
