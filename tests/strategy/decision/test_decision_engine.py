from app.strategy.analytics import StrategyEvaluation

from app.strategy.decision import (
    AggressivePolicy,
    BalancedPolicy,
    ConservativePolicy,
    DecisionAction,
    DecisionEngine,
)


def evaluation(
    *,
    score=100,
    grade="A",
    concerns=(),
):
    return StrategyEvaluation(
        score=score,
        grade=grade,
        recommendation="READY",
        strengths=(),
        concerns=tuple(concerns),
    )


def test_default_policy_is_balanced():
    engine = DecisionEngine()

    assert isinstance(
        engine.policy,
        BalancedPolicy,
    )


def test_can_use_conservative_policy():
    engine = DecisionEngine(
        policy=ConservativePolicy(),
    )

    decision = engine.decide(
        evaluation(
            score=100,
            grade="A",
        )
    )

    assert decision.action is DecisionAction.LIVE_TRADE


def test_can_use_balanced_policy():
    engine = DecisionEngine(
        policy=BalancedPolicy(),
    )

    decision = engine.decide(
        evaluation(
            score=88,
            grade="B",
        )
    )

    assert decision.action is DecisionAction.PAPER_TRADE


def test_can_use_aggressive_policy():
    engine = DecisionEngine(
        policy=AggressivePolicy(),
    )

    decision = engine.decide(
        evaluation(
            score=78,
            grade="B",
        )
    )

    assert decision.action is DecisionAction.PAPER_TRADE


def test_policy_property():
    policy = ConservativePolicy()

    engine = DecisionEngine(
        policy=policy,
    )

    assert engine.policy is policy


def test_engine_delegates_to_policy():
    class StubPolicy:

        def __init__(self):
            self.called = False

        def decide(self, evaluation):
            self.called = True

            from app.strategy.decision import (
                Decision,
                DecisionAction,
            )

            return Decision(
                action=DecisionAction.REJECT,
                confidence=__import__("decimal").Decimal("0.50"),
                reason="Stub",
            )

    stub = StubPolicy()

    engine = DecisionEngine(
        policy=stub,
    )

    decision = engine.decide(
        evaluation()
    )

    assert stub.called

    assert decision.action is DecisionAction.REJECT