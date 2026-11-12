from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AgentPlanRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=160)
    attendees: int = Field(gt=0)
    start_time: datetime
    end_time: datetime
    required_facilities: list[str] = Field(default_factory=list)
    preferred_venue_type: str | None = None
    priority: int = Field(default=1, ge=1, le=3)
    noise_level: str = "low"  # low, medium, high
    requires_catering: bool = False
    setup_buffer_minutes: int = 15


class AgentMessageOut(BaseModel):
    sender: str
    recipient: str
    message_type: str
    content: str
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentPlanResponse(BaseModel):
    event_name: str
    assigned_venue_id: int | None
    assigned_venue_name: str | None
    start_time: str
    end_time: str
    is_feasible: bool
    status: str
    capacity_waste: int
    compliance_score: float
    hard_violations: list[str]
    soft_warnings: list[str]
    action_items: list[str]
    executive_summary: str
    agent_dialogue: list[AgentMessageOut]


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    context: dict[str, Any] | None = None


class ChatMessageResponse(BaseModel):
    reply: str
    intent: str
    algorithm_selected: str
    routing_reason: str
    plan: AgentPlanResponse | None = None
    action_items: list[str] = Field(default_factory=list)
    subagent_dialogue: list[AgentMessageOut] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)
    venueIds: list[str] = Field(default_factory=list)
    chips: list[str] = Field(default_factory=list)
