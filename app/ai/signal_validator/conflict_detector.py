from .validation_models import *
SIGNS={"STRONGLY_BEARISH":-1,"BEARISH":-1,"NEUTRAL":0,"BULLISH":1,"STRONGLY_BULLISH":1}
class ConflictDetector:
    def __init__(self, conflict_ratio_threshold=.50): self.threshold=conflict_ratio_threshold
    def validate(self, signal, context):
        peers=[p for p in context.peer_signals if getattr(p,"symbol",None)==signal.symbol and
               getattr(p,"signal_id",None)!=signal.signal_id]
        if not peers:
            return ValidationCheckResult(ValidationCheckType.CONFLICT,ValidationStatus.PASS,1,
                ValidationSeverity.INFO,"NO_PEER_CONFLICT","No peer conflict found.")
        current=SIGNS.get(signal.direction.value,0)
        directional=[p for p in peers if SIGNS.get(p.direction.value,0)!=0]
        if current==0 or not directional:
            return ValidationCheckResult(ValidationCheckType.CONFLICT,ValidationStatus.WARN,.75,
                ValidationSeverity.WARNING,"CONFLICT_INDETERMINATE","Conflict is indeterminate.")
        conflicts=sum(SIGNS.get(p.direction.value,0)==-current for p in directional)
        ratio=conflicts/len(directional); score=max(0,1-ratio)
        if ratio>=self.threshold:
            return ValidationCheckResult(ValidationCheckType.CONFLICT,ValidationStatus.FAIL,score,
                ValidationSeverity.ERROR,"SIGNAL_CONFLICT","Peer signals conflict.",{"ratio":ratio})
        status=ValidationStatus.WARN if conflicts else ValidationStatus.PASS
        severity=ValidationSeverity.WARNING if conflicts else ValidationSeverity.INFO
        return ValidationCheckResult(ValidationCheckType.CONFLICT,status,score,severity,
            "MINOR_SIGNAL_CONFLICT" if conflicts else "SIGNAL_CONSISTENT",
            "Minor conflict found." if conflicts else "Signals are consistent.")
