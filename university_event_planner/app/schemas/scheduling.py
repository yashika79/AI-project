from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator


class VenueOut(BaseModel):
    id: int
    name: str
    venue_type: str
    capacity: int
    building: str | None
    facilities: list[str]

    model_config = ConfigDict(from_attributes=True)


class ScheduleRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=160)
    attendees: int = Field(gt=0)
    start_time: datetime
    end_time: datetime
    required_facilities: list[str] = Field(default_factory=list)
    preferred_venue_type: str | None = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        if self.preferred_venue_type not in (None, "indoor", "outdoor"):
            raise ValueError("preferred_venue_type must be indoor, outdoor, or null")
        return self


class VenueRecommendation(BaseModel):
    venue_id: int
    venue_name: str
    capacity: int
    unused_capacity: int
    matched_facilities: list[str]


class ScheduleResponse(BaseModel):
    feasible: bool
    recommendations: list[VenueRecommendation]
    rejected_count: int
    message: str


class EventItemSpec(BaseModel):
    id: int
    name: str
    attendees: int = Field(gt=0)
    start_time: datetime
    end_time: datetime
    required_facilities: list[str] = Field(default_factory=list)
    preferred_venue_type: str | None = None
    priority: int = 1


class StateSpaceSearchRequest(BaseModel):
    events: list[EventItemSpec]
    algorithm: str = Field(default="csp", description="csp, astar, greedy, or min_conflicts")


class AssignmentOut(BaseModel):
    event_id: int
    event_name: str
    venue_id: int
    venue_name: str
    start_time: str
    end_time: str
    waste: int


class StateSpaceSearchResponse(BaseModel):
    algorithm: str
    success: bool
    assignments: list[AssignmentOut]
    unassigned_event_ids: list[int]
    nodes_expanded: int
    execution_time_ms: float
    total_capacity_waste: int
    conflict_count: int
