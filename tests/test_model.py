"""Tests that verify allocation mathematics and safe edge-case behavior."""

import unittest

from optimization.data_models import AffectedGroup, Shelter, ShelterStatus
from optimization.model import ShelterAllocationOptimizer
from optimization.sample_data import build_synthetic_scenario


class ShelterAllocationOptimizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.optimizer = ShelterAllocationOptimizer()

    def test_no_shelter_exceeds_remaining_capacity(self) -> None:
        groups, shelters, distances = build_synthetic_scenario()
        result = self.optimizer.solve(groups, shelters, distances)
        by_shelter = {utilization.shelter_id: utilization for utilization in result.metrics.shelter_utilization}

        self.assertEqual(result.metrics.capacity_violations, ())
        for shelter in shelters:
            self.assertLessEqual(by_shelter[shelter.id].allocated_people, shelter.remaining_capacity)

    def test_unavailable_shelter_receives_zero_people(self) -> None:
        groups = [AffectedGroup("g1", "Area One", 12.0, 77.0, 50, priority=1)]
        shelters = [
            Shelter("open", "Open Shelter", 12.1, 77.1, 50),
            Shelter("closed", "Closed Shelter", 12.2, 77.2, 100, status=ShelterStatus.UNAVAILABLE),
        ]
        distances = {("g1", "open"): 5.0, ("g1", "closed"): 1.0}
        result = self.optimizer.solve(groups, shelters, distances)

        assigned_to_closed = sum(a.people for a in result.allocations if a.shelter_id == "closed")
        self.assertEqual(assigned_to_closed, 0)
        self.assertEqual(result.metrics.allocated_people, 50)

    def test_special_requirements_exclude_incompatible_shelters(self) -> None:
        groups = [
            AffectedGroup(
                "g1",
                "Wheelchair Support Area",
                12.0,
                77.0,
                30,
                special_requirements=frozenset({"wheelchair_access"}),
            )
        ]
        shelters = [
            Shelter("incompatible", "Incompatible Shelter", 12.1, 77.1, 50),
            Shelter(
                "compatible",
                "Accessible Shelter",
                12.2,
                77.2,
                30,
                facilities=frozenset({"wheelchair_access"}),
            ),
        ]
        distances = {("g1", "incompatible"): 1.0, ("g1", "compatible"): 8.0}
        result = self.optimizer.solve(groups, shelters, distances)

        self.assertEqual(result.allocations[0].shelter_id, "compatible")
        self.assertEqual(result.metrics.allocated_people, 30)

    def test_total_allocated_population_is_correct_when_capacity_is_sufficient(self) -> None:
        groups, shelters, distances = build_synthetic_scenario()
        result = self.optimizer.solve(groups, shelters, distances)

        self.assertEqual(result.metrics.total_people, 280)
        self.assertEqual(result.metrics.allocated_people, 280)
        self.assertEqual(result.metrics.unallocated_people, 0)
        self.assertEqual(result.unallocated_by_group, {})

    def test_solution_is_optimal_and_feasible(self) -> None:
        groups, shelters, distances = build_synthetic_scenario()
        result = self.optimizer.solve(groups, shelters, distances)

        self.assertEqual(result.status, "Optimal")
        self.assertEqual(result.metrics.capacity_violations, ())
        self.assertEqual(
            sum(allocation.people for allocation in result.allocations) + sum(result.unallocated_by_group.values()),
            result.metrics.total_people,
        )

    def test_priority_protects_critical_group_when_capacity_is_short(self) -> None:
        groups = [
            AffectedGroup("critical", "Critical Area", 12.0, 77.0, 50, priority=3),
            AffectedGroup("standard", "Standard Area", 12.1, 77.1, 50, priority=1),
        ]
        shelters = [Shelter("only", "Only Shelter", 12.2, 77.2, 50)]
        distances = {
            ("critical", "only"): 20.0,
            ("standard", "only"): 1.0,
        }
        result = self.optimizer.solve(groups, shelters, distances)
        allocated_by_group = {}
        for allocation in result.allocations:
            allocated_by_group[allocation.group_id] = allocated_by_group.get(allocation.group_id, 0) + allocation.people

        self.assertEqual(allocated_by_group.get("critical", 0), 50)
        self.assertEqual(result.unallocated_by_group, {"standard": 50})

    def test_unavailable_shelter_causes_reallocation(self) -> None:
        groups = [AffectedGroup("g1", "Area One", 12.0, 77.0, 80)]
        open_shelters = [
            Shelter("near", "Near Shelter", 12.1, 77.1, 80),
            Shelter("alternate", "Alternate Shelter", 12.2, 77.2, 100),
        ]
        closed_shelters = [
            Shelter("near", "Near Shelter", 12.1, 77.1, 80, status=ShelterStatus.UNAVAILABLE),
            Shelter("alternate", "Alternate Shelter", 12.2, 77.2, 100),
        ]
        distances = {("g1", "near"): 1.0, ("g1", "alternate"): 10.0}

        before = self.optimizer.solve(groups, open_shelters, distances)
        after = self.optimizer.solve(groups, closed_shelters, distances)

        self.assertEqual(before.allocations[0].shelter_id, "near")
        self.assertEqual(after.allocations[0].shelter_id, "alternate")
        self.assertEqual(after.metrics.allocated_people, 80)

    def test_insufficient_capacity_is_safe_and_never_overfills(self) -> None:
        groups = [AffectedGroup("g1", "Area One", 12.0, 77.0, 100)]
        shelters = [Shelter("small", "Small Shelter", 12.1, 77.1, 60)]
        distances = {("g1", "small"): 2.0}
        result = self.optimizer.solve(groups, shelters, distances)

        self.assertEqual(result.metrics.allocated_people, 60)
        self.assertEqual(result.metrics.unallocated_people, 40)
        self.assertEqual(result.metrics.capacity_violations, ())

    def test_unallocated_people_are_reported_clearly(self) -> None:
        groups = [AffectedGroup("g1", "Area One", 12.0, 77.0, 100)]
        shelters = [Shelter("small", "Small Shelter", 12.1, 77.1, 60)]
        distances = {("g1", "small"): 2.0}
        result = self.optimizer.solve(groups, shelters, distances)

        self.assertEqual(result.unallocated_by_group, {"g1": 40})
        self.assertEqual(len(result.metrics.unmet_requirements), 1)
        self.assertIn("40 people unallocated", result.metrics.unmet_requirements[0])
        self.assertIn("capacity was insufficient", result.metrics.unmet_requirements[0])


if __name__ == "__main__":
    unittest.main()
