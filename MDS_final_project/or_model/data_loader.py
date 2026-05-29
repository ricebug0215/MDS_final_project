from __future__ import annotations

import heapq
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


@dataclass(frozen=True)
class GraphRoute:
    """Station-to-station route selected from the transit graph."""

    route_path: str
    transfer_count: int
    in_train_time_min: float
    transfer_time_min: float


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
    graph_edges: pd.DataFrame

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
            graph_edges=pd.read_csv(root / "station_graph_edges.csv"),
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

    def graph_adjacency(self) -> dict[str, list[tuple[str, str, float, float]]]:
        if not hasattr(self, "_graph_adjacency"):
            adjacency: dict[str, list[tuple[str, str, float, float]]] = {}
            for row in self.graph_edges.itertuples(index=False):
                from_station = str(row.from_station_id)
                to_station = str(row.to_station_id)
                edge_type = str(row.edge_type).lower()
                base_time = _safe_float(row.base_time_min)
                transfer_time = _safe_float(row.transfer_time_min)
                adjacency.setdefault(from_station, []).append(
                    (to_station, edge_type, base_time, transfer_time)
                )
            self._graph_adjacency = adjacency  # type: ignore[attr-defined]
        return self._graph_adjacency  # type: ignore[attr-defined]

    def shortest_graph_route(
        self,
        from_station_id: str,
        to_station_id: str,
        transfer_penalty_min: float = 0.0,
    ) -> GraphRoute | None:
        """Find a station route, optionally preferring fewer transfer edges."""
        if from_station_id == to_station_id:
            return GraphRoute(
                route_path=f"{from_station_id} (same station)",
                transfer_count=0,
                in_train_time_min=0.0,
                transfer_time_min=0.0,
            )

        cache_key = (from_station_id, to_station_id, round(transfer_penalty_min, 4))
        if not hasattr(self, "_graph_route_cache"):
            self._graph_route_cache = {}  # type: ignore[attr-defined]
        cache: dict[tuple[str, str, float], GraphRoute | None] = (
            self._graph_route_cache  # type: ignore[attr-defined]
        )
        if cache_key in cache:
            return cache[cache_key]

        adjacency = self.graph_adjacency()
        if from_station_id not in adjacency:
            cache[cache_key] = None
            return None

        # State is ordered so equal-cost paths prefer fewer transfers and then
        # fewer station hops. The penalty only guides route choice; actual time
        # is recomputed from base and transfer times when the path is rebuilt.
        start_state = (0.0, 0, 0)
        best: dict[str, tuple[float, int, int]] = {from_station_id: start_state}
        previous: dict[str, tuple[str, str, float, float]] = {}
        heap: list[tuple[float, int, int, str]] = [(0.0, 0, 0, from_station_id)]

        while heap:
            cost, transfer_count, hops, station_id = heapq.heappop(heap)
            if best.get(station_id) != (cost, transfer_count, hops):
                continue
            if station_id == to_station_id:
                route = self._rebuild_graph_route(
                    from_station_id, to_station_id, previous
                )
                cache[cache_key] = route
                return route

            for to_station, edge_type, base_time, transfer_time in adjacency.get(
                station_id, []
            ):
                is_transfer = edge_type == "transfer"
                edge_time = base_time + transfer_time
                next_cost = cost + edge_time
                if is_transfer:
                    next_cost += transfer_penalty_min
                next_state = (
                    next_cost,
                    transfer_count + (1 if is_transfer else 0),
                    hops + 1,
                )
                best_state = best.get(to_station, (float("inf"), 10**9, 10**9))
                if next_state < best_state:
                    best[to_station] = next_state
                    previous[to_station] = (
                        station_id,
                        edge_type,
                        base_time,
                        transfer_time,
                    )
                    heapq.heappush(heap, (*next_state, to_station))

        cache[cache_key] = None
        return None

    def _rebuild_graph_route(
        self,
        from_station_id: str,
        to_station_id: str,
        previous: dict[str, tuple[str, str, float, float]],
    ) -> GraphRoute:
        nodes = [to_station_id]
        station_id = to_station_id
        in_train_time = 0.0
        transfer_time = 0.0
        transfer_count = 0

        while station_id != from_station_id:
            prev_station, edge_type, base_time, edge_transfer_time = previous[
                station_id
            ]
            if edge_type == "transfer":
                transfer_count += 1
                transfer_time += edge_transfer_time
            else:
                in_train_time += base_time
            station_id = prev_station
            nodes.append(station_id)

        nodes.reverse()
        return GraphRoute(
            route_path="→".join(nodes),
            transfer_count=transfer_count,
            in_train_time_min=in_train_time,
            transfer_time_min=transfer_time,
        )

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


def _safe_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)
