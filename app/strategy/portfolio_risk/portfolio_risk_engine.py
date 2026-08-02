from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from .portfolio_risk_models import (
    ExposureType,
    PortfolioExposure,
    PortfolioRiskDecision,
    PortfolioRiskLimit,
    PortfolioRiskMetrics,
    PortfolioRiskReport,
    PortfolioRiskStatus,
    RiskLimitBreach,
    RiskLimitSeverity,
    RiskLimitType,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")


class PortfolioRiskEngine:
    """Evaluates portfolio metrics and exposures against risk limits."""

    def assess(
        self,
        *,
        metrics: PortfolioRiskMetrics,
        exposures: Iterable[PortfolioExposure],
        limits: Iterable[PortfolioRiskLimit],
    ) -> PortfolioRiskReport:
        self._validate_metrics(metrics)

        try:
            exposure_list = tuple(exposures)
        except TypeError as exc:
            raise TypeError(
                "exposures must be iterable"
            ) from exc

        try:
            limit_list = tuple(limits)
        except TypeError as exc:
            raise TypeError(
                "limits must be iterable"
            ) from exc

        valid_exposures: list[PortfolioExposure] = []
        valid_limits: list[PortfolioRiskLimit] = []

        try:
            for exposure in exposure_list:
                if not isinstance(
                    exposure,
                    PortfolioExposure,
                ):
                    raise TypeError(
                        "every exposure must be a "
                        "PortfolioExposure"
                    )

                valid_exposures.append(exposure)

            for limit in limit_list:
                if not isinstance(
                    limit,
                    PortfolioRiskLimit,
                ):
                    raise TypeError(
                        "every limit must be a "
                        "PortfolioRiskLimit"
                    )

                valid_limits.append(limit)

            self._validate_unique_exposure_ids(
                valid_exposures
            )
            self._validate_unique_limit_ids(
                valid_limits
            )

            breaches = self._evaluate_limits(
                metrics=metrics,
                exposures=valid_exposures,
                limits=valid_limits,
            )

            decision = self._decision(breaches)

            warnings = self._warnings(
                exposures=valid_exposures,
                breaches=breaches,
                metrics=metrics,
            )

            return PortfolioRiskReport(
                status=PortfolioRiskStatus.COMPLETED,
                decision=decision,
                metrics=metrics,
                exposures=tuple(valid_exposures),
                limits=tuple(valid_limits),
                breaches=breaches,
                recommendation=self._recommendation(
                    decision
                ),
                warnings=warnings,
            )

        except Exception as exc:
            return PortfolioRiskReport(
                status=PortfolioRiskStatus.FAILED,
                decision=PortfolioRiskDecision.REVIEW_REQUIRED,
                metrics=metrics,
                exposures=(),
                limits=(),
                breaches=(),
                recommendation=(
                    "Portfolio risk assessment failed. "
                    "Do not approve new exposure until the "
                    "assessment is corrected."
                ),
                warnings=(
                    "Portfolio risk assessment failed.",
                ),
                error=str(exc),
            )

    @classmethod
    def _evaluate_limits(
        cls,
        *,
        metrics: PortfolioRiskMetrics,
        exposures: Iterable[PortfolioExposure],
        limits: Iterable[PortfolioRiskLimit],
    ) -> tuple[RiskLimitBreach, ...]:
        breaches: list[RiskLimitBreach] = []

        for limit in limits:
            if not limit.enabled:
                continue

            observed_values = cls._observed_values(
                limit_type=limit.limit_type,
                metrics=metrics,
                exposures=exposures,
            )

            for label, observed_value in observed_values:
                if observed_value <= limit.threshold:
                    continue

                exceeded_by = (
                    observed_value - limit.threshold
                )

                breaches.append(
                    RiskLimitBreach(
                        limit=limit,
                        observed_value=observed_value,
                        exceeded_by=exceeded_by,
                        message=cls._breach_message(
                            limit=limit,
                            label=label,
                            observed_value=observed_value,
                        ),
                    )
                )

        return tuple(breaches)

    @staticmethod
    def _observed_values(
        *,
        limit_type: RiskLimitType,
        metrics: PortfolioRiskMetrics,
        exposures: Iterable[PortfolioExposure],
    ) -> tuple[tuple[str, Decimal], ...]:
        exposure_list = tuple(exposures)

        if limit_type is RiskLimitType.POSITION_EXPOSURE:
            return tuple(
                (
                    exposure.name,
                    exposure.exposure_ratio,
                )
                for exposure in exposure_list
                if (
                    exposure.exposure_type
                    is ExposureType.POSITION
                )
            )

        if limit_type is RiskLimitType.SECTOR_EXPOSURE:
            return tuple(
                (
                    exposure.name,
                    exposure.exposure_ratio,
                )
                for exposure in exposure_list
                if (
                    exposure.exposure_type
                    is ExposureType.SECTOR
                )
            )

        metric_values = {
            RiskLimitType.GROSS_EXPOSURE: (
                metrics.gross_exposure
            ),
            RiskLimitType.NET_EXPOSURE: (
                metrics.net_exposure
            ),
            RiskLimitType.LEVERAGE: (
                metrics.leverage_ratio
            ),
            RiskLimitType.CONCENTRATION: (
                metrics.concentration_score
            ),
            RiskLimitType.VOLATILITY: (
                metrics.volatility
            ),
            RiskLimitType.DRAWDOWN: (
                metrics.maximum_drawdown
            ),
            RiskLimitType.VALUE_AT_RISK: (
                metrics.value_at_risk
            ),
            RiskLimitType.EXPECTED_SHORTFALL: (
                metrics.expected_shortfall
            ),
            RiskLimitType.RISK_BUDGET: (
                metrics.risk_budget_used
            ),
            # A low liquidity score represents greater risk.
            # Convert it into an illiquidity score so every
            # configured threshold remains a maximum boundary.
            RiskLimitType.LIQUIDITY: (
                _ONE - metrics.liquidity_score
            ),
        }

        if limit_type in metric_values:
            return (
                (
                    limit_type.value,
                    metric_values[limit_type],
                ),
            )

        # Custom limits require an external measurement and
        # therefore are not automatically evaluated here.
        return ()

    @staticmethod
    def _breach_message(
        *,
        limit: PortfolioRiskLimit,
        label: str,
        observed_value: Decimal,
    ) -> str:
        return (
            f"{limit.name} was breached by {label}: "
            f"observed {observed_value}, "
            f"limit {limit.threshold}."
        )

    @staticmethod
    def _decision(
        breaches: Iterable[RiskLimitBreach],
    ) -> PortfolioRiskDecision:
        breach_list = tuple(breaches)

        if any(
            breach.limit.severity
            is RiskLimitSeverity.CRITICAL
            for breach in breach_list
        ):
            return PortfolioRiskDecision.REJECT

        if breach_list:
            return PortfolioRiskDecision.REVIEW_REQUIRED

        return PortfolioRiskDecision.APPROVE

    @staticmethod
    def _warnings(
        *,
        exposures: Iterable[PortfolioExposure],
        breaches: Iterable[RiskLimitBreach],
        metrics: PortfolioRiskMetrics,
    ) -> tuple[str, ...]:
        warnings = [
            warning
            for exposure in exposures
            for warning in exposure.warnings
        ]

        warnings.extend(
            breach.message
            for breach in breaches
        )

        illiquid_count = sum(
            1
            for exposure in exposures
            if not exposure.liquid
        )

        if illiquid_count:
            warnings.append(
                f"{illiquid_count} portfolio exposures "
                "are marked illiquid."
            )

        if metrics.liquidity_score < Decimal("0.50"):
            warnings.append(
                "Portfolio liquidity is below the preferred level."
            )

        if (
            metrics.diversification_score
            < Decimal("0.40")
        ):
            warnings.append(
                "Portfolio diversification is weak."
            )

        return tuple(warnings)

    @staticmethod
    def _recommendation(
        decision: PortfolioRiskDecision,
    ) -> str:
        recommendations = {
            PortfolioRiskDecision.APPROVE: (
                "Portfolio risk remains within configured "
                "limits. New exposure may proceed."
            ),
            PortfolioRiskDecision.REVIEW_REQUIRED: (
                "Review warning-level portfolio risk "
                "breaches before adding new exposure."
            ),
            PortfolioRiskDecision.REJECT: (
                "Reject new exposure until all critical "
                "portfolio risk breaches are resolved."
            ),
        }

        return recommendations[decision]

    @staticmethod
    def _validate_metrics(
        metrics: PortfolioRiskMetrics,
    ) -> None:
        if not isinstance(
            metrics,
            PortfolioRiskMetrics,
        ):
            raise TypeError(
                "metrics must be PortfolioRiskMetrics"
            )

    @staticmethod
    def _validate_unique_exposure_ids(
        exposures: Iterable[PortfolioExposure],
    ) -> None:
        seen: set[str] = set()

        for exposure in exposures:
            if exposure.exposure_id in seen:
                raise ValueError(
                    "exposure_id values must be unique"
                )

            seen.add(exposure.exposure_id)

    @staticmethod
    def _validate_unique_limit_ids(
        limits: Iterable[PortfolioRiskLimit],
    ) -> None:
        seen: set[str] = set()

        for limit in limits:
            if limit.limit_id in seen:
                raise ValueError(
                    "limit_id values must be unique"
                )

            seen.add(limit.limit_id)