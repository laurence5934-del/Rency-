from __future__ import annotations

import math

import pytest

from app.ai.market_regime_detector import (
    MarketIndicators,
    MarketRegime,
    MarketRegimeDetector,
    RiskState,
    TrendState,
    VolatilityState,
)


def bullish_indicators(**overrides):
    values = {
        "price": 120.0,
        "sma_20": 115.0,
        "sma_50": 108.0,
        "sma_200": 95.0,
        "ema_21": 114.0,
        "rsi": 65.0,
        "macd": 2.0,
        "macd_signal": 1.0,
        "adx": 32.0,
        "atr": 1.2,
        "volume": 1_300_000.0,
        "average_volume": 1_000_000.0,
        "vix": 14.0,
    }
    values.update(overrides)
    return MarketIndicators(**values)


def bearish_indicators(**overrides):
    values = {
        "price": 80.0,
        "sma_20": 84.0,
        "sma_50": 90.0,
        "sma_200": 105.0,
        "ema_21": 85.0,
        "rsi": 35.0,
        "macd": -2.0,
        "macd_signal": -1.0,
        "adx": 35.0,
        "atr": 2.0,
        "volume": 1_200_000.0,
        "average_volume": 1_000_000.0,
        "vix": 28.0,
    }
    values.update(overrides)
    return MarketIndicators(**values)


class TestEnums:
    def test_trend_values(self):
        assert TrendState.BULL.value == "BULL"
        assert TrendState.STRONG_BEAR.value == "STRONG_BEAR"

    def test_volatility_values(self):
        assert VolatilityState.LOW.value == "LOW"
        assert VolatilityState.EXTREME.value == "EXTREME"

    def test_risk_values(self):
        assert RiskState.RISK_ON.value == "RISK_ON"
        assert RiskState.RISK_OFF.value == "RISK_OFF"


class TestMarketIndicators:
    def test_defaults_are_none(self):
        indicators = MarketIndicators()
        assert indicators.available_count() == 0
        assert all(value is None for value in indicators.to_dict().values())

    def test_numeric_values_are_converted_to_float(self):
        indicators = MarketIndicators(price=100, rsi=50)
        assert indicators.price == 100.0
        assert indicators.rsi == 50.0

    @pytest.mark.parametrize("field", ["price", "sma_20", "adx", "atr", "volume", "vix"])
    def test_non_numeric_values_raise_type_error(self, field):
        with pytest.raises(TypeError):
            MarketIndicators(**{field: "bad"})

    @pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
    def test_non_finite_values_raise_value_error(self, value):
        with pytest.raises(ValueError):
            MarketIndicators(price=value)

    @pytest.mark.parametrize(
        "field",
        ["price", "sma_20", "sma_50", "sma_200", "ema_21", "adx", "atr", "volume", "average_volume", "vix"],
    )
    def test_negative_non_negative_fields_raise_value_error(self, field):
        with pytest.raises(ValueError):
            MarketIndicators(**{field: -1})

    @pytest.mark.parametrize("rsi", [-0.1, 100.1])
    def test_rsi_out_of_range_raises(self, rsi):
        with pytest.raises(ValueError):
            MarketIndicators(rsi=rsi)

    @pytest.mark.parametrize("adx", [-0.1, 100.1])
    def test_adx_out_of_range_raises(self, adx):
        with pytest.raises(ValueError):
            MarketIndicators(adx=adx)

    def test_macd_may_be_negative(self):
        indicators = MarketIndicators(macd=-2, macd_signal=-1)
        assert indicators.macd == -2.0

    def test_from_mapping(self):
        indicators = MarketIndicators.from_mapping({"price": 101, "rsi": 55})
        assert indicators == MarketIndicators(price=101, rsi=55)

    def test_from_mapping_requires_mapping(self):
        with pytest.raises(TypeError):
            MarketIndicators.from_mapping([("price", 100)])

    def test_from_mapping_rejects_unknown_fields(self):
        with pytest.raises(ValueError, match="unknown indicator fields"):
            MarketIndicators.from_mapping({"price": 100, "unknown": 1})

    def test_available_count(self):
        assert MarketIndicators(price=100, rsi=50, atr=2).available_count() == 3

    def test_to_dict_contains_all_fields(self):
        result = MarketIndicators(price=100).to_dict()
        assert set(result) == set(MarketIndicators.__dataclass_fields__)
        assert result["price"] == 100.0

    def test_dataclass_is_frozen(self):
        indicators = MarketIndicators(price=100)
        with pytest.raises(Exception):
            indicators.price = 101


