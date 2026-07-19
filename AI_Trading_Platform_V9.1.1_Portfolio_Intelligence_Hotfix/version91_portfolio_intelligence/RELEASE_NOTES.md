# Release Notes — Version 9.1

## Added
- Immutable `PortfolioIntelligence` and `PortfolioAdvisor` models
- Portfolio health scoring from 0–100
- Capacity-aware suggested paper-position size
- Streamlit Portfolio Intelligence component
- Detailed JSON diagnostics
- Six unit tests

## Changed
- Active dashboard uses `show_portfolio_intelligence`
- Duplicate dashboard-state import is removed by the installer
- Known mojibake emoji strings in `main.py` are repaired
- Original account summary is replaced with the intelligence panel
- Duplicate portfolio rendering is removed

## Unchanged
- IBKR data acquisition
- Existing snapshot and risk models
- Paper-trading and manual-approval safeguards
- Order transmission behavior
