"""Priority policy helpers kept separate so the policy is easy to discuss/change."""

from .data_models import AffectedGroup


def priority_label(priority: int) -> str:
    """Return a presentation label for the project team's suggested 1--3 scale."""

    labels = {1: "standard", 2: "high", 3: "critical"}
    return labels.get(priority, f"custom level {priority}")


def priority_protection_score(group: AffectedGroup) -> int:
    """Return the coefficient used for unallocated people from this group.

    This intentionally returns the group's positive priority directly.  The
    solver's dynamically calculated protection penalty ensures this priority
    score outranks any secondary travel or balancing savings when capacity is
    insufficient.
    """

    return group.priority
