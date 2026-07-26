# Version 10.1.1.8 - Enterprise Execution Engine

Default mode is SIMULATED. No live broker connection is included.

Features: order validation, lifecycle state machine, broker adapter abstraction, simulated fills, partial fills, retries, idempotency, reconciliation, metrics, audit log, and dashboard API.

```powershell
python -m compileall app/ai/execution_engine
$env:PYTHONPATH = $PWD
python tests/test_enterprise_execution_engine_smoke.py
echo $LASTEXITCODE
```
Expected: `0`
