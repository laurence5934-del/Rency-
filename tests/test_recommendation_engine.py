from __future__ import annotations

import pytest

from app.ai.ranking_models import RankingResult
from app.ai.recommendation_engine import RecommendationEngine
from app.ai.recommendation_models import (
    Recommendation,
    RecommendationReport,
)
from app.ai.recommendation_report import (
    RecommendationReportFormatter,
)
from app.ai.recommendation_rules import RecommendationRules


def make_result(
    *,
    symbol: str = "AAPL",
    recommendation: Recommendation = Recommendation.BUY,
    confidence: float = 85.0,
    overall_score: float = 78.0,
    trend: float = 80.0,
    momentum: float = 75.0,
    volume: float = 70.0,
    breakout: float = 65.0,
    risk: float = 80.0,
) -> RankingResult:
    return RankingResult(
        symbol=symbol,
        overall_score=overall_score,
        confidence=confidence,
        recommendation=recommendation,
        trend_score=trend,
        momentum_score=momentum,
        volume_score=volume,
        breakout_score=breakout,
        risk_score=risk,
        explanations=(),
    )


def test_generate_returns_report() -> None:
    engine = RecommendationEngine()

    report = engine.generate(make_result())

    assert isinstance(report, RecommendationReport)
    assert report.symbol == "AAPL"
    assert report.recommendation is Recommendation.BUY
    assert report.confidence == 85.0
    assert report.overall_score == 78.0


def test_report_summary() -> None:
    report = RecommendationEngine().generate(
        make_result()
    )

    assert report.summary == (
        "AAPL: BUY (85.0% confidence)"
    )


def test_generate_many_preserves_order() -> None:
    engine = RecommendationEngine()

    reports = engine.generate_many(
        [
            make_result(symbol="AAPL"),
            make_result(symbol="MSFT"),
        ]
    )

    assert tuple(
        report.symbol
        for report in reports
    ) == (
        "AAPL",
        "MSFT",
    )


def test_generate_rejects_invalid_result() -> None:
    engine = RecommendationEngine()

    with pytest.raises(TypeError):
        engine.generate(None)  # type: ignore[arg-type]


def test_generate_many_rejects_non_iterable() -> None:
    engine = RecommendationEngine()

    with pytest.raises(TypeError):
        engine.generate_many(None)  # type: ignore[arg-type]


def test_generate_many_rejects_strings() -> None:
    engine = RecommendationEngine()

    with pytest.raises(TypeError):
        engine.generate_many("AAPL")  # type: ignore[arg-type]


def test_strength_rules() -> None:
    result = make_result(
        trend=90,
        momentum=85,
        volume=80,
        breakout=75,
        risk=95,
    )

    strengths = RecommendationRules.strengths(result)

    assert "Strong price trend" in strengths
    assert "Strong market momentum" in strengths
    assert "Healthy volume participation" in strengths
    assert "Favorable breakout conditions" in strengths
    assert "Favorable risk profile" in strengths


def test_weakness_rules() -> None:
    result = make_result(
        trend=30,
        momentum=35,
        volume=25,
        breakout=40,
    )

    weaknesses = RecommendationRules.weaknesses(result)

    assert "Weak price trend" in weaknesses
    assert "Weak market momentum" in weaknesses
    assert "Limited volume participation" in weaknesses
    assert "Breakout conditions are weak" in weaknesses


def test_low_risk_score_creates_elevated_risk() -> None:
    result = make_result(risk=30)

    risks = RecommendationRules.risks(result)

    assert "Elevated risk profile" in risks


def test_moderate_risk_score_creates_moderate_risk() -> None:
    result = make_result(risk=60)

    risks = RecommendationRules.risks(result)

    assert "Moderate risk profile" in risks


def test_low_confidence_creates_risk() -> None:
    result = make_result(confidence=45)

    risks = RecommendationRules.risks(result)

    assert "Low recommendation confidence" in risks


def test_trend_momentum_divergence_creates_risk() -> None:
    result = make_result(
        trend=85,
        momentum=35,
    )

    risks = RecommendationRules.risks(result)

    assert (
        "Momentum does not confirm the current trend"
        in risks
    )


def test_breakout_without_volume_creates_risk() -> None:
    result = make_result(
        breakout=85,
        volume=35,
    )

    risks = RecommendationRules.risks(result)

    assert (
        "Breakout lacks strong volume confirmation"
        in risks
    )


@pytest.mark.parametrize(
    ("recommendation", "expected_action"),
    [
        (
            Recommendation.STRONG_BUY,
            "Consider initiating a position",
        ),
        (
            Recommendation.BUY,
            "Consider initiating a partial position",
        ),
        (
            Recommendation.WATCH,
            "Keep the symbol on the active watchlist",
        ),
        (
            Recommendation.HOLD,
            "Avoid increasing exposure without improvement",
        ),
        (
            Recommendation.SELL,
            "Avoid initiating a new position",
        ),
    ],
)
def test_suggested_actions(
    recommendation: Recommendation,
    expected_action: str,
) -> None:
    result = make_result(
        recommendation=recommendation,
    )

    actions = RecommendationRules.suggested_actions(
        result
    )

    assert expected_action in actions


@pytest.mark.parametrize(
    "method_name",
    [
        "strengths",
        "weaknesses",
        "risks",
        "suggested_actions",
    ],
)
def test_rules_reject_invalid_result(
    method_name: str,
) -> None:
    method = getattr(
        RecommendationRules,
        method_name,
    )

    with pytest.raises(TypeError):
        method(None)  # type: ignore[arg-type]


def test_formatter_contains_report_sections() -> None:
    report = RecommendationEngine().generate(
        make_result()
    )

    output = RecommendationReportFormatter.format(
        report
    )

    assert "Symbol: AAPL" in output
    assert "Recommendation: BUY" in output
    assert "Confidence: 85.0%" in output
    assert "Overall Score: 78.0" in output
    assert "Strengths:" in output
    assert "Weaknesses:" in output
    assert "Risks:" in output
    assert "Suggested Actions:" in output


def test_formatter_handles_empty_sections() -> None:
    report = RecommendationReport(
        symbol="AAPL",
        recommendation=Recommendation.WATCH,
        confidence=60.0,
        overall_score=55.0,
    )

    output = RecommendationReportFormatter.format(
        report
    )

    assert "- None identified" in output
    assert "- No major risks identified" in output
    assert "- No action suggested" in output


def test_formatter_rejects_invalid_report() -> None:
    with pytest.raises(TypeError):
        RecommendationReportFormatter.format(
            None  # type: ignore[arg-type]
        )


def test_format_many() -> None:
    engine = RecommendationEngine()

    reports = engine.generate_many(
        [
            make_result(symbol="AAPL"),
            make_result(symbol="MSFT"),
        ]
    )

    output = RecommendationReportFormatter.format_many(
        reports
    )

    assert "Symbol: AAPL" in output
    assert "Symbol: MSFT" in output
    assert "-" * 60 in output


def test_format_many_empty_iterable() -> None:
    output = RecommendationReportFormatter.format_many(
        []
    )

    assert output == ""


def test_format_many_rejects_non_iterable() -> None:
    with pytest.raises(TypeError):
        RecommendationReportFormatter.format_many(
            None  # type: ignore[arg-type]
        )


def test_format_many_rejects_string() -> None:
    with pytest.raises(TypeError):
        RecommendationReportFormatter.format_many(
            "AAPL"  # type: ignore[arg-type]
        )