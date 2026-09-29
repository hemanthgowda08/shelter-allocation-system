"""Validated input and output models for the allocation engine.

These classes deliberately use only the Python standard library so that the
optimization logic remains independent from a future web framework or database.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Tuple


class ShelterStatus(str, Enum):
    """Whether a shelter can accept new people in this optimization run."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


def _validate_coordinates(latitude: float, longitude: float, label: str) -> None:
    if not -90 <= latitude <= 90:
        raise ValueError(f"{label} latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError(f"{label} longitude must be between -180 and 180.")


@dataclass(frozen=True)
class AffectedGroup:
    """People at one source location who share a priority and requirements.

    A larger ``priority`` value means the group should be protected first when
    the eligible shelter capacity is insufficient.  Priority must be a
    positive integer; a suggested scale is 1 (standard), 2 (high), 3 (critical).
    """

    id: str
    name: str
    latitude: float
    longitude: float
    people: int
    priority: int = 1
    special_requirements: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id or not self.name:
            raise ValueError("Affected groups need non-empty id and name values.")
        _validate_coordinates(self.latitude, self.longitude, self.name)
        if not isinstance(self.people, int) or self.people < 0:
            raise ValueError(f"{self.name} people must be a non-negative integer.")
        if not isinstance(self.priority, int) or self.priority < 1:
            raise ValueError(f"{self.name} priority must be a positive integer.")


@dataclass(frozen=True)
class Shelter:
    """One potential shelter and the capacity still usable during this run."""

    id: str
    name: str
    latitude: float
    longitude: float
    capacity: int
    current_occupancy: int = 0
    status: ShelterStatus = ShelterStatus.AVAILABLE
    facilities: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id or not self.name:
            raise ValueError("Shelters need non-empty id and name values.")
        _validate_coordinates(self.latitude, self.longitude, self.name)
        if not isinstance(self.capacity, int) or self.capacity < 0:
            raise ValueError(f"{self.name} capacity must be a non-negative integer.")
        if not isinstance(self.current_occupancy, int) or self.current_occupancy < 0:
            raise ValueError(f"{self.name} occupancy must be a non-negative integer.")
        if self.current_occupancy > self.capacity:
            raise ValueError(f"{self.name} occupancy cannot exceed capacity.")

    @property
    def remaining_capacity(self) -> int:
        """Beds/spaces that are available for this allocation run."""

        if self.status != ShelterStatus.AVAILABLE:
            return 0
        return self.capacity - self.current_occupancy


@dataclass(frozen=True)
class ObjectiveConfig:
    """Explicit, configurable weights for the optimization objective.

    ``travel_weight`` is charged once per person-distance unit.  ``imbalance_weight``
    is charged once per unit of the range between the highest and lowest shelter
    utilization (0 to 1).  The protection penalty is calculated from these two
    values and the submitted scenario, rather than guessed as a magic constant.
    This makes one avoidable unallocated person cost more than any possible
    travel/balance improvement.  A higher priority value then has proportionally
    higher protection.
    """

    travel_weight: float = 1.0
    imbalance_weight: float = 10.0

    def __post_init__(self) -> None:
        if self.travel_weight < 0 or self.imbalance_weight < 0:
            raise ValueError("Objective weights cannot be negative.")


@dataclass(frozen=True)
class Allocation:
    """A positive person flow from one affected group to one shelter."""

    group_id: str
    group_name: str
    shelter_id: str
    shelter_name: str
    people: int
    distance: float
    priority: int
    constraints: Tuple[str, ...]


@dataclass(frozen=True)
class ShelterUtilization:
    """Occupancy figures after new allocations have been added."""

    shelter_id: str
    shelter_name: str
    allocated_people: int
    remaining_capacity: int
    utilization: float


@dataclass(frozen=True)
class OptimizationMetrics:
    """Computed evidence for explaining and checking a solver run."""

    total_people: int
    allocated_people: int
    unallocated_people: int
    total_travel_distance: float
    average_travel_distance: float
    shelter_utilization: Tuple[ShelterUtilization, ...]
    capacity_violations: Tuple[str, ...]
    unmet_requirements: Tuple[str, ...]
    objective_value: float
    runtime_ms: float


@dataclass(frozen=True)
class OptimizationResult:
    """The allocation, explanation information, and summary from one solve."""

    status: str
    allocations: Tuple[Allocation, ...]
    unallocated_by_group: Dict[str, int]
    metrics: OptimizationMetrics

