from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from or_model.data_loader import ORDataStore, OUTDOOR_CATEGORIES


@dataclass
class LegDetail:
    """One directed move between nodes in the routing graph."""

    from_label: str
    to_label: str
    from_station_id: str
    to_station_id: str
    walk_time_min: float
    metro_time_min: float
    wait_time_min: float
    transfer_count: int
    fare_yen: int
    crowd_score: float
    rain_penalty_min: float
    outdoor_penalty_min: float
    transfer_penalty_min: float
    route_path: str
    objective_cost: float

    @property
    def total_time_min(self) -> float:
        return (
            self.walk_time_min
            + self.metro_time_min
            + self.wait_time_min
            + self.rain_penalty_min
            + self.outdoor_penalty_min
        )


@dataclass
class ProblemInstance:
    """Routing graph for one trip request."""

    labels: list[str]
    attraction_ids: list[str]
    stay_minutes: list[int]
    start_station_id: str
    end_station_id: str
    time_slot: str
    day_type: str
    legs: dict[tuple[int, int], LegDetail] = field(default_factory=dict)
    cost_matrix: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    time_matrix: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    fare_matrix: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))


def time_to_slot(time_hhmm: str) -> str:
    hour, minute = map(int, time_hhmm.split(":"))
    slot_hour = hour if minute < 30 else hour + 1
    slot_hour = min(slot_hour, 23)
    return f"{slot_hour:02d}:00"


def minutes_between(start_hhmm: str, end_hhmm: str) -> int:
    sh, sm = map(int, start_hhmm.split(":"))
    eh, em = map(int, end_hhmm.split(":"))
    return (eh * 60 + em) - (sh * 60 + sm)


def _rain_walk_multiplier(weather_row: Any | None, avoid_rain: bool) -> float:
    if not avoid_rain or weather_row is None:
        return 1.0
    severity = float(weather_row.get("rain_severity", 0.0) or 0.0)
    rain_mm = float(weather_row.get("rain_mm", 0.0) or 0.0)
    if severity <= 0.0 and rain_mm <= 0.0:
        return 1.0
    return 1.0 + min(1.5, severity + rain_mm / 40.0)


def _outdoor_penalty_min(
    category: str | None,
    prefer_indoor_on_rain: bool,
    rain_active: bool,
) -> float:
    if not rain_active or not prefer_indoor_on_rain:
        return 0.0
    if category and str(category).lower() in OUTDOOR_CATEGORIES:
        return 15.0
    return 0.0


def build_problem(
    data: ORDataStore,
    attraction_ids: list[str],
    stay_minutes: dict[str, int],
    start_station_id: str,
    end_station_id: str,
    trip_date: str,
    day_type: str,
    start_time: str,
    preferences: dict[str, Any],
) -> ProblemInstance:
    """Build node labels and weighted cost / time / fare matrices."""
    time_slot = time_to_slot(start_time)
    prefs = preferences
    w_time = float(prefs.get("time_weight", 0.5))
    w_fare = float(prefs.get("fare_weight", 0.2))
    w_crowd = float(prefs.get("crowd_weight", 0.3))
    max_transfers = int(prefs.get("max_transfers", 3))
    route_transfer_penalty = float(
        prefs.get("route_transfer_penalty_min", 20.0 if max_transfers <= 1 else 0.0)
    )
    include_wait = bool(prefs.get("include_wait_time", True))
    avoid_rain = bool(prefs.get("avoid_rain", False))
    prefer_indoor = bool(prefs.get("prefer_indoor_on_rain", True))
    rain_weight = float(prefs.get("rain_penalty_weight", 0.15))

    weather_row = data.weather_for(trip_date)
    rain_mult = _rain_walk_multiplier(weather_row, avoid_rain)
    rain_active = rain_mult > 1.0

    labels = ["__start__", *attraction_ids, "__end__"]
    n = len(labels)
    cost = np.full((n, n), 1_000_000.0, dtype=float)
    time_m = np.zeros((n, n), dtype=float)
    fare_m = np.zeros((n, n), dtype=int)
    legs: dict[tuple[int, int], LegDetail] = {}

    station_of_attr: dict[str, str] = {}
    walk_to_attr: dict[str, float] = {}
    walk_from_attr: dict[str, float] = {}
    category_of: dict[str, str | None] = {}

    for aid in attraction_ids:
        acc = data.access_for(aid)
        att = data.attraction_row(aid)
        station_of_attr[aid] = str(acc["nearest_station_id"])
        walk_min = float(acc["access_walk_time_min"])
        walk_to_attr[aid] = walk_min
        walk_from_attr[aid] = walk_min
        cat = att.get("category")
        category_of[aid] = str(cat) if pd_notna(cat) else None

    route_lookup = data.route_lookup()
    fare_lookup = data.fare_lookup()

    for i, from_label in enumerate(labels):
        for j, to_label in enumerate(labels):
            if i == j:
                continue
            if to_label == "__start__" or from_label == "__end__":
                continue
            leg = _leg_between(
                from_label=from_label,
                to_label=to_label,
                start_station_id=start_station_id,
                end_station_id=end_station_id,
                station_of_attr=station_of_attr,
                walk_to_attr=walk_to_attr,
                walk_from_attr=walk_from_attr,
                category_of=category_of,
                route_lookup=route_lookup,
                fare_lookup=fare_lookup,
                data=data,
                day_type=day_type,
                time_slot=time_slot,
                max_transfers=max_transfers,
                route_transfer_penalty=route_transfer_penalty,
                include_wait=include_wait,
                rain_mult=rain_mult,
                rain_active=rain_active,
                prefer_indoor=prefer_indoor,
                w_time=w_time,
                w_fare=w_fare,
                w_crowd=w_crowd,
                rain_weight=rain_weight,
            )
            if leg is None:
                continue
            legs[(i, j)] = leg
            cost[i, j] = leg.objective_cost
            time_m[i, j] = leg.total_time_min
            fare_m[i, j] = leg.fare_yen

    stay_list = [int(stay_minutes.get(aid, 60)) for aid in attraction_ids]
    return ProblemInstance(
        labels=labels,
        attraction_ids=attraction_ids,
        stay_minutes=stay_list,
        start_station_id=start_station_id,
        end_station_id=end_station_id,
        time_slot=time_slot,
        day_type=day_type,
        legs=legs,
        cost_matrix=cost,
        time_matrix=time_m,
        fare_matrix=fare_m,
    )


