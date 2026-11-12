from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any


@dataclass(frozen=True)
class TimeSlot:
    start_time: datetime
    end_time: datetime

    def overlaps(self, other: TimeSlot, buffer_minutes: int = 0) -> bool:
        """Check if two time slots overlap, including optional setup/teardown buffer."""
        buffer = timedelta(minutes=buffer_minutes)
        return (self.start_time - buffer) < other.end_time and other.start_time < (self.end_time + buffer)

    @property
    def duration_hours(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 3600.0


@dataclass(frozen=True)
class VenueSpec:
    id: int
    name: str
    venue_type: str  # "indoor", "outdoor", "lab", "auditorium"
    capacity: int
    facilities: frozenset[str]
    open_time: time = time(8, 0)
    close_time: time = time(22, 0)
    building: str | None = None
    noise_allowed: bool = True
    catering_allowed: bool = True


@dataclass(frozen=True)
class EventSpec:
    id: int
    name: str
    attendees: int
    start_time: datetime
    end_time: datetime
    required_facilities: frozenset[str] = field(default_factory=frozenset)
    preferred_venue_type: str | None = None
    priority: int = 1  # 1 = Normal, 2 = High (departmental), 3 = Critical (academic/convocation)
    noise_level: str = "low"  # "low", "medium", "high"
    requires_catering: bool = False
    setup_buffer_minutes: int = 15

    @property
    def slot(self) -> TimeSlot:
        return TimeSlot(self.start_time, self.end_time)


@dataclass
class Assignment:
    event_id: int
    venue_id: int
    slot: TimeSlot
    waste: int = 0
    compliance_score: float = 100.0


@dataclass
class SearchResult:
    algorithm: str
    success: bool
    assignments: list[Assignment]
    unassigned_events: list[int]
    nodes_expanded: int
    execution_time_ms: float
    total_capacity_waste: int
    conflict_count: int
    extra_metrics: dict[str, Any] = field(default_factory=dict)

