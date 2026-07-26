from .validation_models import *
class RiskValidator:
    def __init__(self, maximum_drawdown=.20, maximum_daily_loss=.05):
        self.max_drawdown=maximum_drawdown; self.max_daily_loss=maximum_daily_loss
    def validate(self, signal, context):
        r=context.risk
        if r is None:
            return ValidationCheckResult(ValidationCheckType.RISK,ValidationStatus.WARN,.7,
                ValidationSeverity.WARNING,"RISK_CONTEXT_MISSING","Risk context missing.")
        if r.trading_halted:
            return ValidationCheckResult(ValidationCheckType.RISK,ValidationStatus.FAIL,0,
                ValidationSeverity.CRITICAL,"TRADING_HALTED","Trading is halted.")
        if signal.symbol in r.restricted_symbols:
            return ValidationCheckResult(ValidationCheckType.RISK,ValidationStatus.FAIL,0,
                ValidationSeverity.CRITICAL,"RESTRICTED_SYMBOL","Symbol is restricted.")
        if r.portfolio_drawdown>=self.max_drawdown:
            return ValidationCheckResult(ValidationCheckType.RISK,ValidationStatus.FAIL,0,
                ValidationSeverity.CRITICAL,"MAX_DRAWDOWN_BREACH","Maximum drawdown reached.")
        if r.daily_loss>=self.max_daily_loss:
            return ValidationCheckResult(ValidationCheckType.RISK,ValidationStatus.FAIL,0,
                ValidationSeverity.CRITICAL,"DAILY_LOSS_LIMIT","Daily loss limit reached.")
        score=max(0,min(1,1-r.portfolio_drawdown/self.max_drawdown,1-r.daily_loss/self.max_daily_loss))
        return ValidationCheckResult(ValidationCheckType.RISK,ValidationStatus.PASS,score,
            ValidationSeverity.INFO,"RISK_LIMITS_OK","Risk checks passed.")
