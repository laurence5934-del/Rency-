from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from .models import *
from .policy_engine import ConsensusPolicyEngine
from .voting_engine import WeightedVotingEngine
from .registry import ContributorRegistry
from .reputation import ContributorReputationManager
from .metrics import ConsensusMetrics

class EnterpriseAIConsensusEngine:
    def __init__(self, policy=None, registry=None, reputation_manager=None, metrics=None, max_workers=8):
        self.policy_engine=ConsensusPolicyEngine(policy)
        self.registry=registry or ContributorRegistry()
        self.reputation=reputation_manager or ContributorReputationManager()
        self._metrics=metrics or ConsensusMetrics(); self.max_workers=max_workers
        self.voting_engine=WeightedVotingEngine(self.policy_engine.policy.neutral_deadband)
    def evaluate_votes(self, symbol, votes, correlation_id=None):
        started=datetime.now(timezone.utc).isoformat(); adjusted=[]
        for vote in votes:
            if vote.symbol!=symbol: raise ValueError("vote symbol mismatch")
            multiplier=self.reputation.multiplier(vote.contributor_id)
            adjusted.append(ContributorVote(vote.contributor_id,vote.symbol,vote.direction,
                vote.confidence,vote.weight*multiplier,vote.rationale,vote.evidence_ids,
                {**dict(vote.metadata),"reputation_multiplier":multiplier,
                 "original_weight":vote.weight},vote.created_at_utc))
        outcome=self.voting_engine.calculate(tuple(adjusted))
        decision,reasons=self.policy_engine.decide(outcome)
        report=ConsensusReport.create(symbol=symbol,started_at_utc=started,decision=decision,
            outcome=outcome,votes=adjusted,policy=self.policy_engine.policy.snapshot(),
            reasons=reasons,correlation_id=correlation_id)
        self._metrics.increment("consensus_cycles")
        self._metrics.increment("votes_processed",len(adjusted))
        self._metrics.increment({ConsensusDecision.APPROVE:"decisions_approved",
            ConsensusDecision.REVIEW:"decisions_reviewed",
            ConsensusDecision.REJECT:"decisions_rejected",
            ConsensusDecision.ABSTAIN:"decisions_abstained"}[decision])
        return report
    def collect_and_evaluate(self, symbol, context=None, correlation_id=None):
        votes=[]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures={pool.submit(c.vote,symbol,context):c for c in self.registry.enabled()}
            for f in as_completed(futures):
                try: votes.append(f.result())
                except Exception: self._metrics.increment("contributor_errors")
        return self.evaluate_votes(symbol,votes,correlation_id)
    def metrics(self): return self._metrics.snapshot()
    def health(self):
        return {"status":"HEALTHY","registry":self.registry.health(),
                "metrics":self.metrics(),"max_workers":self.max_workers,
                "policy":self.policy_engine.policy.snapshot()}
