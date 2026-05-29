from __future__ import annotations

from typing import Any

from or_model.cost_matrix import ProblemInstance, build_problem, minutes_between
from or_model.data_loader import ORDataStore
from or_model.tsp_solver import solve_tsp


def optimize_trip(
    request: dict[str, Any],
    data_dir: str | None = None,
) -> dict[str, Any]:
    """Run the itinerary optimizer for one trip request payload.

    Args:
        request: Dict matching schemas/trip_request.json (example instance).
        data_dir: Optional override for data/OR_data path.

    Returns:
        Structured result with visit order, legs, totals, and constraint checks.
    """
    data = ORDataStore.load(data_dir)

    attraction_ids = [a["attraction_id"] for a in request["attractions"]]
    stay_map = {a["attraction_id"]: int(a["stay_minutes"]) for a in request["attractions"]}

    problem = build_problem(
        data=data,
        attraction_ids=attraction_ids,
        stay_minutes=stay_map,
        start_station_id=request["start_station_id"],
        end_station_id=request["end_station_id"],
        trip_date=request["trip_date"],
        day_type=request["day_type"],
        start_time=request["start_time"],
        preferences=request.get("preferences", {}),
    )

    tsp = solve_tsp(problem)
    legs_out: list[dict[str, Any]] = []
    total_travel_min = 0.0
    total_fare = 0
    total_stay = sum(stay_map[aid] for aid in attraction_ids)

    visit_order: list[str] = []
    for idx in tsp.order:
        label = problem.labels[idx]
        if label.startswith("P"):
            visit_order.append(label)

    for a, b in zip(tsp.order[:-1], tsp.order[1:]):
        leg = problem.legs.get((a, b))
        if leg is None:
            return _infeasible_response(
                request,
                reason=f"No feasible metro leg: {problem.labels[a]} -> {problem.labels[b]}",
            )
        total_travel_min += leg.total_time_min
        total_fare += leg.fare_yen
        legs_out.append(
            {
                "from": leg.from_label,
                "to": leg.to_label,
                "from_station_id": leg.from_station_id,
                "to_station_id": leg.to_station_id,
                "walk_time_min": round(leg.walk_time_min, 2),
                "metro_time_min": round(leg.metro_time_min, 2),
                "wait_time_min": round(leg.wait_time_min, 2),
                "transfer_count": leg.transfer_count,
                "fare_yen": leg.fare_yen,
                "crowd_score": round(leg.crowd_score, 4),
                "rain_penalty_min": round(leg.rain_penalty_min, 2),
                "outdoor_penalty_min": round(leg.outdoor_penalty_min, 2),
                "transfer_penalty_min": round(leg.transfer_penalty_min, 2),
                "total_leg_time_min": round(leg.total_time_min, 2),
                "route_path": leg.route_path,
            }
        )

    time_budget = minutes_between(request["start_time"], request["end_time"])
    total_time = total_travel_min + total_stay
    budget_yen = int(request["budget_yen"])

    binding: list[str] = []
    if total_time > time_budget:
        binding.append("time")
    if total_fare > budget_yen:
        binding.append("budget")

    status = "optimal" if not binding else "optimal_with_violation"

    names = {
        row["attraction_id"]: row["attraction_name"]
        for _, row in data.attractions[
            data.attractions["attraction_id"].isin(attraction_ids)
        ].iterrows()
    }

    return {
        "request_id": request.get("request_id"),
        "status": status,
        "solver": tsp.method,
        "ordered_attraction_ids": visit_order,
        "ordered_attraction_names": [names.get(aid, aid) for aid in visit_order],
        "legs": legs_out,
        "totals": {
            "travel_time_min": round(total_travel_min, 2),
            "stay_time_min": total_stay,
            "total_time_min": round(total_time, 2),
            "total_fare_yen": total_fare,
            "objective_cost": round(tsp.objective_cost, 2),
        },
        "constraints": {
            "time_budget_min": time_budget,
            "budget_yen": budget_yen,
            "binding": binding,
            "feasible": len(binding) == 0,
        },
        "meta": {
            "day_type": request["day_type"],
            "time_slot_used": problem.time_slot,
            "trip_date": request["trip_date"],
        },
    }


def _infeasible_response(request: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "request_id": request.get("request_id"),
        "status": "infeasible",
        "reason": reason,
        "ordered_attraction_ids": [],
        "legs": [],
    }
