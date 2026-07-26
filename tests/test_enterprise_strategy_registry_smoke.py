from app.strategy import RiskProfile, StrategyDefinition, StrategyRegistry, StrategyStatus, StrategyVersion


def main() -> None:
    registry = StrategyRegistry()
    definition = StrategyDefinition(
        strategy_id="momentum-core", name="Momentum Core", version=StrategyVersion(1, 0, 0),
        description="Trend-following strategy", author="AITradingOS", category="momentum",
        risk_profile=RiskProfile.MODERATE, supported_assets=("SPY", "QQQ"),
        supported_timeframes=("1h", "1d"), parameters={"lookback": 20, "risk_per_trade": 0.01},
        entry_rules=("close_above_sma",), exit_rules=("close_below_sma",),
    )
    registry.register(definition)
    certified = registry.set_status("momentum-core", "1.0.0", StrategyStatus.CERTIFIED)
    assert certified.status is StrategyStatus.CERTIFIED
    assert registry.get("momentum-core").key == "momentum-core@1.0.0"
    assert registry.snapshot()["certified_count"] == 1


if __name__ == "__main__":
    main()
