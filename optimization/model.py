"""PuLP integer-programming model for emergency shelter allocation."""

from time import perf_counter
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import pulp

from .data_models import (
    AffectedGroup,
    Allocation,
    ObjectiveConfig,
    OptimizationMetrics,
    OptimizationResult,
    Shelter,
    ShelterStatus,
    ShelterUtilization,
)
from .priority import priority_protection_score


DistanceMatrix = Mapping[Tuple[str, str], float]


class OptimizationError(RuntimeError):
    """Raised when the input cannot be modeled or the solver does not finish."""


class ShelterAllocationOptimizer:
    """Solve the shelter allocation model without any Flask or database dependency."""

    def __init__(self, objective_config: ObjectiveConfig = None) -> None:
        self.objective_config = objective_config or ObjectiveConfig()

    def solve(
        self,
        groups: Sequence[AffectedGroup],
        shelters: Sequence[Shelter],
        distances: DistanceMatrix,
    ) -> OptimizationResult:
        """Return a feasible integer allocation, or a clear input/solver error.

        The decision variable ``x[group, shelter]`` is the integer number of
        people sent along a compatible, available route.  ``u[group]`` is the
        integer number left unallocated.  See README.md for the exact objective
        and constraints.
        """

        groups = list(groups)
        shelters = list(shelters)
        self._validate_inputs(groups, shelters, distances)
        started_at = perf_counter()

        compatible_pairs = [
            (group, shelter)
            for group in groups
            for shelter in shelters
            if self._is_eligible(group, shelter)
        ]
        max_distance = max((distances[(g.id, s.id)] for g, s in compatible_pairs), default=0.0)
        total_people = sum(group.people for group in groups)

        problem = pulp.LpProblem("emergency_shelter_allocation", pulp.LpMinimize)
        allocations = {
            (group.id, shelter.id): pulp.LpVariable(
                f"allocated__{group.id}__{shelter.id}", lowBound=0, cat=pulp.LpInteger
            )
            for group, shelter in compatible_pairs
        }
        unallocated = {
            group.id: pulp.LpVariable(f"unallocated__{group.id}", lowBound=0, cat=pulp.LpInteger)
            for group in groups
        }

        for group in groups:
            group_allocations = [
                allocations[(group.id, shelter.id)]
                for shelter in shelters
                if (group.id, shelter.id) in allocations
            ]
            problem += (
                pulp.lpSum(group_allocations) + unallocated[group.id] == group.people,
                f"demand_conservation__{group.id}",
            )

        for shelter in shelters:
            shelter_allocations = [
                allocations[(group.id, shelter.id)]
                for group in groups
                if (group.id, shelter.id) in allocations
            ]
            problem += (
                pulp.lpSum(shelter_allocations) <= shelter.remaining_capacity,
                f"remaining_capacity__{shelter.id}",
            )

        utilization_range = self._add_utilization_balance_constraints(problem, shelters, groups, allocations)
        protection_penalty = self._protection_penalty(total_people, max_distance)
        priority_unallocated = pulp.lpSum(
            protection_penalty * priority_protection_score(group) * unallocated[group.id]
            for group in groups
        )
        travel_cost = pulp.lpSum(
            self.objective_config.travel_weight * distances[(group.id, shelter.id)] * allocations[(group.id, shelter.id)]
            for group, shelter in compatible_pairs
        )
        balance_cost = self.objective_config.imbalance_weight * utilization_range
        problem += priority_unallocated + travel_cost + balance_cost

        status_code = problem.solve(self._select_solver())
        status = pulp.LpStatus[status_code]
        if status != "Optimal":
            raise OptimizationError(f"PuLP could not find an optimal allocation (status: {status}).")

        runtime_ms = (perf_counter() - started_at) * 1000
        return self._build_result(
            groups,
            shelters,
            distances,
            allocations,
            unallocated,
            status,
            float(pulp.value(problem.objective)),
            runtime_ms,
        )

    @staticmethod
    def _select_solver() -> pulp.LpSolver:
        """Choose HiGHS when installed, with CBC as a portable fallback.

        ``highspy`` supplies a native HiGHS build for current ARM macOS and
        other common platforms.  PuLP's bundled CBC binary is useful as a
        fallback on systems where it is compatible, but is not assumed to run
        everywhere.
        """

        available = pulp.listSolvers(onlyAvailable=True)
        if "HiGHS" in available:
            return pulp.HiGHS(msg=False)
        if "PULP_CBC_CMD" in available:
            return pulp.PULP_CBC_CMD(msg=False)
        raise OptimizationError(
            "No PuLP solver is available. Install the dependencies in optimization/requirements.txt."
        )

    def _add_utilization_balance_constraints(
        self,
        problem: pulp.LpProblem,
        shelters: Sequence[Shelter],
        groups: Sequence[AffectedGroup],
        allocations: Mapping[Tuple[str, str], pulp.LpVariable],
    ) -> pulp.LpAffineExpression:
        """Create min/max utilization variables; their difference is the imbalance."""

        usable_shelters = [shelter for shelter in shelters if shelter.remaining_capacity > 0]
        if not usable_shelters:
            return pulp.LpAffineExpression()

        maximum = pulp.LpVariable("maximum_utilization", lowBound=0, upBound=1)
        minimum = pulp.LpVariable("minimum_utilization", lowBound=0, upBound=1)
        for shelter in usable_shelters:
            assigned = pulp.lpSum(
                allocations[(group.id, shelter.id)]
                for group in groups
                if (group.id, shelter.id) in allocations
            )
            utilization = assigned / shelter.remaining_capacity
            problem += maximum >= utilization, f"maximum_utilization__{shelter.id}"
            problem += minimum <= utilization, f"minimum_utilization__{shelter.id}"
        return maximum - minimum

    def _protection_penalty(self, total_people: int, max_distance: float) -> float:
        """Calculate a safe priority penalty from the submitted scenario.

        It exceeds the largest possible combined secondary-cost change, so the
        optimizer never leaves someone unallocated merely to reduce distance or
        balance.  This is preferable to a hidden hard-coded penalty.
        """

        secondary_upper_bound = (
            total_people * self.objective_config.travel_weight * max_distance
            + self.objective_config.imbalance_weight
        )
        return secondary_upper_bound + 1.0

    @staticmethod
    def _is_eligible(group: AffectedGroup, shelter: Shelter) -> bool:
        return (
            shelter.status == ShelterStatus.AVAILABLE
            and shelter.remaining_capacity > 0
            and group.special_requirements.issubset(shelter.facilities)
        )

    @staticmethod
    def _validate_inputs(
        groups: Sequence[AffectedGroup], shelters: Sequence[Shelter], distances: DistanceMatrix
    ) -> None:
        if not groups:
            raise ValueError("At least one affected group is required.")
        if not shelters:
            raise ValueError("At least one shelter is required.")
        group_ids = [group.id for group in groups]
        shelter_ids = [shelter.id for shelter in shelters]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("Affected group ids must be unique.")
        if len(shelter_ids) != len(set(shelter_ids)):
            raise ValueError("Shelter ids must be unique.")

        for group in groups:
            for shelter in shelters:
                key = (group.id, shelter.id)
                if key not in distances:
                    raise ValueError(f"Missing distance for group '{group.id}' and shelter '{shelter.id}'.")
                if distances[key] < 0:
                    raise ValueError(f"Distance for {group.id} to {shelter.id} cannot be negative.")

    def _build_result(
        self,
        groups: Sequence[AffectedGroup],
        shelters: Sequence[Shelter],
        distances: DistanceMatrix,
        variables: Mapping[Tuple[str, str], pulp.LpVariable],
        unallocated_variables: Mapping[str, pulp.LpVariable],
        status: str,
        objective_value: float,
        runtime_ms: float,
    ) -> OptimizationResult:
        group_by_id = {group.id: group for group in groups}
        shelter_by_id = {shelter.id: shelter for shelter in shelters}
        result_allocations: List[Allocation] = []
        assigned_by_shelter = {shelter.id: 0 for shelter in shelters}

        for group in groups:
            for shelter in shelters:
                variable = variables.get((group.id, shelter.id))
                people = int(round(variable.value())) if variable is not None and variable.value() else 0
                if not people:
                    continue
                assigned_by_shelter[shelter.id] += people
                requirements = ", ".join(sorted(group.special_requirements)) or "none"
                result_allocations.append(
                    Allocation(
                        group_id=group.id,
                        group_name=group.name,
                        shelter_id=shelter.id,
                        shelter_name=shelter.name,
                        people=people,
                        distance=float(distances[(group.id, shelter.id)]),
                        priority=group.priority,
                        constraints=(
                            "Shelter status is available.",
                            f"Required facilities satisfied: {requirements}.",
                            "Shelter assignment is within remaining capacity.",
                        ),
                    )
                )

        unallocated_by_group = {
            group.id: int(round(unallocated_variables[group.id].value()))
            for group in groups
            if int(round(unallocated_variables[group.id].value())) > 0
        }
        total_people = sum(group.people for group in groups)
        allocated_people = sum(allocation.people for allocation in result_allocations)
        total_travel = sum(allocation.people * allocation.distance for allocation in result_allocations)
        utilization = tuple(
            ShelterUtilization(
                shelter_id=shelter.id,
                shelter_name=shelter.name,
                allocated_people=assigned_by_shelter[shelter.id],
                remaining_capacity=shelter.remaining_capacity,
                utilization=(assigned_by_shelter[shelter.id] / shelter.remaining_capacity)
                if shelter.remaining_capacity
                else 0.0,
            )
            for shelter in shelters
        )
        capacity_violations = tuple(
            f"{shelter.name} exceeds remaining capacity."
            for shelter in shelters
            if assigned_by_shelter[shelter.id] > shelter.remaining_capacity
        )
        unmet_requirements = tuple(
            self._unallocated_explanation(
                group_by_id[group_id], shelters, unallocated_people
            )
            for group_id, unallocated_people in unallocated_by_group.items()
        )
        metrics = OptimizationMetrics(
            total_people=total_people,
            allocated_people=allocated_people,
            unallocated_people=total_people - allocated_people,
            total_travel_distance=total_travel,
            average_travel_distance=(total_travel / allocated_people) if allocated_people else 0.0,
            shelter_utilization=utilization,
            capacity_violations=capacity_violations,
            unmet_requirements=unmet_requirements,
            objective_value=objective_value,
            runtime_ms=runtime_ms,
        )
        return OptimizationResult(
            status=status,
            allocations=tuple(result_allocations),
            unallocated_by_group=unallocated_by_group,
            metrics=metrics,
        )

    def _unallocated_explanation(
        self, group: AffectedGroup, shelters: Sequence[Shelter], unallocated_people: int
    ) -> str:
        eligible_shelters = [shelter for shelter in shelters if self._is_eligible(group, shelter)]
        if not eligible_shelters:
            required = ", ".join(sorted(group.special_requirements)) or "no special facility"
            return (
                f"{group.name}: {unallocated_people} people unallocated because no available shelter "
                f"meets the required facilities ({required})."
            )
        return (
            f"{group.name}: {unallocated_people} people unallocated because eligible shelter capacity "
            "was insufficient."
        )
