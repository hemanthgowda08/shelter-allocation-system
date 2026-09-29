"""Run the deterministic, synthetic Phase 1 example from the repository root."""

from .model import ShelterAllocationOptimizer
from .priority import priority_label
from .sample_data import build_synthetic_scenario


def main() -> None:
    groups, shelters, distances = build_synthetic_scenario()
    result = ShelterAllocationOptimizer().solve(groups, shelters, distances)

    print("Emergency Shelter Allocation — synthetic demonstration data")
    print(f"Solver status: {result.status}")
    print("\nAllocations")
    for allocation in result.allocations:
        print(
            f"- {allocation.group_name} -> {allocation.shelter_name}: {allocation.people} people "
            f"({allocation.distance:.1f} distance units; {priority_label(allocation.priority)} priority)"
        )

    metrics = result.metrics
    print("\nMetrics")
    print(f"- Total people: {metrics.total_people}")
    print(f"- Allocated people: {metrics.allocated_people}")
    print(f"- Unallocated people: {metrics.unallocated_people}")
    print(f"- Total travel distance: {metrics.total_travel_distance:.1f} person-distance units")
    print(f"- Average travel distance: {metrics.average_travel_distance:.2f} distance units/person")
    print(f"- Capacity violations: {len(metrics.capacity_violations)}")
    print(f"- Runtime: {metrics.runtime_ms:.2f} ms")
    print("\nShelter utilization")
    for utilization in metrics.shelter_utilization:
        print(
            f"- {utilization.shelter_name}: {utilization.allocated_people}/"
            f"{utilization.remaining_capacity} newly allocated "
            f"({utilization.utilization:.1%})"
        )
    if metrics.unmet_requirements:
        print("\nUnmet requirements")
        for explanation in metrics.unmet_requirements:
            print(f"- {explanation}")


if __name__ == "__main__":
    main()
