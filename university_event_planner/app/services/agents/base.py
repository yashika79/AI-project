from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

MessageType = Literal["REQUEST", "PROPOSAL", "CRITIQUE", "APPROVAL", "REJECT", "SUMMARY"]


@dataclass
class AgentMessage:
    sender: str
    recipient: str
    message_type: MessageType
    content: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CoordinatedEventPlan:
    event_name: str
    assigned_venue_id: int | None
    assigned_venue_name: str | None
    start_time: str
    end_time: str
    is_feasible: bool
    status: str  # "APPROVED", "CONDITIONALLY_APPROVED", "REJECTED"
    capacity_waste: int
    compliance_score: float
    hard_violations: list[str] = field(default_factory=list)
    soft_warnings: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    agent_dialogue: list[AgentMessage] = field(default_factory=list)
    executive_summary: str = ""

