from app.ai.confidence_engine import (
    ConfidenceDecision,
    ConfidenceInput,
    EnterpriseConfidenceEngine,
)


def make_input(**overrides):
    values = dict(
        symbol="NVDA",
        consensus_score=0.85,
        agreement_ratio=0.82,
        contributor_reputation=0.80,
        validation_quality=0.88,
        data_completeness=0.90,
        freshness_score=0.87,
        stability_score=0.83,
        volatility_penalty=0.02,
        uncertainty_penalty=0.03,
    )
    values.update(overrides)
    return ConfidenceInput(**values)


def test_trusts_high_quality_input():
    report = EnterpriseConfidenceEngine().evaluate(make_input())
    assert report.decision == ConfidenceDecision.TRUST


def test_rejects_low_data_completeness():
    report = EnterpriseConfidenceEngine().evaluate(
        make_input(data_completeness=0.30)
    )
    assert report.decision == ConfidenceDecision.REJECT


def test_penalties_reduce_score():
    engine = EnterpriseConfidenceEngine()
    low_penalty = engine.evaluate(make_input())
    high_penalty = engine.evaluate(
        make_input(volatility_penalty=0.30, uncertainty_penalty=0.20)
    )
    assert high_penalty.score < low_penalty.score
