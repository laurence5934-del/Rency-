from __future__ import annotations

from decimal import Decimal

from .regime_models import (
    MarketRegime,
    MarketRegimeReport,
    MarketRegimeSignal,
    RegimeConfidence,
    RegimeDetectionStatus,
)


_ZERO = Decimal("0")
_ONE = Decimal("1")
_TWO = Decimal("2")
_FIVE = Decimal("5")


class MarketRegimeEngine:
    """Detects the current market regime from normalized signals."""

    def detect(
        self,
        signal: MarketRegimeSignal,
    ) -> MarketRegimeReport:
        if not isinstance(signal, MarketRegimeSignal):
            raise TypeError(
                "signal must be a MarketRegimeSignal"
            )

        try:
            overall_score = self._overall_score(signal)
            regime = self._detect_regime(
                signal=signal,
                overall_score=overall_score,
            )
            confidence = self._confidence(
                signal=signal,
                regime=regime,
                overall_score=overall_score,
            )

            warnings = self._warnings(
                signal=signal,
                regime=regime,
            )

            return MarketRegimeReport(
                status=RegimeDetectionStatus.COMPLETED,
                regime=regime,
                confidence=confidence,
                overall_score=overall_score,
                signal=signal,
                recommendation=self._recommendation(
                    regime
                ),
                warnings=warnings,
            )

        except Exception as exc:
            return MarketRegimeReport(
                status=RegimeDetectionStatus.FAILED,
                regime=MarketRegime.UNKNOWN,
                confidence=RegimeConfidence.LOW,
                overall_score=_ZERO,
                signal=signal,
                recommendation=(
                    "Do not deploy regime-dependent "
                    "strategies until detection succeeds."
                ),
                warnings=(
                    "Market-regime detection failed.",
                ),
                error=str(exc),
            )

    @staticmethod
    def _overall_score(
        signal: MarketRegimeSignal,
    ) -> Decimal:
        defensive_volatility_score = (
            _ONE - signal.volatility_score
        )

        return (
            signal.trend_score
            + defensive_volatility_score
            + signal.breadth_score
            + signal.momentum_score
            + signal.liquidity_score
        ) / _FIVE

    @staticmethod
    def _detect_regime(
        *,
        signal: MarketRegimeSignal,
        overall_score: Decimal,
    ) -> MarketRegime:
        if (
            signal.volatility_score >= Decimal("0.85")
            and signal.liquidity_score <= Decimal("0.25")
            and signal.trend_score <= Decimal("0.25")
        ):
            return MarketRegime.RISK_OFF

        if (
            signal.volatility_score >= Decimal("0.80")
            and signal.trend_score >= Decimal("0.40")
        ):
            return MarketRegime.HIGH_VOLATILITY

        if (
            signal.trend_score <= Decimal("0.15")
            and signal.breadth_score <= Decimal("0.20")
            and signal.momentum_score <= Decimal("0.15")
        ):
            return MarketRegime.STRONG_BEAR

        if (
            signal.trend_score <= Decimal("0.30")
            and signal.breadth_score <= Decimal("0.35")
            and signal.momentum_score <= Decimal("0.30")
        ):
            return MarketRegime.BEAR

        if (
            signal.trend_score <= Decimal("0.45")
            and signal.momentum_score <= Decimal("0.40")
            and signal.breadth_score <= Decimal("0.50")
        ):
            return MarketRegime.CORRECTION

        if (
            signal.trend_score >= Decimal("0.85")
            and signal.breadth_score >= Decimal("0.75")
            and signal.momentum_score >= Decimal("0.80")
            and signal.volatility_score <= Decimal("0.40")
        ):
            return MarketRegime.STRONG_BULL

        if (
            signal.trend_score >= Decimal("0.65")
            and signal.breadth_score >= Decimal("0.60")
            and signal.momentum_score >= Decimal("0.60")
        ):
            return MarketRegime.BULL

        if (
            Decimal("0.40")
            <= overall_score
            <= Decimal("0.60")
        ):
            return MarketRegime.SIDEWAYS

        return MarketRegime.UNKNOWN

    @staticmethod
    def _confidence(
        *,
        signal: MarketRegimeSignal,
        regime: MarketRegime,
        overall_score: Decimal,
    ) -> RegimeConfidence:
        directional_strength = abs(
            overall_score - Decimal("0.50")
        ) * _TWO

        signal_alignment = (
            abs(
                signal.trend_score
                - signal.momentum_score
            )
            + abs(
                signal.trend_score
                - signal.breadth_score
            )
        ) / _TWO

        alignment_score = _ONE - signal_alignment

        confidence_score = (
            directional_strength
            + alignment_score
        ) / _TWO

        if regime is MarketRegime.UNKNOWN:
            return RegimeConfidence.LOW

        if confidence_score >= Decimal("0.85"):
            return RegimeConfidence.VERY_HIGH

        if confidence_score >= Decimal("0.70"):
            return RegimeConfidence.HIGH

        if confidence_score >= Decimal("0.50"):
            return RegimeConfidence.MEDIUM

        return RegimeConfidence.LOW

    @staticmethod
    def _warnings(
        *,
        signal: MarketRegimeSignal,
        regime: MarketRegime,
    ) -> tuple[str, ...]:
        warnings = list(signal.warnings)

        if signal.volatility_score >= Decimal("0.80"):
            warnings.append(
                "Market volatility is elevated."
            )

        if signal.liquidity_score <= Decimal("0.30"):
            warnings.append(
                "Market liquidity is weak."
            )

        if abs(
            signal.trend_score
            - signal.momentum_score
        ) >= Decimal("0.40"):
            warnings.append(
                "Trend and momentum signals are materially divergent."
            )

        if regime is MarketRegime.UNKNOWN:
            warnings.append(
                "Available signals do not support a clear regime."
            )

        return tuple(warnings)

    @staticmethod
    def _recommendation(
        regime: MarketRegime,
    ) -> str:
        recommendations = {
            MarketRegime.STRONG_BULL: (
                "Favor trend-following, momentum, and growth "
                "strategies while maintaining normal risk controls."
            ),
            MarketRegime.BULL: (
                "Maintain constructive exposure and prioritize "
                "high-quality growth and trend strategies."
            ),
            MarketRegime.SIDEWAYS: (
                "Favor range-based, income, and mean-reversion "
                "strategies."
            ),
            MarketRegime.CORRECTION: (
                "Reduce position size and require stronger "
                "confirmation before new entries."
            ),
            MarketRegime.BEAR: (
                "Reduce directional exposure and favor defensive "
                "or hedged strategies."
            ),
            MarketRegime.STRONG_BEAR: (
                "Preserve capital, minimize long exposure, and "
                "prioritize defensive risk controls."
            ),
            MarketRegime.HIGH_VOLATILITY: (
                "Reduce leverage and position size while avoiding "
                "fragile breakout entries."
            ),
            MarketRegime.RISK_OFF: (
                "Prioritize capital preservation, liquidity, and "
                "defensive positioning."
            ),
            MarketRegime.UNKNOWN: (
                "Avoid regime-dependent deployment until market "
                "signals become clearer."
            ),
        }

        return recommendations[regime]