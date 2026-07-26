from ai_trading_platform_v4_pro.ai_trading_platform_v4_pro.app.ai.consensus_engine import ContributorVote, Direction, EnterpriseAIConsensusEngine, ConsensusDecision

votes=(
    ContributorVote("technical-ai","PLTR",Direction.STRONGLY_BULLISH,.91,1.2,"Strong trend"),
    ContributorVote("sentiment-ai","PLTR",Direction.BULLISH,.84,1.0,"Positive sentiment"),
    ContributorVote("fundamental-ai","PLTR",Direction.BULLISH,.78,1.1,"Strong fundamentals"),
)
engine=EnterpriseAIConsensusEngine()
report=engine.evaluate_votes("PLTR",votes)
assert report.decision==ConsensusDecision.APPROVE
assert report.outcome.contributor_count==3
assert report.outcome.consensus_score>=.68
assert engine.metrics()["votes_processed"]==3
