from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Booking, Venue
from app.schemas.agents import (
    AgentMessageOut,
    AgentPlanRequest,
    AgentPlanResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.services.agents import CoordinatorAgent, OrchestratorAgent
from app.services.search.state import EventSpec, TimeSlot, VenueSpec

router = APIRouter(prefix="", tags=["agents & chat"])


def _build_context(db: Session) -> tuple[list[VenueSpec], list[tuple[int, TimeSlot]]]:
    venues_db = db.scalars(select(Venue).options(selectinload(Venue.facilities))).all()
    bookings_db = db.scalars(select(Booking)).all()

    venue_specs = [
        VenueSpec(
            id=v.id,
            name=v.name,
            venue_type=v.venue_type,
            capacity=v.capacity,
            facilities=frozenset([f.name for f in v.facilities]),
            building=v.building,
        )
        for v in venues_db
    ]

    existing_bookings = [
        (b.venue_id, TimeSlot(b.start_time, b.end_time))
        for b in bookings_db
        if b.status in ("confirmed", "approved")
    ]
    return venue_specs, existing_bookings


def _map_venue_to_3d_id(venue_name: str | None) -> list[str]:
    if not venue_name:
        return []
    vn = venue_name.lower()
    if "hall b" in vn or "34 b" in vn or "34·b" in vn or "34 · b" in vn or "34b" in vn:
        return ["b34b"]
    if "hall a" in vn or "34 a" in vn or "34·a" in vn or "34 · a" in vn or "34a" in vn or "34" in vn:
        return ["b34a"]
    if "seminar 2" in vn or "32 b" in vn or "32·b" in vn or "32 · b" in vn or "32b" in vn:
        return ["b32b"]
    if "seminar 1" in vn or "32 a" in vn or "32·a" in vn or "32 · a" in vn or "32a" in vn or "32" in vn:
        return ["b32a"]
    if "mall" in vn:
        return ["mall"]
    if "auditorium" in vn:
        return ["aud"]
    if "ground" in vn or "lawn" in vn or "unipolis" in vn or "amphitheatre" in vn:
        return ["gnd"]
    if "lab" in vn:
        return ["b34a"]
    if "conference" in vn:
        return ["b32a"]
    return ["aud"]


@router.post("/chat", response_model=ChatMessageResponse)
@router.post("/agents/chat", response_model=ChatMessageResponse)
def chat_with_orchestrator(payload: ChatMessageRequest, db: Session = Depends(get_db)):
    """Conversational Orchestrator Endpoint for Lovely Professional University.
    
    Abstracts AI internals and accepts natural language instructions:
    - Parses intent & event specs automatically.
    - Dynamically routes to CSP when hard constraints are present.
    - Dynamically routes to A* when optimization/waste minimization is desired.
    - Dynamically routes to Policy RAG when rules or guidelines are queried.
    - Connects directly to the 3D Three.js presentation layer (flying camera to venueIds).
    """
    venue_specs, existing_bookings = _build_context(db)
    orchestrator = OrchestratorAgent(venues=venue_specs, existing_bookings=existing_bookings)

    turn = orchestrator.process_message(payload.message)

    plan_out: AgentPlanResponse | None = None
    venue_ids: list[str] = []
    if turn.plan:
        dialogue_out = [
            AgentMessageOut(
                sender=m.sender,
                recipient=m.recipient,
                message_type=m.message_type,
                content=m.content,
                timestamp=m.timestamp,
                data={k: str(v) for k, v in m.data.items() if not k.endswith("_spec") and k != "search_result"},
            )
            for m in turn.plan.agent_dialogue
        ]
        plan_out = AgentPlanResponse(
            event_name=turn.plan.event_name,
            assigned_venue_id=turn.plan.assigned_venue_id,
            assigned_venue_name=turn.plan.assigned_venue_name,
            start_time=turn.plan.start_time,
            end_time=turn.plan.end_time,
            is_feasible=turn.plan.is_feasible,
            status=turn.plan.status,
            capacity_waste=turn.plan.capacity_waste,
            compliance_score=turn.plan.compliance_score,
            hard_violations=turn.plan.hard_violations,
            soft_warnings=turn.plan.soft_warnings,
            action_items=turn.plan.action_items,
            executive_summary=turn.plan.executive_summary,
            agent_dialogue=dialogue_out,
        )
        if turn.plan.assigned_venue_name:
            venue_ids = _map_venue_to_3d_id(turn.plan.assigned_venue_name)

    subagent_out = [
        AgentMessageOut(
            sender=m.sender,
            recipient=m.recipient,
            message_type=m.message_type,
            content=m.content,
            timestamp=m.timestamp,
            data={k: str(v) for k, v in m.data.items() if not k.endswith("_spec") and k != "search_result"},
        )
        for m in turn.subagent_dialogue
    ]

    # Compute chips for interactive UI
    chips: list[str] = []
    if plan_out and plan_out.is_feasible:
        chips = ["Book this", "Show another"]
        if turn.suggested_followups:
            chips.extend(turn.suggested_followups[:2])
    elif turn.suggested_followups:
        chips = turn.suggested_followups[:4]
    else:
        chips = ["Hackathon", "Fest", "Seminar", "Sports meet"]

    return ChatMessageResponse(
        reply=turn.reply,
        intent=turn.intent,
        algorithm_selected=turn.algorithm_selected,
        routing_reason=turn.routing_reason,
        plan=plan_out,
        action_items=turn.action_items,
        subagent_dialogue=subagent_out,
        suggested_followups=turn.suggested_followups,
        venueIds=venue_ids,
        chips=chips,
    )


@router.post("/agents/plan", response_model=AgentPlanResponse)
def plan_event_with_agents(payload: AgentPlanRequest, db: Session = Depends(get_db)):
    """Direct multi-agent planning endpoint using explicit structured parameters."""
    venue_specs, existing_bookings = _build_context(db)
    coordinator = CoordinatorAgent(venues=venue_specs, existing_bookings=existing_bookings)

    event_spec = EventSpec(
        id=1,
        name=payload.event_name,
        attendees=payload.attendees,
        start_time=payload.start_time,
        end_time=payload.end_time,
        required_facilities=frozenset(payload.required_facilities),
        preferred_venue_type=payload.preferred_venue_type,
        priority=payload.priority,
        noise_level=payload.noise_level,
        requires_catering=payload.requires_catering,
        setup_buffer_minutes=payload.setup_buffer_minutes,
    )

    plan = coordinator.plan_event(event_spec)

    dialogue_out = [
        AgentMessageOut(
            sender=m.sender,
            recipient=m.recipient,
            message_type=m.message_type,
            content=m.content,
            timestamp=m.timestamp,
            data={k: str(v) for k, v in m.data.items() if not k.endswith("_spec") and k != "search_result"},
        )
        for m in plan.agent_dialogue
    ]

    return AgentPlanResponse(
        event_name=plan.event_name,
        assigned_venue_id=plan.assigned_venue_id,
        assigned_venue_name=plan.assigned_venue_name,
        start_time=plan.start_time,
        end_time=plan.end_time,
        is_feasible=plan.is_feasible,
        status=plan.status,
        capacity_waste=plan.capacity_waste,
        compliance_score=plan.compliance_score,
        hard_violations=plan.hard_violations,
        soft_warnings=plan.soft_warnings,
        action_items=plan.action_items,
        executive_summary=plan.executive_summary,
        agent_dialogue=dialogue_out,
    )
