from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class SymbolUniverse:
    """
    A normalized collection of unique market symbols.
    """

    name: str
    symbols: tuple[str, ...]
    description: str = ""
    source: str = "custom"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "Universe name cannot be empty."
            )

        if not self.source.strip():
            raise ValueError(
                "Universe source cannot be empty."
            )

        if len(set(self.symbols)) != len(self.symbols):
            raise ValueError(
                "Universe symbols must be unique."
            )

        for symbol in self.symbols:
            if not isinstance(symbol, str):
                raise TypeError(
                    "Every universe symbol must be a string."
                )

            if not symbol.strip():
                raise ValueError(
                    "Universe symbols cannot be empty."
                )

            if symbol != symbol.strip().upper():
                raise ValueError(
                    "Universe symbols must be normalized."
                )

    @property
    def symbol_count(self) -> int:
        return len(self.symbols)

    def contains(self, symbol: str) -> bool:
        normalized_symbol = symbol.strip().upper()
        return normalized_symbol in self.symbols