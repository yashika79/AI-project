from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class RuleEvaluationRequest(BaseModel):
    venue_id: int
    event_name: str
    attendees: int = Field(gt=0)
    start_time: datetime
    end_time: datetime
    required_facilities: list[str] = Field(default_factory=list)
    preferred_venue_type: str | None = None
    noise_level: str = "low"  # low, medium, high
    requires_catering: bool = False
    setup_buffer_minutes: int = 15


class RuleDetailOut(BaseModel):
    rule_id: str
    rule_name: str
    is_hard: bool
    passed: bool
    message: str


class RuleEvaluationResponse(BaseModel):
    venue_id: int
    venue_name: str
    event_name: str
    is_feasible: bool
    overall_compliance_score: float
    hard_violations: list[str]
    soft_warnings: list[str]
    passed_rules: list[str]
    recommendations: list[str]
    details: list[RuleDetailOut]