class TestMarketRegime:
    def test_tradeable_bull_and_bear_states(self):
        for trend in (TrendState.STRONG_BULL, TrendState.BULL, TrendState.BEAR, TrendState.STRONG_BEAR):
            regime = MarketRegime(trend, VolatilityState.NORMAL, RiskState.NEUTRAL, 0.5, 0.4, 0.4, (), 3)
            assert regime.is_tradeable_trend is True

    def test_sideways_and_unknown_are_not_tradeable(self):
        for trend in (TrendState.SIDEWAYS, TrendState.UNKNOWN):
            regime = MarketRegime(trend, VolatilityState.UNKNOWN, RiskState.UNKNOWN, 0.0, 0.0, 0.0, (), 0)
            assert regime.is_tradeable_trend is False

    def test_to_dict_serializes_enums_and_reasons(self):
        regime = MarketRegime(
            TrendState.BULL,
            VolatilityState.LOW,
            RiskState.RISK_ON,
            0.75,
            0.5,
            0.2,
            ("reason",),
            7,
        )
        result = regime.to_dict()
        assert result["trend"] == "BULL"
        assert result["volatility"] == "LOW"
        assert result["risk"] == "RISK_ON"
        assert result["reasons"] == ["reason"]
        assert result["is_tradeable_trend"] is True


class TestDetectorValidation:
    def test_default_configuration(self):
        detector = MarketRegimeDetector()
        assert detector.trend_threshold == 0.25
        assert detector.strong_trend_threshold == 0.65
        assert detector.minimum_indicators == 3
        assert detector.last_regime is None

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"trend_threshold": 0},
            {"trend_threshold": 0.7, "strong_trend_threshold": 0.65},
            {"strong_trend_threshold": 1.1},
        ],
    )
    def test_invalid_trend_thresholds_raise(self, kwargs):
        with pytest.raises(ValueError):
            MarketRegimeDetector(**kwargs)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"low_volatility_atr_percent": 3.0},
            {"high_volatility_atr_percent": 5.0},
            {"extreme_volatility_atr_percent": 2.0},
        ],
    )
    def test_invalid_atr_thresholds_raise(self, kwargs):
        with pytest.raises(ValueError):
            MarketRegimeDetector(**kwargs)

    def test_invalid_vix_thresholds_raise(self):
        with pytest.raises(ValueError):
            MarketRegimeDetector(high_vix_threshold=40, extreme_vix_threshold=35)

    def test_minimum_indicators_requires_integer(self):
        with pytest.raises(TypeError):
            MarketRegimeDetector(minimum_indicators=3.5)
        with pytest.raises(TypeError):
            MarketRegimeDetector(minimum_indicators=True)

    def test_minimum_indicators_must_be_positive(self):
        with pytest.raises(ValueError):
            MarketRegimeDetector(minimum_indicators=0)

    def test_repr_contains_configuration(self):
        text = repr(MarketRegimeDetector())
        assert "MarketRegimeDetector" in text
        assert "trend_threshold=0.25" in text
        assert "minimum_indicators=3" in text


