from app.ai.consensus_engine import (
    ConsensusDecision,
    ContributorVote,
    Direction,
    EnterpriseAIConsensusEngine,
)


def test_ai_consensus_engine_smoke() -> None:
    engine = EnterpriseAIConsensusEngine()

    votes = (
        ContributorVote(
            contributor_id="technical",
            symbol="PLTR",
            direction=Direction.BULLISH,
            confidence=0.80,
        ),
        ContributorVote(
            contributor_id="fundamental",
            symbol="PLTR",
            direction=Direction.BULLISH,
            confidence=0.70,
        ),
        ContributorVote(
            contributor_id="sentiment",
            symbol="PLTR",
            direction=Direction.BULLISH,
            confidence=0.75,
        ),
    )

    report = engine.evaluate_votes("PLTR", votes)

    assert report is not None
    assert report.decision == ConsensusDecision.APPROVE
    assert report.outcome.contributor_count == 3
    assert report.outcome.consensus_score >= 0.68
    assert engine.metrics()["votes_processed"] == 3