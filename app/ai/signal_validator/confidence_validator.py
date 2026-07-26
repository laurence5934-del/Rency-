from .validation_models import *
class ConfidenceValidator:
    def __init__(self, minimum_confidence=.50, warning_confidence=.65):
        self.minimum=minimum_confidence; self.warning=warning_confidence
    def validate(self, signal, context):
        c=float(signal.confidence)
        if c<self.minimum:
            return ValidationCheckResult(ValidationCheckType.CONFIDENCE,ValidationStatus.FAIL,c,
                ValidationSeverity.ERROR,"CONFIDENCE_TOO_LOW","Confidence below minimum.")
        if c<self.warning:
            return ValidationCheckResult(ValidationCheckType.CONFIDENCE,ValidationStatus.WARN,c,
                ValidationSeverity.WARNING,"CONFIDENCE_MARGINAL","Confidence requires review.")
        return ValidationCheckResult(ValidationCheckType.CONFIDENCE,ValidationStatus.PASS,c,
            ValidationSeverity.INFO,"CONFIDENCE_ACCEPTABLE","Confidence passed.")
