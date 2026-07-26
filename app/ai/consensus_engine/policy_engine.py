from dataclasses import dataclass
from .models import *

@dataclass(frozen=True, slots=True)
class ConsensusPolicy:
    minimum_contributors:int=3
    approval_threshold:float=.68
    review_threshold:float=.52
    minimum_participation_weight:float=1.5
    maximum_dissent_ratio:float=.35
    neutral_deadband:float=.10
    def __post_init__(self):
        if self.minimum_contributors<=0: raise ValueError("minimum_contributors must be positive")
        if not 0<=self.review_threshold<=self.approval_threshold<=1:
            raise ValueError("invalid thresholds")
    def snapshot(self):
        return ConsensusPolicySnapshot(self.minimum_contributors,self.approval_threshold,
            self.review_threshold,self.minimum_participation_weight,
            self.maximum_dissent_ratio,self.neutral_deadband)

class ConsensusPolicyEngine:
    def __init__(self, policy=None): self.policy=policy or ConsensusPolicy()
    def decide(self, outcome):
        reasons=[]
        if outcome.contributor_count<self.policy.minimum_contributors:
            reasons.append("INSUFFICIENT_CONTRIBUTORS")
        if outcome.participation_weight<self.policy.minimum_participation_weight:
            reasons.append("INSUFFICIENT_PARTICIPATION_WEIGHT")
        if outcome.winning_direction==Direction.NEUTRAL:
            reasons.append("NEUTRAL_CONSENSUS")
        if reasons: return ConsensusDecision.ABSTAIN, tuple(reasons)
        if outcome.dissent_ratio>self.policy.maximum_dissent_ratio:
            return ConsensusDecision.REVIEW, ("EXCESSIVE_DISSENT",)
        if outcome.consensus_score>=self.policy.approval_threshold:
            return ConsensusDecision.APPROVE, ()
        if outcome.consensus_score>=self.policy.review_threshold:
            return ConsensusDecision.REVIEW, ("MARGINAL_CONSENSUS",)
        return ConsensusDecision.REJECT, ("CONSENSUS_BELOW_THRESHOLD",)
