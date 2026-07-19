# AI Trading Platform — Version 9.1.2

## Quality and Margin-Metric Refinement

Version 9.1.2 is a stabilization release for Version 9.1.

### Changes

- Replaces the confusing Buying Power percentage with **Margin Multiple**
- Adds an **Available Margin Estimate**
- Preserves `buying_power_percent` as a backward-compatible property
- Fixes the stale `PortfolioSnapshot` import in `order_manager.py`
- Converts `test_account_summary.py` from a live IBKR call into isolated unit tests
- Updates Portfolio Intelligence tests
- Creates automatic backups before patching

### Why the account-summary test changed

The previous file executed `get_account_summary()` during pytest collection,
which required a running TWS or IB Gateway session. Unit tests should not
contact external services during import. The replacement uses a fake IBKR
application and verifies the request, response, error handling, and disconnect.

### Installation

Extract the ZIP in the repository root and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

$installer = Get-ChildItem `
    -Path . `
    -Filter "INSTALL_VERSION912.ps1" `
    -Recurse `
    -File |
    Select-Object -First 1

& $installer.FullName
```

### Test sequence

```powershell
python -m pytest tests\test_account_summary.py tests\test_portfolio_intelligence.py -q
python -m pytest tests\test_order_manager.py -q
python -m pytest -q
```

### Dashboard

```powershell
streamlit run app\dashboard\main.py
```

### Rollback

```powershell
& ".\version912_quality_refinement\ROLLBACK_VERSION912.ps1"
```

### Git checkpoint

```powershell
git status
git add app\broker\order_manager.py
git add app\services\portfolio_intelligence.py
git add app\dashboard\components\portfolio_intelligence.py
git add tests\test_account_summary.py
git add tests\test_portfolio_intelligence.py
git commit -m "Add Version 9.1.2 quality and margin metric refinements"
git push
```
