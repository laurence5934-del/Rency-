from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.watchlist.watchlist_exporter import WatchlistExporter
from app.watchlist.watchlist_models import (
    Watchlist,
    WatchlistEntry,
)


def make_watchlist() -> Watchlist:
    return Watchlist(
        name="Morning Watchlist",
        source_symbol_count=5,
        entries=(
            WatchlistEntry(
                rank=1,
                symbol="AAPL",
                last_price=212.50,
                total_score=91.5,
                qualified=True,
                trend_score=20.0,
                momentum_score=18.0,
                volume_score=15.0,
                breakout_score=20.0,
                risk_score=18.5,
                reasons=("Trend", "Breakout"),
            ),
            WatchlistEntry(
                rank=2,
                symbol="MSFT",
                last_price=530.10,
                total_score=88.4,
                qualified=True,
                trend_score=19.0,
                momentum_score=18.0,
                volume_score=14.0,
                breakout_score=19.0,
                risk_score=18.4,
                reasons=("Momentum",),
            ),
        ),
    )


def test_to_dict() -> None:
    exporter = WatchlistExporter()

    payload = exporter.to_dict(make_watchlist())

    assert payload["name"] == "Morning Watchlist"
    assert payload["symbol_count"] == 2
    assert payload["symbols"] == ["AAPL", "MSFT"]


def test_export_csv(tmp_path: Path) -> None:
    exporter = WatchlistExporter()

    output = tmp_path / "watchlist.csv"

    exporter.export_csv(
        make_watchlist(),
        output,
    )

    assert output.exists()

    text = output.read_text(
        encoding="utf-8"
    )

    assert "AAPL" in text
    assert "MSFT" in text
    assert "total_score" in text


def test_export_json(tmp_path: Path) -> None:
    exporter = WatchlistExporter()

    output = tmp_path / "watchlist.json"

    exporter.export_json(
        make_watchlist(),
        output,
    )

    assert output.exists()

    data = json.loads(
        output.read_text(
            encoding="utf-8"
        )
    )

    assert data["name"] == "Morning Watchlist"
    assert data["entries"][0]["symbol"] == "AAPL"


def test_export_creates_parent_directory(
    tmp_path: Path,
) -> None:
    exporter = WatchlistExporter()

    output = (
        tmp_path
        / "exports"
        / "watchlist.json"
    )

    exporter.export_json(
        make_watchlist(),
        output,
    )

    assert output.exists()


def test_export_rejects_existing_file(
    tmp_path: Path,
) -> None:
    exporter = WatchlistExporter()

    output = tmp_path / "watchlist.json"

    output.write_text("{}")

    with pytest.raises(
        FileExistsError,
    ):
        exporter.export_json(
            make_watchlist(),
            output,
        )


def test_export_can_overwrite_existing_file(
    tmp_path: Path,
) -> None:
    exporter = WatchlistExporter()

    output = tmp_path / "watchlist.json"

    output.write_text("{}")

    exporter.export_json(
        make_watchlist(),
        output,
        overwrite=True,
    )

    data = json.loads(
        output.read_text()
    )

    assert data["symbol_count"] == 2


def test_csv_extension_validation() -> None:
    exporter = WatchlistExporter()

    with pytest.raises(
        ValueError,
        match=".csv",
    ):
        exporter.export_csv(
            make_watchlist(),
            "watchlist.json",
        )


def test_json_extension_validation() -> None:
    exporter = WatchlistExporter()

    with pytest.raises(
        ValueError,
        match=".json",
    ):
        exporter.export_json(
            make_watchlist(),
            "watchlist.csv",
        )


def test_negative_indent_rejected(
) -> None:
    exporter = WatchlistExporter()

    with pytest.raises(
        ValueError,
        match="indent",
    ):
        exporter.export_json(
            make_watchlist(),
            "watchlist.json",
            indent=-1,
        )


def test_requires_watchlist() -> None:
    exporter = WatchlistExporter()

    with pytest.raises(
        TypeError,
        match="Watchlist",
    ):
        exporter.to_dict([])  # type: ignore[arg-type]