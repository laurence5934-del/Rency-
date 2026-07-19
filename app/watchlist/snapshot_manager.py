from __future__ import annotations

from pathlib import Path

from app.watchlist.snapshot_models import WatchlistSnapshot
from app.watchlist.snapshot_storage import SnapshotStorage
from app.watchlist.watchlist_comparator import WatchlistComparator
from app.watchlist.watchlist_comparison_models import (
    WatchlistComparison,
)
from app.watchlist.watchlist_models import Watchlist


class SnapshotManager:
    """
    High-level interface for creating, storing,
    retrieving, comparing, and maintaining
    watchlist snapshots.
    """

    def __init__(self, storage_directory: str | Path):
        self._storage = SnapshotStorage(storage_directory)
        self._comparator = WatchlistComparator()

    @property
    def storage(self) -> SnapshotStorage:
        return self._storage

    def create_snapshot(
        self,
        watchlist: Watchlist,
        *,
        notes: str = "",
        overwrite: bool = False,
    ) -> WatchlistSnapshot:
        """
        Create and immediately save a snapshot.
        """

        snapshot = WatchlistSnapshot(
            watchlist=watchlist,
            notes=notes,
        )

        self._storage.save(
            snapshot,
            overwrite=overwrite,
        )

        return snapshot

    def load_snapshot(
        self,
        snapshot_id: str,
    ) -> WatchlistSnapshot:
        return self._storage.load(snapshot_id)

    def latest_snapshot(self) -> WatchlistSnapshot | None:
        return self._storage.latest()

    def compare_snapshots(
        self,
        previous_snapshot_id: str,
        current_snapshot_id: str,
    ) -> WatchlistComparison:
        previous = self.load_snapshot(previous_snapshot_id)
        current = self.load_snapshot(current_snapshot_id)

        return self._comparator.compare(
            previous.watchlist,
            current.watchlist,
        )

    def compare_latest(
        self,
    ) -> WatchlistComparison:
        snapshots = self._storage.list_snapshots()

        if len(snapshots) < 2:
            raise ValueError(
                "At least two snapshots are required."
            )

        previous = snapshots[-2]
        current = snapshots[-1]

        return self._comparator.compare(
            previous.watchlist,
            current.watchlist,
        )

    def list_snapshots(
        self,
    ) -> tuple[WatchlistSnapshot, ...]:
        return self._storage.list_snapshots()

    def delete_snapshot(
        self,
        snapshot_id: str,
    ) -> None:
        self._storage.delete(snapshot_id)

    def prune_old_snapshots(
        self,
        keep_last: int,
    ) -> int:
        """
        Keep only the newest N snapshots.

        Returns
        -------
        Number of deleted snapshots.
        """

        if keep_last < 1:
            raise ValueError(
                "keep_last must be at least 1."
            )

        snapshots = self._storage.list_snapshots()

        if len(snapshots) <= keep_last:
            return 0

        to_delete = snapshots[:-keep_last]

        for snapshot in to_delete:
            self._storage.delete(
                snapshot.snapshot_id
            )

        return len(to_delete)