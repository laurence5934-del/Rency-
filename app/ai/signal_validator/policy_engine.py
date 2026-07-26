from dataclasses import dataclass, field
from typing import Mapping
from .validation_models import *

@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    minimum_accept_score: float=.75
    minimum_review_score: float=.50
    quarantine_on_critical: bool=True
    reject_on_error: bool=True
    check_weights: Mapping[ValidationCheckType,float]=field(default_factory=lambda:{
        ValidationCheckType.FRESHNESS:.20, ValidationCheckType.CONFIDENCE:.20,
        ValidationCheckType.DUPLICATE:.15, ValidationCheckType.CONFLICT:.15,
        ValidationCheckType.PORTFOLIO:.10, ValidationCheckType.RISK:.20})
    def __post_init__(self):
        if not 0 <= self.minimum_review_score <= self.minimum_accept_score <= 1:
            raise ValueError("invalid policy thresholds")
    def snapshot(self):
        return ValidationPolicySnapshot(self.minimum_accept_score,self.minimum_review_score,
            self.quarantine_on_critical,self.reject_on_error,
            {k.value:v for k,v in self.check_weights.items()})

class ValidationPolicyEngine:
    def __init__(self, policy=None): self.policy=policy or ValidationPolicy()
    def decide(self, score, checks):
        if self.policy.quarantine_on_critical and any(
            c.severity==ValidationSeverity.CRITICAL and c.status in {ValidationStatus.FAIL,ValidationStatus.ERROR}
            for c in checks): return ValidationDecision.QUARANTINE
        if self.policy.reject_on_error and any(c.status==ValidationStatus.ERROR for c in checks):
            return ValidationDecision.REJECT
        if score >= self.policy.minimum_accept_score and all(c.status!=ValidationStatus.FAIL for c in checks):
            return ValidationDecision.ACCEPT
        if score >= self.policy.minimum_review_score: return ValidationDecision.REVIEW
        return ValidationDecision.REJECT
