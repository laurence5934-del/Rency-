from app.strategy.analytics.risk import RiskAnalyzer


def test_risk_analyzer_exists():
    analyzer = RiskAnalyzer()
    assert analyzer is not None