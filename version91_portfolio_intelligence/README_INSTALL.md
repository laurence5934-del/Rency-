# AI Trading Platform — Version 9.1

## Portfolio Intelligence Dashboard

Version 9.1 adds a dashboard-ready portfolio intelligence layer built on the
existing `PortfolioSnapshot`, snapshot adapter, and portfolio risk limits.

## Included

- Live portfolio intelligence metrics
- Portfolio health score and status
- Rule-based AI Portfolio Advisor
- Suggested maximum paper-position size
- Exposure, cash, buying-power, utilization, drawdown, and P/L metrics
- Dashboard integration patch
- Unicode/emoji repairs in `main.py`
- Unit tests
- Automatic backup and rollback script

## Safety

This feature is analytical only. It does not transmit orders. The advisor's
position size is a portfolio-capacity ceiling, not a trade recommendation.
Every candidate must still pass symbol-level risk checks and manual approval.

## Installation

1. Extract this ZIP.
2. Open PowerShell in your repository root.
3. Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& ".ersion91_portfolio_intelligence\INSTALL_VERSION91.ps1"
```

If the folder name differs:

```powershell
$installer = Get-ChildItem -Path . -Filter "INSTALL_VERSION91.ps1" -Recurse -File | Select-Object -First 1
& $installer.FullName
```

## Tests

```powershell
python -m pytest tests	est_portfolio_intelligence.py -q
python -m pytest -q
```

## Start dashboard

```powershell
streamlit run app\dashboard\main.py
```

## Git checkpoint

```powershell
git status
git add app\services\portfolio_intelligence.py
git add app\dashboard\components\portfolio_intelligence.py
git add app\dashboard\main.py
git add tests	est_portfolio_intelligence.py
git commit -m "Add Version 9.1 portfolio intelligence dashboard"
git push
```

## Rollback

```powershell
& ".ersion91_portfolio_intelligence\ROLLBACK_VERSION91.ps1"
```
