from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DashboardSection:
    title: str
    metrics: dict[str, str]


@dataclass(frozen=True, slots=True)
class AnalyticsDashboard:
    sections: tuple[DashboardSection, ...]