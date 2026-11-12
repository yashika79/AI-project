from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from app.services.evaluation.scenarios import get_benchmark_venues, get_scenario_events
from app.services.search import (
    SearchResult,
    solve_astar,
    solve_csp,
    solve_greedy,
    solve_min_conflicts,
)


@dataclass
class AlgorithmEvaluation:
    algorithm_name: str
    success: bool
    assigned_count: int
    unassigned_count: int
    total_events: int
    solve_rate_percent: float
    execution_time_ms: float
    nodes_expanded: int
    total_capacity_waste: int
    average_waste_per_event: float
    conflict_count: int
    trade_off_summary: str


@dataclass
class BenchmarkReport:
    scenario_name: str
    total_events: int
    total_venues: int
    evaluations: list[AlgorithmEvaluation]
    recommendation: str


def run_benchmark(
    scenario_name: str = "medium",
    venues=None,
    events=None,
) -> BenchmarkReport:
    scenario_venues = venues or get_benchmark_venues()
    scenario_events = events or get_scenario_events(scenario_name)

    total_events = len(scenario_events)
    total_venues = len(scenario_venues)

    evaluations: list[AlgorithmEvaluation] = []

    # 1. Evaluate Greedy Best-Fit
    res_greedy: SearchResult = solve_greedy(scenario_events, scenario_venues)
    evaluations.append(
        AlgorithmEvaluation(
            algorithm_name="Greedy Best-Fit (Baseline)",
            success=res_greedy.success,
            assigned_count=len(res_greedy.assignments),
            unassigned_count=len(res_greedy.unassigned_events),
            total_events=total_events,
            solve_rate_percent=round((len(res_greedy.assignments) / max(1, total_events)) * 100, 1),
            execution_time_ms=res_greedy.execution_time_ms,
            nodes_expanded=res_greedy.nodes_expanded,
            total_capacity_waste=res_greedy.total_capacity_waste,
            average_waste_per_event=round(
                res_greedy.total_capacity_waste / max(1, len(res_greedy.assignments)), 1
            ),
            conflict_count=res_greedy.conflict_count,
            trade_off_summary="Ultra-fast O(N*V) heuristic. Ideal for initial assignments, but susceptible to early myopic choices.",
        )
    )

    # 2. Evaluate CSP Backtracking with MRV + LCV + Forward Checking
    res_csp: SearchResult = solve_csp(scenario_events, scenario_venues)
    evaluations.append(
        AlgorithmEvaluation(
            algorithm_name="CSP Backtracking (MRV + LCV + FC)",
            success=res_csp.success,
            assigned_count=len(res_csp.assignments),
            unassigned_count=len(res_csp.unassigned_events),
            total_events=total_events,
            solve_rate_percent=round((len(res_csp.assignments) / max(1, total_events)) * 100, 1),
            execution_time_ms=res_csp.execution_time_ms,
            nodes_expanded=res_csp.nodes_expanded,
            total_capacity_waste=res_csp.total_capacity_waste,
            average_waste_per_event=round(
                res_csp.total_capacity_waste / max(1, len(res_csp.assignments)), 1
            ),
            conflict_count=res_csp.conflict_count,
            trade_off_summary="Complete and sound. Guaranteed to find a valid conflict-free assignment or prove inconsistency.",
        )
    )

    # 3. Evaluate A* State-Space Search
    res_astar: SearchResult = solve_astar(scenario_events, scenario_venues)
    evaluations.append(
        AlgorithmEvaluation(
            algorithm_name="A* Heuristic Search (Admissible h)",
            success=res_astar.success,
            assigned_count=len(res_astar.assignments),
            unassigned_count=len(res_astar.unassigned_events),
            total_events=total_events,
            solve_rate_percent=round((len(res_astar.assignments) / max(1, total_events)) * 100, 1),
            execution_time_ms=res_astar.execution_time_ms,
            nodes_expanded=res_astar.nodes_expanded,
            total_capacity_waste=res_astar.total_capacity_waste,
            average_waste_per_event=round(
                res_astar.total_capacity_waste / max(1, len(res_astar.assignments)), 1
            ),
            conflict_count=res_astar.conflict_count,
            trade_off_summary="Optimal capacity utilization via admissible lower-bound heuristic. Higher memory overhead.",
        )
    )

    # 4. Evaluate Min-Conflicts Local Search
    res_mc: SearchResult = solve_min_conflicts(scenario_events, scenario_venues)
    evaluations.append(
        AlgorithmEvaluation(
            algorithm_name="Min-Conflicts (Local Repair)",
            success=res_mc.success,
            assigned_count=len(res_mc.assignments),
            unassigned_count=len(res_mc.unassigned_events),
            total_events=total_events,
            solve_rate_percent=round((len(res_mc.assignments) / max(1, total_events)) * 100, 1),
            execution_time_ms=res_mc.execution_time_ms,
            nodes_expanded=res_mc.nodes_expanded,
            total_capacity_waste=res_mc.total_capacity_waste,
            average_waste_per_event=round(
                res_mc.total_capacity_waste / max(1, len(res_mc.assignments)), 1
            ),
            conflict_count=res_mc.conflict_count,
            trade_off_summary="Iterative repair metaheuristic. Excellent for large batch timetables and schedule updates.",
        )
    )

    # Determine recommended algorithm based on metrics
    successful = [e for e in evaluations if e.success]
    if successful:
        # Pick the one with smallest capacity waste among successful
        best = min(successful, key=lambda x: (x.total_capacity_waste, x.execution_time_ms))
        rec = f"Recommended approach for '{scenario_name}': {best.algorithm_name}. Achieved 100% solve rate with minimal capacity waste ({best.total_capacity_waste} seats) in {best.execution_time_ms}ms."
    else:
        best = max(evaluations, key=lambda x: (x.solve_rate_percent, -x.total_capacity_waste))
        rec = f"No algorithm fully satisfied all constraints without conflict. {best.algorithm_name} scheduled the highest proportion ({best.solve_rate_percent}%)."

    return BenchmarkReport(
        scenario_name=scenario_name,
        total_events=total_events,
        total_venues=total_venues,
        evaluations=evaluations,
        recommendation=rec,
    )

