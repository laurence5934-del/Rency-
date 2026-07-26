from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4

def utc_now(): return datetime.now(timezone.utc).isoformat()

class Direction(str, Enum):
    STRONGLY_BEARISH="STRONGLY_BEARISH"; BEARISH="BEARISH"; NEUTRAL="NEUTRAL"
    BULLISH="BULLISH"; STRONGLY_BULLISH="STRONGLY_BULLISH"

class ConsensusDecision(str, Enum):
    APPROVE="APPROVE"; REVIEW="REVIEW"; REJECT="REJECT"; ABSTAIN="ABSTAIN"

@dataclass(frozen=True, slots=True)
class ContributorVote:
    contributor_id: str
    symbol: str
    direction: Direction
    confidence: float
    weight: float=1.0
    rationale: str=""
    evidence_ids: tuple[str,...]=()
    metadata: Mapping[str,Any]=field(default_factory=dict)
    created_at_utc: str=field(default_factory=utc_now)
    def __post_init__(self):
        if not self.contributor_id.strip(): raise ValueError("contributor_id cannot be empty")
        if not self.symbol.strip(): raise ValueError("symbol cannot be empty")
        if not 0 <= self.confidence <= 1: raise ValueError("confidence must be between 0 and 1")
        if self.weight < 0: raise ValueError("weight cannot be negative")

@dataclass(frozen=True, slots=True)
class ConsensusPolicySnapshot:
    minimum_contributors:int
    approval_threshold:float
    review_threshold:float
    minimum_participation_weight:float
    maximum_dissent_ratio:float
    neutral_deadband:float

@dataclass(frozen=True, slots=True)
class ConsensusOutcome:
    winning_direction:Direction
    consensus_score:float
    agreement_ratio:float
    dissent_ratio:float
    participation_weight:float
    directional_scores:Mapping[str,float]
    contributor_count:int
    abstention_count:int

@dataclass(frozen=True, slots=True)
class ConsensusReport:
    consensus_id:UUID
    symbol:str
    started_at_utc:str
    completed_at_utc:str
    decision:ConsensusDecision
    outcome:ConsensusOutcome
    votes:tuple[ContributorVote,...]
    policy:ConsensusPolicySnapshot
    reasons:tuple[str,...]=()
    correlation_id:str|None=None
    @classmethod
    def create(cls, *, symbol, started_at_utc, decision, outcome, votes:Sequence[ContributorVote],
               policy, reasons=(), correlation_id=None):
        return cls(uuid4(),symbol,started_at_utc,utc_now(),decision,outcome,tuple(votes),
                   policy,tuple(reasons),correlation_id)
    def to_dict(self):
        data=asdict(self); data["consensus_id"]=str(self.consensus_id)
        data["decision"]=self.decision.value
        data["outcome"]["winning_direction"]=self.outcome.winning_direction.value
        return data