class TestDetection:
    def test_detect_accepts_mapping(self):
        result = MarketRegimeDetector().detect({"price": 100, "sma_200": 90, "rsi": 60})
        assert isinstance(result, MarketRegime)

    def test_detect_rejects_invalid_type(self):
        with pytest.raises(TypeError):
            MarketRegimeDetector().detect("bad")

    def test_insufficient_indicators_returns_unknown(self):
        result = MarketRegimeDetector(minimum_indicators=3).detect(MarketIndicators(price=100, rsi=50))
        assert result.trend is TrendState.UNKNOWN
        assert result.volatility is VolatilityState.UNKNOWN
        assert result.risk is RiskState.UNKNOWN
        assert result.confidence == 0.0
        assert "Insufficient indicators" in result.reasons[0]

    def test_strong_bull_market(self):
        result = MarketRegimeDetector().detect(bullish_indicators())
        assert result.trend is TrendState.STRONG_BULL
        assert result.volatility is VolatilityState.LOW
        assert result.risk is RiskState.RISK_ON
        assert result.trend_score > 0.65
        assert result.confidence > 0.7

    def test_strong_bear_market(self):
        result = MarketRegimeDetector().detect(bearish_indicators())
        assert result.trend is TrendState.STRONG_BEAR
        assert result.volatility is VolatilityState.NORMAL
        assert result.risk is RiskState.RISK_OFF
        assert result.trend_score < -0.65

    def test_sideways_market(self):
        indicators = MarketIndicators(
            price=100,
            sma_20=100,
            sma_50=100,
            sma_200=100,
            ema_21=100,
            rsi=50,
            macd=0,
            macd_signal=0,
            adx=10,
            atr=2,
            vix=20,
        )
        result = MarketRegimeDetector().detect(indicators)
        assert result.trend is TrendState.SIDEWAYS
        assert result.risk is RiskState.NEUTRAL
        assert result.confidence >= 0.45

    @pytest.mark.parametrize(
        ("atr", "expected"),
        [
            (0.5, VolatilityState.LOW),
            (2.0, VolatilityState.NORMAL),
            (4.0, VolatilityState.HIGH),
            (6.0, VolatilityState.EXTREME),
        ],
    )
    def test_atr_volatility_classification(self, atr, expected):
        indicators = MarketIndicators(price=100, atr=atr, rsi=50)
        result = MarketRegimeDetector(minimum_indicators=3).detect(indicators)
        assert result.volatility is expected

    @pytest.mark.parametrize(
        ("vix", "expected"),
        [
            (12, VolatilityState.LOW),
            (20, VolatilityState.NORMAL),
            (28, VolatilityState.HIGH),
            (40, VolatilityState.EXTREME),
        ],
    )
    def test_vix_volatility_classification(self, vix, expected):
        indicators = MarketIndicators(price=100, rsi=50, vix=vix)
        result = MarketRegimeDetector().detect(indicators)
        assert result.volatility is expected

    def test_extreme_volatility_forces_risk_off(self):
        result = MarketRegimeDetector().detect(bullish_indicators(atr=7, vix=40))
        assert result.volatility is VolatilityState.EXTREME
        assert result.risk is RiskState.RISK_OFF

    def test_vix_at_30_forces_risk_off(self):
        result = MarketRegimeDetector().detect(bullish_indicators(vix=30, atr=2))
        assert result.risk is RiskState.RISK_OFF

    def test_last_regime_is_updated(self):
        detector = MarketRegimeDetector()
        result = detector.detect(bullish_indicators())
        assert detector.last_regime is result

    def test_reset_clears_last_regime(self):
        detector = MarketRegimeDetector()
        detector.detect(bullish_indicators())
        detector.reset()
        assert detector.last_regime is None

    def test_to_dict_before_detection(self):
        result = MarketRegimeDetector().to_dict()
        assert result["last_regime"] is None
        assert result["minimum_indicators"] == 3

    def test_to_dict_after_detection(self):
        detector = MarketRegimeDetector()
        detector.detect(bullish_indicators())
        result = detector.to_dict()
        assert result["last_regime"]["trend"] == "STRONG_BULL"

    def test_reasons_explain_the_result(self):
        result = MarketRegimeDetector().detect(bullish_indicators())
        assert any("SMA 200" in reason for reason in result.reasons)
        assert any("MACD" in reason for reason in result.reasons)
        assert any("ATR volatility" in reason for reason in result.reasons)


class TestRegimeMultipliers:
    def test_requires_available_regime(self):
        with pytest.raises(ValueError):
            MarketRegimeDetector().regime_multipliers()

    def test_strong_bull_favors_buy(self):
        detector = MarketRegimeDetector()
        regime = detector.detect(bullish_indicators())
        multipliers = detector.regime_multipliers(regime)
        assert multipliers["BUY"] > 1.0
        assert multipliers["BUY"] > multipliers["SELL"]

    def test_strong_bear_favors_sell(self):
        detector = MarketRegimeDetector()
        multipliers = detector.regime_multipliers(detector.detect(bearish_indicators()))
        assert multipliers["SELL"] > multipliers["BUY"]

    def test_sideways_favors_hold(self):
        detector = MarketRegimeDetector()
        regime = detector.detect(
            MarketIndicators(price=100, sma_20=100, sma_50=100, sma_200=100, atr=2, vix=20)
        )
        multipliers = detector.regime_multipliers(regime)
        assert multipliers["HOLD"] > multipliers["BUY"]
        assert multipliers["HOLD"] > multipliers["SELL"]

    def test_extreme_volatility_reduces_directional_weights(self):
        detector = MarketRegimeDetector()
        regime = detector.detect(bullish_indicators(atr=7, vix=40))
        multipliers = detector.regime_multipliers(regime)
        assert multipliers["HOLD"] > multipliers["BUY"]

    def test_uses_last_regime_by_default(self):
        detector = MarketRegimeDetector()
        detector.detect(bullish_indicators())
        assert detector.regime_multipliers() == detector.regime_multipliers(detector.last_regime)

    def test_multiplier_values_are_rounded(self):
        detector = MarketRegimeDetector()
        multipliers = detector.regime_multipliers(detector.detect(bullish_indicators()))
        assert all(value == round(value, 6) for value in multipliers.values())
