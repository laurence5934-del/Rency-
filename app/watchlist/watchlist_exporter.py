from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.watchlist.watchlist_models import Watchlist, WatchlistEntry


class WatchlistExporter:
    """
    Export Watchlist objects to CSV and JSON files.
    """

    CSV_FIELDNAMES = (
        "rank",
        "symbol",
        "last_price",
        "total_score",
        "qualified",
        "trend_score",
        "momentum_score",
        "volume_score",
        "breakout_score",
        "risk_score",
        "reasons",
    )

    def export_csv(
        self,
        watchlist: Watchlist,
        path: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        self._validate_watchlist(watchlist)

        file_path = self._prepare_output_path(
            path,
            expected_suffix=".csv",
            overwrite=overwrite,
        )

        with file_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=self.CSV_FIELDNAMES,
            )
            writer.writeheader()

            for entry in watchlist.entries:
                writer.writerow(
                    self._entry_to_csv_row(entry)
                )

        return file_path

    def export_json(
        self,
        watchlist: Watchlist,
        path: str | Path,
        *,
        overwrite: bool = False,
        indent: int = 2,
    ) -> Path:
        self._validate_watchlist(watchlist)

        if indent < 0:
            raise ValueError(
                "indent cannot be negative."
            )

        file_path = self._prepare_output_path(
            path,
            expected_suffix=".json",
            overwrite=overwrite,
        )

        payload = self.to_dict(watchlist)

        with file_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                indent=indent,
                ensure_ascii=False,
            )
            file.write("\n")

        return file_path

    def to_dict(
        self,
        watchlist: Watchlist,
    ) -> dict[str, Any]:
        self._validate_watchlist(watchlist)

        return {
            "name": watchlist.name,
            "created_at": watchlist.created_at.isoformat(),
            "source_symbol_count": watchlist.source_symbol_count,
            "symbol_count": watchlist.symbol_count,
            "symbols": list(watchlist.symbols),
            "entries": [
                self._entry_to_dict(entry)
                for entry in watchlist.entries
            ],
        }

    @staticmethod
    def _entry_to_dict(
        entry: WatchlistEntry,
    ) -> dict[str, Any]:
        return {
            "rank": entry.rank,
            "symbol": entry.symbol,
            "last_price": entry.last_price,
            "total_score": entry.total_score,
            "qualified": entry.qualified,
            "trend_score": entry.trend_score,
            "momentum_score": entry.momentum_score,
            "volume_score": entry.volume_score,
            "breakout_score": entry.breakout_score,
            "risk_score": entry.risk_score,
            "reasons": list(entry.reasons),
        }

    @classmethod
    def _entry_to_csv_row(
        cls,
        entry: WatchlistEntry,
    ) -> dict[str, Any]:
        row = cls._entry_to_dict(entry)
        row["reasons"] = " | ".join(entry.reasons)
        return row

    @staticmethod
    def _validate_watchlist(
        watchlist: Watchlist,
    ) -> None:
        if not isinstance(watchlist, Watchlist):
            raise TypeError(
                "watchlist must be a Watchlist."
            )

    @staticmethod
    def _prepare_output_path(
        path: str | Path,
        *,
        expected_suffix: str,
        overwrite: bool,
    ) -> Path:
        file_path = Path(path)

        if file_path.suffix.lower() != expected_suffix:
            raise ValueError(
                f"Expected output file type: {expected_suffix}"
            )

        if file_path.exists() and file_path.is_dir():
            raise ValueError(
                f"Output path is a directory: {file_path}"
            )

        if file_path.exists() and not overwrite:
            raise FileExistsError(
                f"Output file already exists: {file_path}"
            )

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return file_path