from dataclasses import dataclass

import pytest

from app.strategy import (
    DependencyResolutionError, DependencyResolver, RiskProfile, StrategyConflictError,
    StrategyDefinition, StrategyFactory, StrategyManager, StrategyRegistry, StrategyStatus,
    StrategyVersion, StrategyVersioning,
)


def make_strategy(strategy_id="momentum", version=StrategyVersion(1, 0, 0), dependencies=()):
    return StrategyDefinition(
        strategy_id=strategy_id, name=strategy_id.title(), version=version,
        description="Test strategy", author="AITradingOS", category="momentum",
        risk_profile=RiskProfile.MODERATE, supported_assets=("SPY",), supported_timeframes=("1h",),
        parameters={"lookback": 20}, dependencies=dependencies,
        entry_rules=("entry",), exit_rules=("exit",),
    )


def test_registry_versioning_lifecycle_and_dashboard_state():
    registry = StrategyRegistry()
    base = registry.register(make_strategy())
    newer = StrategyVersioning.next_minor(base, parameters={"lookback": 30})
    registry.register(newer)
    assert registry.get("momentum").version == StrategyVersion(1, 1, 0)
    certified = registry.set_status("momentum", "1.1.0", StrategyStatus.CERTIFIED)
    assert certified.status is StrategyStatus.CERTIFIED
    assert registry.snapshot() == {
        "strategy_count": 1, "version_count": 2, "certified_count": 1,
        "strategies": ("momentum@1.0.0", "momentum@1.1.0"),
    }
    with pytest.raises(StrategyConflictError):
        registry.register(base)
    assert registry.metrics.snapshot()["registrations"] == 2
    assert len(registry.audit_log.events()) == 3


def test_validation_dependencies_and_factory_certification_boundary():
    registry = StrategyRegistry()
    core = make_strategy("core")
    overlay = make_strategy("overlay", dependencies=("core",))
    assert [s.strategy_id for s in DependencyResolver().resolve((overlay, core))] == ["core", "overlay"]
    with pytest.raises(DependencyResolutionError):
        DependencyResolver().resolve((overlay,))

    @dataclass
    class Runtime:
        definition: StrategyDefinition
        def evaluate(self, market_context):
            return self.definition.strategy_id

    factory = StrategyFactory()
    factory.register_builder("momentum", Runtime)
    manager = StrategyManager(registry, factory)
    manager.onboard(core)
    with pytest.raises(PermissionError):
        manager.instantiate("core")
    manager.certify("core", "1.0.0")
    assert manager.instantiate("core").evaluate({}) == "core"
