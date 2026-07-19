import pytest

from app.scanner.market_data_adapter import MarketDataAdapter


def make_provider_data() -> dict:
    return {
        "symbol": "AAPL",
        "highs": [101.0, 102.0, 103.0],
        "lows": [99.0, 100.0, 101.0],
        "closes": [100.0, 101.0, 102.0],
        "current_volume": 1_500_000,
    }


def test_adapter_returns_dataframe():
    frame = MarketDataAdapter.to_dataframe(
        make_provider_data()
    )

    assert list(frame.columns) == [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert len(frame) == 3


def test_adapter_maps_price_values():
    frame = MarketDataAdapter.to_dataframe(
        make_provider_data()
    )

    assert frame["high"].tolist() == [101.0, 102.0, 103.0]
    assert frame["low"].tolist() == [99.0, 100.0, 101.0]
    assert frame["close"].tolist() == [100.0, 101.0, 102.0]


def test_adapter_repeats_current_volume():
    frame = MarketDataAdapter.to_dataframe(
        make_provider_data()
    )

    assert frame["volume"].tolist() == [
        1_500_000,
        1_500_000,
        1_500_000,
    ]


def test_adapter_uses_default_volume_when_missing():
    data = make_provider_data()
    data.pop("current_volume")

    frame = MarketDataAdapter.to_dataframe(data)

    assert frame["volume"].tolist() == [
        1_000_000,
        1_000_000,
        1_000_000,
    ]


@pytest.mark.parametrize(
    "missing_field",
    ["highs", "lows", "closes"],
)
def test_adapter_rejects_missing_required_fields(
    missing_field: str,
):
    data = make_provider_data()
    data.pop(missing_field)

    with pytest.raises(
        ValueError,
        match=f"Missing required field: {missing_field}",
    ):
        MarketDataAdapter.to_dataframe(data)


def test_adapter_rejects_unequal_array_lengths():
    data = make_provider_data()
    data["highs"] = [101.0, 102.0]

    with pytest.raises(
        ValueError,
        match="must have equal length",
    ):
        MarketDataAdapter.to_dataframe(data)