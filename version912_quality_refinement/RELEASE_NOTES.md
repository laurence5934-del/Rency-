# Release Notes — Version 9.1.2

## Fixed

- Stale import:
  - from `app.models.risk_models`
  - to `app.models.portfolio_risk_models`
- Live IBKR call during pytest collection
- Misleading buying-power percentage display

## Added

- Margin multiple
- Available margin estimate
- Two isolated account-summary tests
- Backward-compatible buying-power percentage property
- Installer failure handling
- Automatic rollback backups

## Safety

No execution logic or live-order permissions are enabled by this release.
The Portfolio Advisor remains informational and paper-trading oriented.
