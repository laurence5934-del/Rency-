from decimal import Decimal

from app.strategy.analytics.expectancy import ExpectancyAnalyzer


def test_average_win():
    analyzer = ExpectancyAnalyzer()

    result = analyzer.average_win(
        [
            Decimal("100"),
            Decimal("-50"),
            Decimal("250"),
            Decimal("-75"),
            Decimal("150"),
        ]
    )

    assert result == Decimal("166.6666666666666666666666667")

def test_average_loss():
    analyzer = ExpectancyAnalyzer()

    result = analyzer.average_loss(
        [
            Decimal("100"),
            Decimal("-50"),
            Decimal("250"),
            Decimal("-75"),
            Decimal("150"),
        ]
    )

    assert result == Decimal("62.5")

def test_payoff_ratio():
    analyzer = ExpectancyAnalyzer()

    result = analyzer.payoff_ratio(
        average_win=Decimal("200"),
        average_loss=Decimal("100"),
    )

    assert result == Decimal("2")

def test_expectancy():
    analyzer = ExpectancyAnalyzer()

    result = analyzer.expectancy(
        win_rate=Decimal("0.40"),
        average_win=Decimal("250"),
        average_loss=Decimal("80"),
    )

    assert result == Decimal("52")

def test_expectancy_percent():
    analyzer = ExpectancyAnalyzer()

    result = analyzer.expectancy_percent(
        expectancy=Decimal("52"),
        average_loss=Decimal("80"),
    )

    assert result == Decimal("0.65")

def test_recovery_factor():
    analyzer = ExpectancyAnalyzer()

    result = analyzer.recovery_factor(
        net_profit=Decimal("1500"),
        max_drawdown=Decimal("300"),
    )

    assert result == Decimal("5")