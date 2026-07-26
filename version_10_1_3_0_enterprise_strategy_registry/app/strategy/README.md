# AITradingOS Enterprise Strategy Registry

**Version:** 10.1.3.0  
**Safety boundary:** registry-only; no broker connectivity, order placement, or live trading.

## Purpose

Provides a centralized, immutable, versioned, and auditable catalog of trading strategy definitions. It is the source of truth for future strategy evaluation, backtesting, paper trading, learning, and deployment workflows.

## Capabilities

- Semantic strategy versions and latest-version lookup
- Draft, testing, certified, deprecated, and disabled lifecycle states
- Deterministic validation of metadata, assets, timeframes, rules, and parameters
- Thread-safe registration, lookup, filtering, replacement, status transitions, and removal
- Safe declarative JSON loading (no dynamic code import)
- Parameter profiles and overrides
- Dependency graph validation and topological ordering
- Pluggable executable strategy builders
- Audit events, operational counters, and read-only dashboard output

## Integration contract

Downstream systems should consume immutable `StrategyDefinition` objects through `StrategyRegistry` or `StrategyManager`. Live execution must independently enforce certification, portfolio, risk, and broker controls.
