from __future__ import annotations

from pathlib import Path

import pytest

from app.watchlist.universe_manager import UniverseManager
from app.watchlist.universe_models import SymbolUniverse


def test_create_normalizes_and_deduplicates_symbols() -> None:
    manager = UniverseManager()

    universe = manager.create(
        name="Technology",
        symbols=[
            " aapl ",
            "MSFT",
            "aapl",
            " nvda ",
        ],
    )

    assert universe.symbols == (
        "AAPL",
        "MSFT",
        "NVDA",
    )
    assert universe.symbol_count == 3


def test_create_registers_universe() -> None:
    manager = UniverseManager()

    created = manager.create(
        name="Technology",
        symbols=["AAPL", "MSFT"],
    )

    retrieved = manager.get("technology")

    assert retrieved is created


def test_get_is_case_insensitive() -> None:
    manager = UniverseManager()

    manager.create(
        name="Mega Cap",
        symbols=["AAPL"],
    )

    assert manager.get("MEGA CAP").name == "Mega Cap"


def test_duplicate_registration_is_rejected() -> None:
    manager = UniverseManager()

    manager.create(
        name="Technology",
        symbols=["AAPL"],
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        manager.create(
            name="technology",
            symbols=["MSFT"],
        )


def test_register_can_replace_existing_universe() -> None:
    manager = UniverseManager()

    first = manager.create(
        name="Technology",
        symbols=["AAPL"],
    )

    replacement = SymbolUniverse(
        name="Technology",
        symbols=("MSFT",),
    )

    manager.register(
        replacement,
        replace=True,
    )

    assert manager.get("Technology") is replacement
    assert manager.get("Technology") is not first


def test_combine_universes_removes_duplicates() -> None:
    manager = UniverseManager()

    technology = manager.create(
        name="Technology",
        symbols=["AAPL", "MSFT"],
    )

    growth = manager.create(
        name="Growth",
        symbols=["MSFT", "NVDA"],
    )

    combined = manager.combine(
        name="Combined",
        universes=[
            technology,
            growth,
        ],
    )

    assert combined.symbols == (
        "AAPL",
        "MSFT",
        "NVDA",
    )
    assert combined.source == "combined"


def test_exclude_removes_requested_symbols() -> None:
    manager = UniverseManager()

    universe = manager.create(
        name="Technology",
        symbols=[
            "AAPL",
            "MSFT",
            "NVDA",
        ],
    )

    filtered = manager.exclude(
        universe,
        [" msft "],
        name="Technology Filtered",
    )

    assert filtered.symbols == (
        "AAPL",
        "NVDA",
    )


def test_load_text_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "technology.txt"

    file_path.write_text(
        (
            "# Technology symbols\n"
            "AAPL\n"
            "MSFT, NVDA\n"
            "\n"
            "aapl\n"
        ),
        encoding="utf-8",
    )

    manager = UniverseManager()

    universe = manager.load_text(
        file_path,
    )

    assert universe.name == "technology"
    assert universe.symbols == (
        "AAPL",
        "MSFT",
        "NVDA",
    )


def test_load_csv_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "stocks.csv"

    file_path.write_text(
        (
            "Symbol,Sector\n"
            "AAPL,Technology\n"
            "MSFT,Technology\n"
            "aapl,Technology\n"
        ),
        encoding="utf-8",
    )

    manager = UniverseManager()

    universe = manager.load_csv(
        file_path,
    )

    assert universe.symbols == (
        "AAPL",
        "MSFT",
    )


def test_load_csv_rejects_missing_symbol_column(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "stocks.csv"

    file_path.write_text(
        (
            "Ticker,Sector\n"
            "AAPL,Technology\n"
        ),
        encoding="utf-8",
    )

    manager = UniverseManager()

    with pytest.raises(
        ValueError,
        match="does not contain symbol column",
    ):
        manager.load_csv(
            file_path,
        )


def test_remove_unregisters_universe() -> None:
    manager = UniverseManager()

    universe = manager.create(
        name="Technology",
        symbols=["AAPL"],
    )

    removed = manager.remove(
        "technology"
    )

    assert removed is universe

    with pytest.raises(
        KeyError,
        match="Unknown universe",
    ):
        manager.get("technology")


def test_names_returns_registered_universe_names() -> None:
    manager = UniverseManager()

    manager.create(
        name="Technology",
        symbols=["AAPL"],
    )
    manager.create(
        name="ETFs",
        symbols=["SPY"],
    )

    assert manager.names() == (
        "Technology",
        "ETFs",
    )


def test_contains_normalizes_requested_symbol() -> None:
    universe = SymbolUniverse(
        name="Technology",
        symbols=(
            "AAPL",
            "MSFT",
        ),
    )

    assert universe.contains(" aapl ")
    assert not universe.contains("NVDA")


def test_create_rejects_empty_symbol() -> None:
    manager = UniverseManager()

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        manager.create(
            name="Invalid",
            symbols=["AAPL", " "],
        )