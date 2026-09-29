# Emergency Shelter Allocation Engine (Phase 1)

This is a standalone Python integer-programming module for **PRJ_525 — Emergency Shelter Allocation Platform**.

## Scope and data note

Official problem statement: **“An AI-driven platform for optimizing emergency shelter allocation during crises.”**

This module is the team's proposed optimization implementation. It uses mathematical optimization, not machine learning: there is no labelled historical data showing a “correct” allocation. All values in `sample_data.py` are deterministic, synthetic demonstration data, not real disaster statistics.

No Flask, React, database, authentication, or map integration is included in Phase 1.

## Run it

Use Python 3.9+ and install the two solver dependencies. PuLP formulates the
model; HiGHS is the included solver backend and avoids an Intel-only bundled
CBC binary on ARM Macs:

```bash
python3 -m pip install -r optimization/requirements.txt
python3 -m optimization.run_example
python3 -m unittest discover -s tests -v
```

## What the model does

For each affected group `i` and eligible shelter `j`:

- `x[i,j]` is an integer: people assigned from group `i` to shelter `j`.
- `u[i]` is an integer: people in group `i` who remain unallocated.

An eligible pair requires all of the following:

1. The shelter status is `available`.
2. The shelter has remaining capacity (`capacity - current occupancy > 0`).
3. The shelter provides every special facility the group requires.

The model never creates a decision variable for an ineligible pair, so an unavailable or incompatible shelter cannot receive anyone.

### Constraints

For every affected group `i`:

`sum_j x[i,j] + u[i] = people[i]`

For every shelter `j`:

`sum_i x[i,j] <= capacity[j] - current_occupancy[j]`

The first constraint accounts for every person. The second prevents any capacity violation. Integer variables prevent fractional people.

### Objective function and configurable weights

The solver minimizes:

`M * sum_i(priority[i] * u[i]) + travel_weight * sum_ij(distance[i,j] * x[i,j]) + imbalance_weight * (max_utilization - min_utilization)`

Default configuration in `ObjectiveConfig`:

- `travel_weight = 1.0`
- `imbalance_weight = 10.0`
- `M = total_people * travel_weight * maximum_eligible_distance + imbalance_weight + 1`

`M` is calculated for each submitted scenario. It is greater than any possible improvement in the travel and balance terms. Consequently, the engine allocates every feasible person before trading off distance or utilization; if capacity is insufficient, leaving a higher-priority person unallocated is more costly than leaving a lower-priority person unallocated. Suggested priority levels are 1 = standard, 2 = high, 3 = critical.

Travel distance is represented as **person-distance units**: moving 10 people over a 3-unit distance adds 30 units. The utilization term discourages avoidable imbalance between usable shelters, without overriding allocation or priority protection.

## Files and team learning guide

| File | What it does | Concept to learn | Likely viva question |
| --- | --- | --- | --- |
| `data_models.py` | Validates inputs and defines typed results. | Data validation and domain modelling. | Why reject occupancy greater than capacity? |
| `priority.py` | Makes the priority policy explicit and changeable. | Policy separated from algorithm. | How does priority affect a short-capacity outcome? |
| `model.py` | Builds and solves the PuLP integer program. | Decision variables, constraints, objective functions. | Why is `x[i,j]` an integer? |
| `sample_data.py` | Supplies reproducible synthetic scenario data. | Deterministic testing data. | Are these real disaster figures? |
| `run_example.py` | Prints allocations and metrics. | Separating a library from a command-line entry point. | How could Flask later reuse the model? |
| `tests/test_model.py` | Verifies model behavior rather than only execution. | Constraint and scenario testing. | How do you prove an unavailable shelter receives zero people? |

## Explainability output

Each positive allocation contains the source group, destination shelter, people count, travel distance, priority, and the relevant availability/facility/capacity constraints. The result also reports total and average travel distance, utilization, solver runtime, capacity violations, unallocated people, and a clear reason for every group with unallocated people.

## Limitations of Phase 1

Distances are inputs, not routes calculated from a map. Facility matching is an all-or-nothing set check. Priority is a simple positive integer policy. Real deployments would validate and source these inputs from a database and may add travel-time, family cohesion, medical transport, and fairness rules only after stakeholders define them.

## Web milestone integration

The optimization package remains framework-independent. The project root now contains a Flask application (`app.py`), a persistence adapter (`backend/`), and a lightweight browser dashboard (`frontend/`) that call this optimizer through an API.
