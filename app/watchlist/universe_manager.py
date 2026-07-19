from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from app.watchlist.universe_models import SymbolUniverse


class UniverseManager:
    """
    Create, load, register, combine, and retrieve symbol universes.

    The manager does not download live index constituents. It manages
    deterministic symbol collections supplied by the application or user.
    """

    def __init__(self) -> None:
        self._universes: dict[str, SymbolUniverse] = {}

    def create(
        self,
        name: str,
        symbols: Iterable[str],
        *,
        description: str = "",
        source: str = "custom",
        register: bool = True,
    ) -> SymbolUniverse:
        normalized_symbols = self.normalize_symbols(
            symbols
        )

        universe = SymbolUniverse(
            name=name.strip(),
            symbols=tuple(normalized_symbols),
            description=description.strip(),
            source=source.strip(),
        )

        if register:
            self.register(universe)

        return universe

    def register(
        self,
        universe: SymbolUniverse,
        *,
        replace: bool = False,
    ) -> None:
        if not isinstance(universe, SymbolUniverse):
            raise TypeError(
                "universe must be a SymbolUniverse."
            )

        key = self._normalize_name(universe.name)

        if key in self._universes and not replace:
            raise ValueError(
                f"Universe already registered: {universe.name}"
            )

        self._universes[key] = universe

    def get(
        self,
        name: str,
    ) -> SymbolUniverse:
        key = self._normalize_name(name)

        try:
            return self._universes[key]
        except KeyError as exc:
            raise KeyError(
                f"Unknown universe: {name}"
            ) from exc

    def remove(
        self,
        name: str,
    ) -> SymbolUniverse:
        key = self._normalize_name(name)

        try:
            return self._universes.pop(key)
        except KeyError as exc:
            raise KeyError(
                f"Unknown universe: {name}"
            ) from exc

    def names(self) -> tuple[str, ...]:
        return tuple(
            universe.name
            for universe in self._universes.values()
        )

    def combine(
        self,
        name: str,
        universes: Iterable[SymbolUniverse],
        *,
        description: str = "",
        register: bool = True,
    ) -> SymbolUniverse:
        universe_list = list(universes)

        if not universe_list:
            raise ValueError(
                "At least one universe is required."
            )

        combined_symbols: list[str] = []

        for universe in universe_list:
            if not isinstance(universe, SymbolUniverse):
                raise TypeError(
                    "Every item must be a SymbolUniverse."
                )

            combined_symbols.extend(
                universe.symbols
            )

        return self.create(
            name=name,
            symbols=combined_symbols,
            description=description,
            source="combined",
            register=register,
        )

    def exclude(
        self,
        universe: SymbolUniverse,
        symbols: Iterable[str],
        *,
        name: str | None = None,
        register: bool = False,
    ) -> SymbolUniverse:
        if not isinstance(universe, SymbolUniverse):
            raise TypeError(
                "universe must be a SymbolUniverse."
            )

        excluded_symbols = set(
            self.normalize_symbols(symbols)
        )

        remaining_symbols = [
            symbol
            for symbol in universe.symbols
            if symbol not in excluded_symbols
        ]

        return self.create(
            name=name or universe.name,
            symbols=remaining_symbols,
            description=universe.description,
            source=f"{universe.source}:filtered",
            register=register,
        )

    def load_text(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        description: str = "",
        register: bool = True,
    ) -> SymbolUniverse:
        file_path = Path(path)

        self._validate_file(
            file_path,
            expected_suffixes={".txt"},
        )

        symbols: list[str] = []

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                clean_line = line.strip()

                if not clean_line:
                    continue

                if clean_line.startswith("#"):
                    continue

                symbols.extend(
                    part.strip()
                    for part in clean_line.split(",")
                )

        return self.create(
            name=name or file_path.stem,
            symbols=symbols,
            description=description,
            source=str(file_path),
            register=register,
        )

    def load_csv(
        self,
        path: str | Path,
        *,
        symbol_column: str = "symbol",
        name: str | None = None,
        description: str = "",
        register: bool = True,
    ) -> SymbolUniverse:
        file_path = Path(path)

        self._validate_file(
            file_path,
            expected_suffixes={".csv"},
        )

        symbols: list[str] = []

        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError(
                    "CSV file must contain a header row."
                )

            normalized_headers = {
                header.strip().lower(): header
                for header in reader.fieldnames
                if header is not None
            }

            requested_column = (
                symbol_column.strip().lower()
            )

            actual_column = normalized_headers.get(
                requested_column
            )

            if actual_column is None:
                raise ValueError(
                    "CSV file does not contain symbol column: "
                    f"{symbol_column}"
                )

            for row in reader:
                value = row.get(actual_column)

                if value is not None:
                    symbols.append(value)

        return self.create(
            name=name or file_path.stem,
            symbols=symbols,
            description=description,
            source=str(file_path),
            register=register,
        )

    @classmethod
    def normalize_symbols(
        cls,
        symbols: Iterable[str],
    ) -> list[str]:
        if isinstance(symbols, str):
            symbols = [symbols]

        try:
            symbol_list = list(symbols)
        except TypeError as exc:
            raise TypeError(
                "symbols must be an iterable of strings."
            ) from exc

        normalized: list[str] = []
        seen: set[str] = set()

        for symbol in symbol_list:
            clean_symbol = cls.normalize_symbol(
                symbol
            )

            if clean_symbol not in seen:
                normalized.append(clean_symbol)
                seen.add(clean_symbol)

        return normalized

    @staticmethod
    def normalize_symbol(
        symbol: str,
    ) -> str:
        if not isinstance(symbol, str):
            raise TypeError(
                "Every symbol must be a string."
            )

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError(
                "Symbols cannot be empty."
            )

        return normalized_symbol

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:
        if not isinstance(name, str):
            raise TypeError(
                "Universe name must be a string."
            )

        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "Universe name cannot be empty."
            )

        return normalized_name

    @staticmethod
    def _validate_file(
        path: Path,
        *,
        expected_suffixes: set[str],
    ) -> None:
        if not path.exists():
            raise FileNotFoundError(
                f"Universe file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Universe path is not a file: {path}"
            )

        if path.suffix.lower() not in expected_suffixes:
            expected = ", ".join(
                sorted(expected_suffixes)
            )

            raise ValueError(
                f"Expected universe file type: {expected}"
            )