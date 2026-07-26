from .validation_models import *
class PortfolioValidator:
    def __init__(self, maximum_symbol_exposure=.15, maximum_gross_exposure=1.5):
        self.max_symbol=maximum_symbol_exposure; self.max_gross=maximum_gross_exposure
    def validate(self, signal, context):
        p=context.portfolio
        if p is None:
            return ValidationCheckResult(ValidationCheckType.PORTFOLIO,ValidationStatus.WARN,.7,
                ValidationSeverity.WARNING,"PORTFOLIO_CONTEXT_MISSING","Portfolio context missing.")
        symbol=float(p.symbol_exposure.get(signal.symbol,0))
        if symbol>=self.max_symbol:
            return ValidationCheckResult(ValidationCheckType.PORTFOLIO,ValidationStatus.FAIL,0,
                ValidationSeverity.ERROR,"SYMBOL_EXPOSURE_LIMIT","Symbol exposure limit reached.")
        if p.gross_exposure>=self.max_gross:
            return ValidationCheckResult(ValidationCheckType.PORTFOLIO,ValidationStatus.FAIL,0,
                ValidationSeverity.ERROR,"GROSS_EXPOSURE_LIMIT","Gross exposure limit reached.")
        score=max(0,min(1,1-symbol/self.max_symbol,1-p.gross_exposure/self.max_gross))
        return ValidationCheckResult(ValidationCheckType.PORTFOLIO,ValidationStatus.PASS,score,
            ValidationSeverity.INFO,"PORTFOLIO_LIMITS_OK","Portfolio checks passed.")