def pd_notna(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and np.isnan(value):
        return False
    return str(value).lower() not in {"nan", "none", ""}


def _leg_between(
    from_label: str,
    to_label: str,
    start_station_id: str,
    end_station_id: str,
    station_of_attr: dict[str, str],
    walk_to_attr: dict[str, float],
    walk_from_attr: dict[str, float],
    category_of: dict[str, str | None],
    route_lookup: dict[tuple[str, str], Any],
    fare_lookup: dict[tuple[str, str], int],
    data: ORDataStore,
    day_type: str,
    time_slot: str,
    max_transfers: int,
    route_transfer_penalty: float,
    include_wait: bool,
    rain_mult: float,
    rain_active: bool,
    prefer_indoor: bool,
    w_time: float,
    w_fare: float,
    w_crowd: float,
    rain_weight: float,
) -> LegDetail | None:
    if from_label == "__start__":
        from_station = start_station_id
        walk_out = 0.0
    else:
        from_station = station_of_attr[from_label]
        walk_out = walk_from_attr[from_label] * rain_mult

    if to_label == "__end__":
        to_station = end_station_id
        walk_in = 0.0
    else:
        to_station = station_of_attr[to_label]
        walk_in = walk_to_attr[to_label] * rain_mult

    outdoor_penalty = 0.0
    if to_label not in {"__start__", "__end__"}:
        outdoor_penalty = _outdoor_penalty_min(
            category_of.get(to_label), prefer_indoor, rain_active
        )

    if from_station == to_station:
        route_path = f"{from_station} (same station)"
        transfer_count = 0
        metro_time = 0.0
        fare = 0
    else:
        graph_route = data.shortest_graph_route(
            from_station, to_station, transfer_penalty_min=route_transfer_penalty
        )
        if graph_route is not None:
            transfer_count = graph_route.transfer_count
            metro_time = (
                graph_route.in_train_time_min + graph_route.transfer_time_min
            )
            route_path = graph_route.route_path
        else:
            route = route_lookup.get((from_station, to_station))
            if route is None:
                return None

            transfer_count = int(route.transfer_count)
            metro_time = float(route.in_train_time_min) + float(
                route.transfer_time_min
            )
            route_path = str(route.route_path)

        fare = int(fare_lookup.get((from_station, to_station), 0))
        if metro_time <= 0.0 and fare <= 0:
            return None

    wait_time = (
        data.wait_minutes(from_station, day_type, time_slot) if include_wait else 0.0
    )
    crowd = (
        data.crowd_score(from_station, day_type, time_slot)
        + data.crowd_score(to_station, day_type, time_slot)
    ) / 2.0

    walk_time = walk_out + walk_in
    transfer_soft_penalty = 12.0 * max(0, transfer_count - max_transfers)
    rain_penalty = max(0.0, rain_mult - 1.0) * walk_time * rain_weight * 60.0

    objective = (
        w_time
        * (
            walk_time
            + metro_time
            + wait_time
            + outdoor_penalty
            + transfer_soft_penalty
        )
        + w_fare * fare
        + w_crowd * crowd * 60.0
        + rain_penalty
    )

    return LegDetail(
        from_label=from_label,
        to_label=to_label,
        from_station_id=from_station,
        to_station_id=to_station,
        walk_time_min=walk_time,
        metro_time_min=metro_time,
        wait_time_min=wait_time,
        transfer_count=transfer_count,
        fare_yen=fare,
        crowd_score=crowd,
        rain_penalty_min=rain_penalty,
        outdoor_penalty_min=outdoor_penalty,
        transfer_penalty_min=transfer_soft_penalty,
        route_path=route_path,
        objective_cost=objective,
    )
