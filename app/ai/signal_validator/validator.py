from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from .validation_models import *
from .policy_engine import ValidationPolicy, ValidationPolicyEngine
from .validation_engine import ValidationScoreEngine
from .freshness_validator import FreshnessValidator
from .confidence_validator import ConfidenceValidator
from .duplicate_validator import DuplicateValidator
from .conflict_detector import ConflictDetector
from .portfolio_validator import PortfolioValidator
from .risk_validator import RiskValidator
from .quarantine_manager import QuarantineManager
from .metrics import SignalValidationMetrics

class EnterpriseSignalValidator:
    def __init__(self, policy=None, max_workers=8):
        self.policy_engine=ValidationPolicyEngine(policy)
        self.score_engine=ValidationScoreEngine(self.policy_engine.policy)
        self.freshness=FreshnessValidator(); self.confidence=ConfidenceValidator()
        self.duplicate=DuplicateValidator(); self.conflict=ConflictDetector()
        self.portfolio=PortfolioValidator(); self.risk=RiskValidator()
        self.quarantine_manager=QuarantineManager(); self._metrics=SignalValidationMetrics()
        self.max_workers=max_workers
    def validate(self, signal, context=None, correlation_id=None):
        started=datetime.now(timezone.utc).isoformat(); context=context or ValidationContext()
        checks=(self.freshness.validate(signal,context),self.confidence.validate(signal,context),
                self.duplicate.validate(signal,context),self.conflict.validate(signal,context),
                self.portfolio.validate(signal,context),self.risk.validate(signal,context))
        score=self.score_engine.calculate(checks)
        decision=self.policy_engine.decide(score,checks)
        reasons=tuple(c.code for c in checks if c.status!=ValidationStatus.PASS)
        report=SignalValidationReport.create(signal_id=signal.signal_id,provider_id=signal.provider_id,
            symbol=signal.symbol,started_at_utc=started,decision=decision,
            validation_score=score,checks=checks,policy=self.policy_engine.policy.snapshot(),
            reasons=reasons,correlation_id=correlation_id)
        self._metrics.increment("signals_validated")
        self._metrics.increment({ValidationDecision.ACCEPT:"signals_accepted",
            ValidationDecision.REVIEW:"signals_reviewed",ValidationDecision.REJECT:"signals_rejected",
            ValidationDecision.QUARANTINE:"signals_quarantined"}[decision])
        if decision==ValidationDecision.QUARANTINE: self.quarantine_manager.add(report)
        return report
    def validate_many(self, signals, context=None):
        self._metrics.increment("validation_cycles"); reports=[]; errors=[]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures={pool.submit(self.validate,s,context):s for s in tuple(signals)}
            for future in as_completed(futures):
                try: reports.append(future.result())
                except Exception as exc:
                    self._metrics.increment("validation_errors"); errors.append(f"{type(exc).__name__}: {exc}")
        return BatchValidationResult(tuple(reports),tuple(errors))
    def metrics(self): return self._metrics.snapshot()
    def quarantine(self, limit=100): return self.quarantine_manager.list(limit)
    def health(self):
        return {"status":"HEALTHY","metrics":self.metrics(),
                "quarantine_size":self.quarantine_manager.size(),
                "duplicate_cache_size":self.duplicate.size(),"max_workers":self.max_workers}
