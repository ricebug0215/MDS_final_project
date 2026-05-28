#!/usr/bin/env python3
"""Demo: run the Tokyo tourism OR model on a sample trip request."""

from __future__ import annotations

import json
from pathlib import Path

from or_model import optimize_trip

DEMO_REQUEST = {
    "request_id": "demo-001",
    "trip_date": "2024-06-15",
    "day_type": "holiday",
    "start_time": "09:00",
    "end_time": "18:00",
    "start_station_id": "G16",
    "end_station_id": "G16",
    "attractions": [
        {"attraction_id": "P0001", "stay_minutes": 90, "must_visit": True},
        {"attraction_id": "P0003", "stay_minutes": 60, "must_visit": True},
        {"attraction_id": "P0008", "stay_minutes": 60, "must_visit": True},
    ],
    "budget_yen": 2500,
    "preferences": {
        "time_weight": 0.5,
        "fare_weight": 0.2,
        "crowd_weight": 0.3,
        "avoid_rain": True,
        "rain_penalty_weight": 0.15,
        "max_transfers": 3,
        "include_wait_time": True,
        "allow_skip_attractions": False,
        "prefer_indoor_on_rain": True,
    },
}


def main() -> None:
    result = optimize_trip(DEMO_REQUEST)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    out = Path("output_or_demo.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out.resolve()}")


if __name__ == "__main__":
    main()
