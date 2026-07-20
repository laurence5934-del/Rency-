from __future__ import annotations

import pytest

from app.ai.profile_manager import ProfileManager
from app.ai.ranking_engine import RankingEngine
from app.ai.ranking_profiles import (
    RankingProfile,
    RankingProfiles,
)
from app.watchlist.watchlist_models import WatchlistEntry


def make_entry() -> WatchlistEntry:
    return WatchlistEntry(
        rank=1,
        symbol="AAPL",
        last_price=100.0,
        total_score=0.0,
        qualified=True,
        trend_score=80,
        momentum_score=75,
        volume_score=70,
        breakout_score=65,
        risk_score=90,
        reasons=(),
    )


def test_all_profiles_exist() -> None:
    profiles = RankingProfiles.all()

    assert len(profiles) == 5


def test_profile_names() -> None:
    assert RankingProfiles.names() == (
        "Growth",
        "Swing",
        "Income",
        "Conservative",
        "Breakout",
    )


@pytest.mark.parametrize(
    "factory",
    [
        RankingProfiles.growth,
        RankingProfiles.swing,
        RankingProfiles.income,
        RankingProfiles.conservative,
        RankingProfiles.breakout,
    ],
)
def test_weights_sum_to_one(factory) -> None:
    profile = factory()

    weights = profile.config.weights

    total = (
        weights.trend
        + weights.momentum
        + weights.volume
        + weights.breakout
        + weights.risk
    )

    assert total == pytest.approx(1.0)


def test_profile_manager_lookup() -> None:
    manager = ProfileManager()

    profile = manager.get("growth")

    assert profile.name == "Growth"


def test_lookup_is_case_insensitive() -> None:
    manager = ProfileManager()

    profile = manager.get(" GrOwTh ")

    assert profile.name == "Growth"


def test_exists() -> None:
    manager = ProfileManager()

    assert manager.exists("growth")
    assert manager.exists("Growth")
    assert not manager.exists("invalid")


def test_invalid_profile_raises() -> None:
    manager = ProfileManager()

    with pytest.raises(ValueError):
        manager.get("xyz")


def test_empty_name_raises() -> None:
    manager = ProfileManager()

    with pytest.raises(ValueError):
        manager.get("")


def test_non_string_name_raises() -> None:
    manager = ProfileManager()

    with pytest.raises(TypeError):
        manager.get(None)  # type: ignore[arg-type]


def test_all_returns_profiles() -> None:
    manager = ProfileManager()

    profiles = manager.all()

    assert all(
        isinstance(profile, RankingProfile)
        for profile in profiles
    )


@pytest.mark.parametrize(
    "method",
    [
        "growth",
        "swing",
        "income",
        "conservative",
        "breakout",
    ],
)
def test_convenience_methods(method) -> None:
    manager = ProfileManager()

    profile = getattr(manager, method)()

    assert isinstance(profile, RankingProfile)


def test_engine_accepts_profile() -> None:
    manager = ProfileManager()

    engine = RankingEngine(
        config=manager.growth().config,
    )

    result = engine.rank_entry(make_entry())

    assert result.overall_score > 0