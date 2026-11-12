from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Protocol
from app.services.search.state import EventSpec, TimeSlot, VenueSpec


@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    is_hard: bool
    passed: bool
    message: str
    score_deduction: float = 0.0


@dataclass
class RuleEvaluationReport:
    venue_id: int
    venue_name: str
    event_id: int
    event_name: str
    is_feasible: bool
    overall_compliance_score: float  # 0.0 to 100.0
    hard_violations: list[str] = field(default_factory=list)
    soft_warnings: list[str] = field(default_factory=list)
    passed_rules: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: list[RuleResult] = field(default_factory=list)


class Rule(Protocol):
    rule_id: str
    rule_name: str
    is_hard: bool

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        ...

