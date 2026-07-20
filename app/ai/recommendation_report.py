from __future__ import annotations

from collections.abc import Iterable

from app.ai.recommendation_models import RecommendationReport


class RecommendationReportFormatter:
    """
    Formats recommendation reports for console output,
    logs, emails, and future dashboards.
    """

    @staticmethod
    def format(
        report: RecommendationReport,
    ) -> str:
        if not isinstance(report, RecommendationReport):
            raise TypeError(
                "report must be a RecommendationReport."
            )

        lines = [
            f"Symbol: {report.symbol}",
            f"Recommendation: {report.recommendation.value}",
            f"Confidence: {report.confidence:.1f}%",
            f"Overall Score: {report.overall_score:.1f}",
            "",
            "Strengths:",
        ]

        lines.extend(
            RecommendationReportFormatter._format_items(
                report.strengths,
                empty_message="None identified",
            )
        )

        lines.extend(
            [
                "",
                "Weaknesses:",
            ]
        )

        lines.extend(
            RecommendationReportFormatter._format_items(
                report.weaknesses,
                empty_message="None identified",
            )
        )

        lines.extend(
            [
                "",
                "Risks:",
            ]
        )

        lines.extend(
            RecommendationReportFormatter._format_items(
                report.risks,
                empty_message="No major risks identified",
            )
        )

        lines.extend(
            [
                "",
                "Suggested Actions:",
            ]
        )

        lines.extend(
            RecommendationReportFormatter._format_items(
                report.suggested_actions,
                empty_message="No action suggested",
            )
        )

        return "\n".join(lines)

    @classmethod
    def format_many(
        cls,
        reports: Iterable[RecommendationReport],
    ) -> str:
        if isinstance(reports, (str, bytes)):
            raise TypeError(
                "reports must be an iterable of RecommendationReport objects."
            )

        try:
            report_list = list(reports)
        except TypeError as exc:
            raise TypeError(
                "reports must be an iterable of RecommendationReport objects."
            ) from exc

        formatted_reports = tuple(
            cls.format(report)
            for report in report_list
        )

        if not formatted_reports:
            return ""

        separator = "\n\n" + ("-" * 60) + "\n\n"

        return separator.join(formatted_reports)

    @staticmethod
    def _format_items(
        items: tuple[str, ...],
        *,
        empty_message: str,
    ) -> tuple[str, ...]:
        if not items:
            return (f"- {empty_message}",)

        return tuple(
            f"- {item}"
            for item in items
        )