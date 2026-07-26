# Version 10.1.2.0 - Enterprise Portfolio Management System

This subsystem is the authoritative in-memory portfolio state for simulation and paper-trading stages.

## Capabilities

- cash and buying-power tracking
- long and short position accounting
- weighted average cost
- realized and unrealized P&L
- dividend and income tracking
- market-price updates
- portfolio snapshots
- reconciliation checks
- audit log
- operational metrics
- dashboard API

## Safety

This package contains no live broker credentials and does not submit orders.

## Compile

```powershell
python -m compileall app/portfolio
```

## Smoke test

```powershell
$env:PYTHONPATH = $PWD
python tests/test_enterprise_portfolio_management_smoke.py
echo $LASTEXITCODE
```

Expected result: `0`
