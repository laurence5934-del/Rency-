from datetime import datetime, timezone
from .validation_models import *
def parse_ts(v):
    x=datetime.fromisoformat(v.replace("Z","+00:00"))
    return x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x.astimezone(timezone.utc)
class FreshnessValidator:
    def __init__(self, maximum_age_seconds=300.0, warning_age_seconds=180.0):
        self.maximum=maximum_age_seconds; self.warning=warning_age_seconds
    def validate(self, signal, context):
        now=datetime.now(timezone.utc); age=max(0,(now-parse_ts(signal.observed_at_utc)).total_seconds())
        if signal.expires_at_utc and parse_ts(signal.expires_at_utc)<=now:
            return ValidationCheckResult(ValidationCheckType.FRESHNESS,ValidationStatus.FAIL,0,
                ValidationSeverity.CRITICAL,"SIGNAL_EXPIRED","Signal has expired.",{"age_seconds":age})
        score=max(0,1-age/self.maximum)
        if age>self.maximum:
            return ValidationCheckResult(ValidationCheckType.FRESHNESS,ValidationStatus.FAIL,0,
                ValidationSeverity.ERROR,"SIGNAL_STALE","Signal is stale.",{"age_seconds":age})
        if age>self.warning:
            return ValidationCheckResult(ValidationCheckType.FRESHNESS,ValidationStatus.WARN,score,
                ValidationSeverity.WARNING,"SIGNAL_AGING","Signal is aging.",{"age_seconds":age})
        return ValidationCheckResult(ValidationCheckType.FRESHNESS,ValidationStatus.PASS,score,
            ValidationSeverity.INFO,"SIGNAL_FRESH","Signal freshness passed.",{"age_seconds":age})
