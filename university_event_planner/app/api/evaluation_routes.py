from __future__ import annotations

from fastapi import APIRouter
from app.schemas.evaluation import (
    AlgorithmEvaluationOut,
    BenchmarkRequest,
    BenchmarkResponse,
)
from app.services.evaluation import run_benchmark

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/scenarios")
def list_benchmark_scenarios():
    """Lists standard evaluation scenarios for comparing AI approaches."""
    return {
        "scenarios": [
            {
                "id": "light",
                "name": "Light Load Scenario",
                "events_count": 4,
                "description": "4 events across diverse faculties with ample venue capacity.",
            },
            {
                "id": "contested",
                "name": "Prime-Time Contested Scenario",
                "events_count": 6,
                "description": "6 events simultaneously competing for key auditoriums and lecture halls at 10:00-12:00.",
            },
            {
                "id": "medium",
                "name": "Campus Fest Scenario",
                "events_count": 12,
                "description": "12 multi-day festival events with varied facility and noise requirements.",
            },
            {
                "id": "stress",
                "name": "High Contention Stress Test",
                "events_count": 20,
                "description": "20 events testing scalability, backtracking depth, and memory bounds.",
            },
        ]
    }


@router.post("/benchmark", response_model=BenchmarkResponse)
def execute_benchmark(payload: BenchmarkRequest):
    """Executes a comparative benchmark across AI approaches (Greedy, CSP, A*, Min-Conflicts)."""
    report = run_benchmark(scenario_name=payload.scenario_name)

    evals_out = [
        AlgorithmEvaluationOut(
            algorithm_name=e.algorithm_name,
            success=e.success,
            assigned_count=e.assigned_count,
            unassigned_count=e.unassigned_count,
            total_events=e.total_events,
            solve_rate_percent=e.solve_rate_percent,
            execution_time_ms=e.execution_time_ms,
            nodes_expanded=e.nodes_expanded,
            total_capacity_waste=e.total_capacity_waste,
            average_waste_per_event=e.average_waste_per_event,
            conflict_count=e.conflict_count,
            trade_off_summary=e.trade_off_summary,
        )
        for e in report.evaluations
    ]

    return BenchmarkResponse(
        scenario_name=report.scenario_name,
        total_events=report.total_events,
        total_venues=report.total_venues,
        recommendation=report.recommendation,
        evaluations=evals_out,
    )

