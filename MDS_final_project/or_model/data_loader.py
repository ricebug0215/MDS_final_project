from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "OR_data"

OUTDOOR_CATEGORIES = frozenset(
    {
        "park",
        "zoo",
        "garden",
        "shrine",
        "temple",
        "observation_deck",
        "amusement_park",
        "beach",
        "natural_feature",
    }
)


@dataclass
class ORDataStore:
    """Loaded static CSV reference tables for one optimization run."""

    attractions: pd.DataFrame
    access: pd.DataFrame
    routes: pd.DataFrame
    fares: pd.DataFrame
    crowd: pd.DataFrame
    frequency: pd.DataFrame
    weather: pd.DataFrame

    @classmethod
    def load(cls, data_dir: Path | str | None = None) -> ORDataStore:
        root = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
        return cls(
            attractions=pd.read_csv(root / "attractions.csv"),
            access=pd.read_csv(root / "attraction_station_access.csv"),
            routes=pd.read_csv(root / "station_pair_routes.csv"),
            fares=pd.read_csv(root / "station_pair_fares.csv"),
            crowd=pd.read_csv(root / "station_crowd_by_time.csv"),
            frequency=pd.read_csv(root / "train_frequency_by_time.csv"),
            weather=pd.read_csv(root / "weather_daily.csv"),
        )

    def route_lookup(self) -> dict[tuple[str, str], Any]:
        if not hasattr(self, "_route_lookup"):
            lookup: dict[tuple[str, str], Any] = {}
            for row in self.routes.itertuples(index=False):
                lookup[(row.from_station_id, row.to_station_id)] = row
            self._route_lookup = lookup  # type: ignore[attr-defined]
        return self._route_lookup  # type: ignore[attr-defined]

    def fare_lookup(self) -> dict[tuple[str, str], int]:
        if not hasattr(self, "_fare_lookup"):
            self._fare_lookup = {  # type: ignore[attr-defined]
                (row.from_station_id, row.to_station_id): int(row.fare_yen)
                for row in self.fares.itertuples(index=False)
            }
        return self._fare_lookup  # type: ignore[attr-defined]

    def access_for(self, attraction_id: str) -> pd.Series:
        rows = self.access[self.access["attraction_id"] == attraction_id]
        if rows.empty:
            raise ValueError(f"Unknown attraction_id: {attraction_id}")
        return rows.iloc[0]

    def attraction_row(self, attraction_id: str) -> pd.Series:
        rows = self.attractions[self.attractions["attraction_id"] == attraction_id]
        if rows.empty:
            raise ValueError(f"Unknown attraction_id: {attraction_id}")
        return rows.iloc[0]

    def weather_for(self, trip_date: str) -> pd.Series | None:
        rows = self.weather[self.weather["date"] == trip_date]
        if rows.empty:
            return None
        return rows.iloc[0]

    def crowd_score(
        self, station_id: str, day_type: str, time_slot: str
    ) -> float:
        rows = self.crowd[
            (self.crowd["station_id"] == station_id)
            & (self.crowd["day_type"] == day_type)
            & (self.crowd["time_slot"] == time_slot)
        ]
        if rows.empty:
            return 0.0
        return float(rows["crowd_score"].mean())

    def wait_minutes(
        self, station_id: str, day_type: str, time_slot: str
    ) -> float:
        rows = self.frequency[
            (self.frequency["station_id"] == station_id)
            & (self.frequency["day_type"] == day_type)
            & (self.frequency["time_slot"] == time_slot)
        ]
        if rows.empty:
            return 0.0
        return float(rows["avg_wait_time_min"].mean())
