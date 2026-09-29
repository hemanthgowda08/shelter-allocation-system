"""Adapter between persisted scenario data and the existing optimizer."""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Any

from optimization.data_models import AffectedGroup, ObjectiveConfig, Shelter, ShelterStatus
from optimization.model import ShelterAllocationOptimizer

from . import db


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def run_optimization(travel_weight: float = 1.0, imbalance_weight: float = 10.0) -> dict[str, Any]:
    raw_groups = db.list_groups()
    raw_shelters = db.list_shelters()
    if not raw_groups or not raw_shelters:
        raise ValueError("Add at least one affected group and one shelter before optimizing.")

    groups = [AffectedGroup(
        id=g["id"], name=g["name"], latitude=g["latitude"], longitude=g["longitude"],
        people=g["people"], priority=g["priority"],
        special_requirements=frozenset(g["special_requirements"]),
    ) for g in raw_groups]
    shelters = [Shelter(
        id=s["id"], name=s["name"], latitude=s["latitude"], longitude=s["longitude"],
        capacity=s["capacity"], current_occupancy=s["current_occupancy"],
        status=ShelterStatus(s["status"]), facilities=frozenset(s["facilities"]),
    ) for s in raw_shelters]

    distances = {(g.id, s.id): haversine_km(g.latitude, g.longitude, s.latitude, s.longitude)
                 for g in groups for s in shelters}
    result = ShelterAllocationOptimizer(
        ObjectiveConfig(travel_weight=travel_weight, imbalance_weight=imbalance_weight)
    ).solve(groups, shelters, distances)
    return serialize_result(result)


def serialize_result(result) -> dict[str, Any]:
    m = result.metrics
    return {
        "status": result.status,
        "allocations": [a.__dict__ for a in result.allocations],
        "unallocated_by_group": result.unallocated_by_group,
        "metrics": {
            "total_people": m.total_people,
            "allocated_people": m.allocated_people,
            "unallocated_people": m.unallocated_people,
            "total_travel_distance": m.total_travel_distance,
            "average_travel_distance": m.average_travel_distance,
            "shelter_utilization": [u.__dict__ for u in m.shelter_utilization],
            "capacity_violations": list(m.capacity_violations),
            "unmet_requirements": list(m.unmet_requirements),
            "objective_value": m.objective_value,
            "runtime_ms": m.runtime_ms,
        },
    }
