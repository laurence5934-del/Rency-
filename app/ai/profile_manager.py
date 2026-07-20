from __future__ import annotations

from app.ai.ranking_profiles import (
    RankingProfile,
    RankingProfiles,
)


class ProfileManager:
    """
    Provides access to built-in AI ranking profiles.
    """

    def __init__(self) -> None:
        self._profiles = {
            profile.name.lower(): profile
            for profile in RankingProfiles.all()
        }

    def get(
        self,
        name: str,
    ) -> RankingProfile:
        if not isinstance(name, str):
            raise TypeError(
                "name must be a string."
            )

        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "name cannot be empty."
            )

        try:
            return self._profiles[normalized_name]
        except KeyError as exc:
            available = ", ".join(self.names())

            raise ValueError(
                f"Unknown ranking profile: {name}. "
                f"Available profiles: {available}."
            ) from exc

    def growth(self) -> RankingProfile:
        return self.get("growth")

    def swing(self) -> RankingProfile:
        return self.get("swing")

    def income(self) -> RankingProfile:
        return self.get("income")

    def conservative(self) -> RankingProfile:
        return self.get("conservative")

    def breakout(self) -> RankingProfile:
        return self.get("breakout")

    def all(self) -> tuple[RankingProfile, ...]:
        return tuple(self._profiles.values())

    def names(self) -> tuple[str, ...]:
        return tuple(
            profile.name
            for profile in self.all()
        )

    def exists(
        self,
        name: str,
    ) -> bool:
        if not isinstance(name, str):
            return False

        return name.strip().lower() in self._profiles