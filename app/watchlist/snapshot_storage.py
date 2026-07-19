from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.watchlist.snapshot_models import WatchlistSnapshot
from app.watchlist.watchlist_models import Watchlist, WatchlistEntry


class SnapshotStorage:
    """
    Save, load, list, and delete watchlist snapshots as JSON files.
    """

    def __init__(self, storage_directory: str | Path) -> None:
        self.storage_directory = Path(storage_directory)

    def save(
        self,
        snapshot: WatchlistSnapshot,
        *,
        overwrite: bool = False,
    ) -> Path:
        """
        Save a snapshot to disk and return the resulting file path.
        """

        self._validate_snapshot(snapshot)
        self.storage_directory.mkdir(parents=True, exist_ok=True)

        output_path = self._snapshot_path(snapshot.snapshot_id)

        if output_path.exists() and not overwrite:
            raise FileExistsError(
                f"Snapshot already exists: {output_path}"
            )

        payload = self._snapshot_to_dict(snapshot)

        output_path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return output_path

    def load(self, snapshot_id: str) -> WatchlistSnapshot:
        """
        Load one snapshot by its snapshot ID.
        """

        self._validate_snapshot_id(snapshot_id)

        input_path = self._snapshot_path(snapshot_id)

        if not input_path.exists():
            raise FileNotFoundError(
                f"Snapshot not found: {snapshot_id}"
            )

        payload = json.loads(
            input_path.read_text(encoding="utf-8")
        )

        return self._snapshot_from_dict(payload)

    def list_snapshot_ids(self) -> tuple[str, ...]:
        """
        Return all stored snapshot IDs in filename order.
        """

        if not self.storage_directory.exists():
            return ()

        return tuple(
            path.stem
            for path in sorted(
                self.storage_directory.glob("*.json")
            )
        )

    def list_snapshots(self) -> tuple[WatchlistSnapshot, ...]:
        """
        Load all snapshots ordered by creation time.
        """

        snapshots = tuple(
            self.load(snapshot_id)
            for snapshot_id in self.list_snapshot_ids()
        )

        return tuple(
            sorted(
                snapshots,
                key=lambda snapshot: snapshot.created_at,
            )
        )

    def latest(self) -> WatchlistSnapshot | None:
        """
        Return the newest snapshot, or None when storage is empty.
        """

        snapshots = self.list_snapshots()

        if not snapshots:
            return None

        return snapshots[-1]

    def delete(self, snapshot_id: str) -> None:
        """
        Delete one stored snapshot.
        """

        self._validate_snapshot_id(snapshot_id)

        snapshot_path = self._snapshot_path(snapshot_id)

        if not snapshot_path.exists():
            raise FileNotFoundError(
                f"Snapshot not found: {snapshot_id}"
            )

        snapshot_path.unlink()

    def exists(self, snapshot_id: str) -> bool:
        """
        Return True when the specified snapshot exists.
        """

        self._validate_snapshot_id(snapshot_id)
        return self._snapshot_path(snapshot_id).exists()

    def _snapshot_path(self, snapshot_id: str) -> Path:
        self._validate_snapshot_id(snapshot_id)

        return self.storage_directory / f"{snapshot_id}.json"

    @staticmethod
    def _snapshot_to_dict(
        snapshot: WatchlistSnapshot,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": snapshot.snapshot_id,
            "created_at": snapshot.created_at.isoformat(),
            "version": snapshot.version,
            "notes": snapshot.notes,
            "watchlist": {
                "name": snapshot.watchlist.name,
                "source_symbol_count": (
                    snapshot.watchlist.source_symbol_count
                ),
                "created_at": (
                    snapshot.watchlist.created_at.isoformat()
                ),
                "entries": [
                    SnapshotStorage._entry_to_dict(entry)
                    for entry in snapshot.watchlist.entries
                ],
            },
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

    @staticmethod
    def _snapshot_from_dict(
        payload: dict[str, Any],
    ) -> WatchlistSnapshot:
        watchlist_payload = payload["watchlist"]

        entries = tuple(
            SnapshotStorage._entry_from_dict(entry_payload)
            for entry_payload in watchlist_payload["entries"]
        )

        watchlist = Watchlist(
            name=watchlist_payload["name"],
            entries=entries,
            source_symbol_count=(
                watchlist_payload["source_symbol_count"]
            ),
            created_at=datetime.fromisoformat(
                watchlist_payload["created_at"]
            ),
        )

        return WatchlistSnapshot(
            watchlist=watchlist,
            snapshot_id=payload["snapshot_id"],
            created_at=datetime.fromisoformat(
                payload["created_at"]
            ),
            version=payload["version"],
            notes=payload.get("notes", ""),
        )

    @staticmethod
    def _entry_from_dict(
        payload: dict[str, Any],
    ) -> WatchlistEntry:
        return WatchlistEntry(
            rank=payload["rank"],
            symbol=payload["symbol"],
            last_price=payload["last_price"],
            total_score=payload["total_score"],
            qualified=payload["qualified"],
            trend_score=payload["trend_score"],
            momentum_score=payload["momentum_score"],
            volume_score=payload["volume_score"],
            breakout_score=payload["breakout_score"],
            risk_score=payload["risk_score"],
            reasons=tuple(payload.get("reasons", [])),
        )

    @staticmethod
    def _validate_snapshot(
        snapshot: WatchlistSnapshot,
    ) -> None:
        if not isinstance(snapshot, WatchlistSnapshot):
            raise TypeError(
                "snapshot must be a WatchlistSnapshot."
            )

    @staticmethod
    def _validate_snapshot_id(snapshot_id: str) -> None:
        if not isinstance(snapshot_id, str):
            raise TypeError(
                "snapshot_id must be a string."
            )

        if not snapshot_id.strip():
            raise ValueError(
                "snapshot_id cannot be empty."
            )

        if Path(snapshot_id).name != snapshot_id:
            raise ValueError(
                "snapshot_id cannot contain path separators."
            )