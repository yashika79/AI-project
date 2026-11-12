from __future__ import annotations

from pydantic import BaseModel, Field


class BenchmarkRequest(BaseModel):
    scenario_name: str = Field(default="medium", description="light, contested, medium, or stress")


class AlgorithmEvaluationOut(BaseModel):
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


class BenchmarkResponse(BaseModel):
    scenario_name: str
    total_events: int
    total_venues: int
    recommendation: str
    evaluations: list[AlgorithmEvaluationOut]

