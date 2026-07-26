# Version 10.1.2.1 - Enterprise Performance Analytics Engine

The analytics subsystem transforms portfolio, trade, risk, income, benchmark, attribution, and AI decision data into deterministic snapshots and dashboard-ready reports.

## Safety boundary

This package is read-only with respect to trading operations. It cannot place orders, connect to a broker, or modify portfolio state.

## Main capabilities

- Portfolio value, cash, buying power, exposure, allocation, and P&L
- Win rate, profit factor, expectancy, average and extreme trade outcomes
- Maximum drawdown, volatility, concentration, and Herfindahl index
- Dividend, option-premium, interest, monthly income, run-rate, and yield-on-cost analytics
- AI decision accuracy and confidence summaries
- Benchmark excess-return comparison
- Symbol, strategy, and broker attribution
- Executive text reports, JSON output, metrics, audit events, and health status

## Verification

```powershell
python -m compileall app/analytics
$env:PYTHONPATH = $PWD
python tests/test_enterprise_performance_analytics_smoke.py
echo $LASTEXITCODE
python -m pytest -q tests/test_enterprise_performance_analytics.py
```
