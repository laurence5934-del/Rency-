from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.watchlist.snapshot_manager import SnapshotManager
from app.watchlist.snapshot_models import WatchlistSnapshot
from app.watchlist.snapshot_storage import SnapshotStorage
from app.watchlist.watchlist_models import (
    Watchlist,
    WatchlistEntry,
)


def make_entry(
    rank: int,
    symbol: str,
    score: float,
    *,
    price: float = 100.0,
) -> WatchlistEntry:
    return WatchlistEntry(
        rank=rank,
        symbol=symbol,
        last_price=price,
        total_score=score,
        qualified=True,
        trend_score=20.0,
        momentum_score=15.0,
        volume_score=10.0,
        breakout_score=10.0,
        risk_score=5.0,
        reasons=("test reason",),
    )


def make_watchlist(
    name: str = "Test Watchlist",
    entries: list[WatchlistEntry] | None = None,
) -> Watchlist:
    if entries is None:
        entries = [
            make_entry(1, "AAPL", 90.0),
            make_entry(2, "MSFT", 85.0),
        ]

    return Watchlist(
        name=name,
        entries=tuple(entries),
        source_symbol_count=len(entries),
    )


def make_snapshot(
    watchlist: Watchlist,
    snapshot_id: str,
    created_at: datetime,
    *,
    notes: str = "",
) -> WatchlistSnapshot:
    return WatchlistSnapshot(
        watchlist=watchlist,
        snapshot_id=snapshot_id,
        created_at=created_at,
        notes=notes,
    )


def test_create_snapshot_saves_file(
    tmp_path: Path,
) -> None:
    manager = SnapshotManager(tmp_path)
    watchlist = make_watchlist()

    snapshot = manager.create_snapshot(
        watchlist,
        notes="Daily scan",
    )

    assert isinstance(snapshot, WatchlistSnapshot)
    assert snapshot.watchlist == watchlist
    assert snapshot.notes == "Daily scan"
    assert manager.storage.exists(snapshot.snapshot_id)


def test_load_snapshot_restores_complete_data(
    tmp_path: Path,
) -> None:
    manager = SnapshotManager(tmp_path)

    created = manager.create_snapshot(
        make_watchlist(),
        notes="Morning scan",
    )

    loaded = manager.load_snapshot(created.snapshot_id)

    assert loaded.snapshot_id == created.snapshot_id
    assert loaded.notes == "Morning scan"
    assert loaded.watchlist.name == "Test Watchlist"
    assert loaded.symbols == ("AAPL", "MSFT")
    assert loaded.symbol_count == 2
    assert loaded.watchlist.entries[0].reasons == (
        "test reason",
    )


def test_latest_snapshot_returns_none_when_empty(
    tmp_path: Path,
) -> None:
    manager = SnapshotManager(tmp_path)

    assert manager.latest_snapshot() is None


def test_latest_snapshot_returns_newest_snapshot(
    tmp_path: Path,
) -> None:
    storage = SnapshotStorage(tmp_path)
    manager = SnapshotManager(tmp_path)

    older = make_snapshot(
        make_watchlist("Older"),
        "older-snapshot",
        datetime(
            2026,
            1,
            1,
            9,
            0,
            tzinfo=timezone.utc,
        ),
    )

    newer = make_snapshot(
        make_watchlist("Newer"),
        "newer-snapshot",
        datetime(
            2026,
            1,
            2,
            9,
            0,
            tzinfo=timezone.utc,
        ),
    )

    storage.save(newer)
    storage.save(older)

    latest = manager.latest_snapshot()

    assert latest is not None
    assert latest.snapshot_id == "newer-snapshot"


def test_list_snapshots_orders_by_creation_time(
    tmp_path: Path,
) -> None:
    storage = SnapshotStorage(tmp_path)
    manager = SnapshotManager(tmp_path)

    first = make_snapshot(
        make_watchlist("First"),
        "snapshot-first",
        datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )

    second = make_snapshot(
        make_watchlist("Second"),
        "snapshot-second",
        datetime(
            2026,
            1,
            2,
            tzinfo=timezone.utc,
        ),
    )

    storage.save(second)
    storage.save(first)

    snapshots = manager.list_snapshots()

    assert tuple(
        snapshot.snapshot_id
        for snapshot in snapshots
    ) == (
        "snapshot-first",
        "snapshot-second",
    )


def test_compare_snapshots_detects_changes(
    tmp_path: Path,
) -> None:
    storage = SnapshotStorage(tmp_path)
    manager = SnapshotManager(tmp_path)

    previous = make_snapshot(
        make_watchlist(
            "Previous",
            [
                make_entry(1, "AAPL", 90.0),
                make_entry(2, "MSFT", 85.0),
            ],
        ),
        "previous",
        datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )

    current = make_snapshot(
        make_watchlist(
            "Current",
            [
                make_entry(1, "NVDA", 95.0),
                make_entry(2, "AAPL", 92.0),
            ],
        ),
        "current",
        datetime(
            2026,
            1,
            2,
            tzinfo=timezone.utc,
        ),
    )

    storage.save(previous)
    storage.save(current)

    comparison = manager.compare_snapshots(
        "previous",
        "current",
    )

    assert comparison.added_symbols == ("NVDA",)
    assert comparison.removed_symbols == ("MSFT",)

    aapl_change = next(
        change
        for change in comparison.changed
        if change.symbol == "AAPL"
    )

    assert aapl_change.rank_change == -1
    assert aapl_change.score_change == 2.0


