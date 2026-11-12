from __future__ import annotations

from typing import Literal
from app.services.search.astar import solve_astar
from app.services.search.csp import solve_csp
from app.services.search.greedy import solve_greedy
from app.services.search.min_conflicts import solve_min_conflicts
from app.services.search.state import (
    Assignment,
    EventSpec,
    SearchResult,
    TimeSlot,
    VenueSpec,
)

AlgorithmType = Literal["csp", "astar", "greedy", "min_conflicts"]


def solve_schedule(
    events: list[EventSpec],
    venues: list[VenueSpec],
    existing_bookings: list[tuple[int, TimeSlot]] | None = None,
    algorithm: AlgorithmType = "csp",
) -> SearchResult:
    """Unified entry point to run any of the state-space search algorithms."""
    algo = algorithm.lower().replace("-", "_")
    if algo in ("csp", "backtracking"):
        return solve_csp(events, venues, existing_bookings)
    elif algo in ("astar", "a_star", "a*"):
        return solve_astar(events, venues, existing_bookings)
    elif algo in ("min_conflicts", "minconflicts", "local_search"):
        return solve_min_conflicts(events, venues, existing_bookings)
    elif algo in ("greedy", "best_fit", "baseline"):
        return solve_greedy(events, venues, existing_bookings)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}. Choose from csp, astar, greedy, min_conflicts.")


__all__ = [
    "Assignment",
    "EventSpec",
    "SearchResult",
    "TimeSlot",
    "VenueSpec",
    "AlgorithmType",
    "solve_schedule",
    "solve_csp",
    "solve_astar",
    "solve_greedy",
    "solve_min_conflicts",
]

