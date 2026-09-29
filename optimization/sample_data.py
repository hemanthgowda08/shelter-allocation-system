"""Deterministic, synthetic demonstration scenario for Phase 1.

The names, populations, capacities, locations, and distances in this module
are invented demonstration values.  They are not real disaster data.
"""

from typing import Dict, List, Tuple

from .data_models import AffectedGroup, Shelter, ShelterStatus


def build_synthetic_scenario() -> Tuple[List[AffectedGroup], List[Shelter], Dict[Tuple[str, str], float]]:
    """Return the same realistic-sized synthetic scenario on every call."""

    groups = [
        AffectedGroup(
            id="riverside",
            name="Riverside Ward",
            latitude=12.9716,
            longitude=77.5946,
            people=120,
            priority=3,
            special_requirements=frozenset({"wheelchair_access"}),
        ),
        AffectedGroup(
            id="hillview",
            name="Hillview Colony",
            latitude=12.9352,
            longitude=77.6245,
            people=90,
            priority=2,
        ),
        AffectedGroup(
            id="market",
            name="Market District",
            latitude=12.9600,
            longitude=77.5800,
            people=70,
            priority=1,
        ),
    ]
    shelters = [
        Shelter(
            id="community_hall",
            name="Community Hall",
            latitude=12.9680,
            longitude=77.5900,
            capacity=130,
            current_occupancy=20,
            status=ShelterStatus.AVAILABLE,
            facilities=frozenset({"wheelchair_access", "medical_first_aid"}),
        ),
        Shelter(
            id="high_school",
            name="High School",
            latitude=12.9400,
            longitude=77.6200,
            capacity=100,
            current_occupancy=15,
            status=ShelterStatus.AVAILABLE,
            facilities=frozenset({"medical_first_aid"}),
        ),
        Shelter(
            id="sports_centre",
            name="Sports Centre",
            latitude=12.9550,
            longitude=77.6000,
            capacity=120,
            current_occupancy=20,
            status=ShelterStatus.AVAILABLE,
            facilities=frozenset({"wheelchair_access"}),
        ),
    ]
    distances = {
        ("riverside", "community_hall"): 3.0,
        ("riverside", "high_school"): 8.0,
        ("riverside", "sports_centre"): 6.0,
        ("hillview", "community_hall"): 6.0,
        ("hillview", "high_school"): 2.5,
        ("hillview", "sports_centre"): 5.0,
        ("market", "community_hall"): 4.0,
        ("market", "high_school"): 5.0,
        ("market", "sports_centre"): 3.0,
    }
    return groups, shelters, distances