def test_compare_latest_uses_two_newest_snapshots(
    tmp_path: Path,
) -> None:
    storage = SnapshotStorage(tmp_path)
    manager = SnapshotManager(tmp_path)

    base_time = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    oldest = make_snapshot(
        make_watchlist(
            "Oldest",
            [make_entry(1, "IBM", 70.0)],
        ),
        "oldest",
        base_time,
    )

    previous = make_snapshot(
        make_watchlist(
            "Previous",
            [make_entry(1, "AAPL", 80.0)],
        ),
        "previous",
        base_time + timedelta(days=1),
    )

    current = make_snapshot(
        make_watchlist(
            "Current",
            [make_entry(1, "NVDA", 95.0)],
        ),
        "current",
        base_time + timedelta(days=2),
    )

    storage.save(current)
    storage.save(oldest)
    storage.save(previous)

    comparison = manager.compare_latest()

    assert comparison.previous_name == "Previous"
    assert comparison.current_name == "Current"
    assert comparison.added_symbols == ("NVDA",)
    assert comparison.removed_symbols == ("AAPL",)


def test_compare_latest_requires_two_snapshots(
    tmp_path: Path,
) -> None:
    manager = SnapshotManager(tmp_path)

    manager.create_snapshot(
        make_watchlist(),
    )

    with pytest.raises(
        ValueError,
        match="At least two snapshots are required",
    ):
        manager.compare_latest()


def test_delete_snapshot_removes_file(
    tmp_path: Path,
) -> None:
    manager = SnapshotManager(tmp_path)

    snapshot = manager.create_snapshot(
        make_watchlist(),
    )

    manager.delete_snapshot(snapshot.snapshot_id)

    assert not manager.storage.exists(
        snapshot.snapshot_id
    )


def test_delete_missing_snapshot_raises_error(
    tmp_path: Path,
) -> None:
    manager = SnapshotManager(tmp_path)

    with pytest.raises(FileNotFoundError):
        manager.delete_snapshot("missing-snapshot")


def test_prune_old_snapshots_keeps_newest(
    tmp_path: Path,
) -> None:
    storage = SnapshotStorage(tmp_path)
    manager = SnapshotManager(tmp_path)

    base_time = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    for index in range(5):
        snapshot = make_snapshot(
            make_watchlist(f"Watchlist {index}"),
            f"snapshot-{index}",
            base_time + timedelta(days=index),
        )
        storage.save(snapshot)

    deleted_count = manager.prune_old_snapshots(
        keep_last=2,
    )

    remaining = manager.list_snapshots()

    assert deleted_count == 3
    assert tuple(
        snapshot.snapshot_id
        for snapshot in remaining
    ) == (
        "snapshot-3",
        "snapshot-4",
    )


def test_prune_returns_zero_when_no_cleanup_needed(
    tmp_path: Path,
) -> None:
    manager = SnapshotManager(tmp_path)

    manager.create_snapshot(make_watchlist())

    deleted_count = manager.prune_old_snapshots(
        keep_last=3,
    )

    assert deleted_count == 0


@pytest.mark.parametrize(
    "keep_last",
    [0, -1, -10],
)
def test_prune_rejects_invalid_keep_last(
    tmp_path: Path,
    keep_last: int,
) -> None:
    manager = SnapshotManager(tmp_path)

    with pytest.raises(
        ValueError,
        match="keep_last must be at least 1",
    ):
        manager.prune_old_snapshots(keep_last)


def test_snapshot_date_uses_created_at_date() -> None:
    snapshot = make_snapshot(
        make_watchlist(),
        "dated-snapshot",
        datetime(
            2026,
            7,
            19,
            15,
            30,
            tzinfo=timezone.utc,
        ),
    )

    assert snapshot.snapshot_date == "2026-07-19"


def test_snapshot_requires_watchlist() -> None:
    with pytest.raises(TypeError):
        WatchlistSnapshot(
            watchlist="invalid",  # type: ignore[arg-type]
        )


def test_storage_rejects_invalid_snapshot_id(
    tmp_path: Path,
) -> None:
    storage = SnapshotStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.load("../invalid")


def test_storage_rejects_duplicate_without_overwrite(
    tmp_path: Path,
) -> None:
    storage = SnapshotStorage(tmp_path)

    snapshot = make_snapshot(
        make_watchlist(),
        "duplicate",
        datetime.now(timezone.utc),
    )

    storage.save(snapshot)

    with pytest.raises(FileExistsError):
        storage.save(snapshot)


def test_storage_allows_explicit_overwrite(
    tmp_path: Path,
) -> None:
    storage = SnapshotStorage(tmp_path)

    original = make_snapshot(
        make_watchlist("Original"),
        "overwrite-test",
        datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )

    replacement = make_snapshot(
        make_watchlist("Replacement"),
        "overwrite-test",
        datetime(
            2026,
            1,
            2,
            tzinfo=timezone.utc,
        ),
    )

    storage.save(original)
    storage.save(replacement, overwrite=True)

    loaded = storage.load("overwrite-test")

    assert loaded.watchlist.name == "Replacement"