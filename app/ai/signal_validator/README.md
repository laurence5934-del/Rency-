# Version 10.1.1.3 - Enterprise Signal Validator

Install at `app/ai/signal_validator/`.

Compile:
`python -m compileall app/ai/signal_validator`

Smoke test:
`$env:PYTHONPATH = $PWD`
`python tests/test_signal_validator_smoke.py`

Capabilities: freshness, confidence, duplicate, conflict, portfolio and risk
validation; weighted scoring; ACCEPT/REVIEW/REJECT/QUARANTINE decisions;
metrics, health, quarantine storage and concurrent batch validation.
