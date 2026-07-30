from app.ai.confidence_engine import (
    ConfidenceDecision,
    ConfidenceInput,
    EnterpriseConfidenceEngine,
)

source = ConfidenceInput(
    symbol="PLTR",
    consensus_score=0.88,
    agreement_ratio=0.86,
    contributor_reputation=0.82,
    validation_quality=0.91,
    data_completeness=0.95,
    freshness_score=0.90,
    stability_score=0.84,
    volatility_penalty=0.03,
    uncertainty_penalty=0.02,
)

engine = EnterpriseConfidenceEngine()
report = engine.evaluate(source)

assert report.symbol == "PLTR"
assert report.decision == ConfidenceDecision.TRUST
assert report.score >= 0.72
assert engine.metrics()["evaluations"] == 1
assert engine.metrics()["trusted"] == 1
