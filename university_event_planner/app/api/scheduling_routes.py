from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Booking, Venue
from app.schemas.scheduling import (
    AssignmentOut,
    ScheduleRequest,
    ScheduleResponse,
    StateSpaceSearchRequest,
    StateSpaceSearchResponse,
    VenueRecommendation,
)
from app.services.scheduler import ExistingBooking, VenueCandidate, recommend_venues
from app.services.search import (
    EventSpec,
    TimeSlot,
    VenueSpec,
    solve_schedule,
)

router = APIRouter(prefix="/schedule", tags=["scheduling"])


class CalendarExportItem(BaseModel):
    event_name: str
    venue_name: str
    start_time: datetime
    end_time: datetime
    description: str | None = None


class CalendarExportRequest(BaseModel):
    events: list[CalendarExportItem]


@router.post("/recommend", response_model=ScheduleResponse)
def recommend_single_event(payload: ScheduleRequest, db: Session = Depends(get_db)):
    """Baseline heuristic recommender for a single event request."""
    venues_db = db.scalars(select(Venue).options(selectinload(Venue.facilities))).all()
    bookings_db = db.scalars(select(Booking)).all()

    venues = [
        VenueCandidate(
            id=v.id,
            name=v.name,
            venue_type=v.venue_type,
            capacity=v.capacity,
            facilities={f.name for f in v.facilities},
        )
        for v in venues_db
    ]
    bookings = [
        ExistingBooking(
            venue_id=b.venue_id,
            start_time=b.start_time,
            end_time=b.end_time,
            status=b.status,
        )
        for b in bookings_db
    ]

    candidates, rejected = recommend_venues(
        venues=venues,
        bookings=bookings,
        attendees=payload.attendees,
        start_time=payload.start_time,
        end_time=payload.end_time,
        required_facilities=set(payload.required_facilities),
        preferred_venue_type=payload.preferred_venue_type,
    )

    recommendations = [
        VenueRecommendation(
            venue_id=v.id,
            venue_name=v.name,
            capacity=v.capacity,
            unused_capacity=v.capacity - payload.attendees,
            matched_facilities=sorted(set(payload.required_facilities)),
        )
        for v in candidates
    ]
    return ScheduleResponse(
        feasible=bool(recommendations),
        recommendations=recommendations,
        rejected_count=rejected,
        message=(
            "Feasible venues found. These are recommendations, not confirmed bookings."
            if recommendations
            else "No venue satisfies all supplied hard constraints for this time range."
        ),
    )


@router.post("/search", response_model=StateSpaceSearchResponse)
def search_state_space(payload: StateSpaceSearchRequest, db: Session = Depends(get_db)):
    """State-Space Search for multi-event or single-event scheduling.
    
    Algorithms available: 'csp' (Backtracking + MRV + LCV), 'astar', 'greedy', 'min_conflicts'.
    """
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
    venue_map = {v.id: v for v in venue_specs}

    existing_bookings = [
        (b.venue_id, TimeSlot(b.start_time, b.end_time))
        for b in bookings_db
        if b.status in ("confirmed", "approved")
    ]

    event_specs = [
        EventSpec(
            id=e.id,
            name=e.name,
            attendees=e.attendees,
            start_time=e.start_time,
            end_time=e.end_time,
            required_facilities=frozenset(e.required_facilities),
            preferred_venue_type=e.preferred_venue_type,
            priority=e.priority,
        )
        for e in payload.events
    ]
    event_map = {e.id: e for e in event_specs}

    try:
        result = solve_schedule(
            events=event_specs,
            venues=venue_specs,
            existing_bookings=existing_bookings,
            algorithm=payload.algorithm,  # type: ignore
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    assignments_out = [
        AssignmentOut(
            event_id=a.event_id,
            event_name=event_map[a.event_id].name,
            venue_id=a.venue_id,
            venue_name=venue_map[a.venue_id].name,
            start_time=a.slot.start_time.isoformat(),
            end_time=a.slot.end_time.isoformat(),
            waste=a.waste,
        )
        for a in result.assignments
    ]

    return StateSpaceSearchResponse(
        algorithm=result.algorithm,
        success=result.success,
        assignments=assignments_out,
        unassigned_event_ids=result.unassigned_events,
        nodes_expanded=result.nodes_expanded,
        execution_time_ms=result.execution_time_ms,
        total_capacity_waste=result.total_capacity_waste,
        conflict_count=result.conflict_count,
    )


@router.post("/export-ics")
def export_icalendar(payload: CalendarExportRequest):
    """Generates standard iCalendar (.ics) format for scheduled events."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//University Event Planner//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for idx, item in enumerate(payload.events):
        dtstart = item.start_time.strftime("%Y%m%dT%H%M%S")
        dtend = item.end_time.strftime("%Y%m%dT%H%M%S")
        uid = f"uep-{idx}-{int(item.start_time.timestamp())}@university.edu"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{item.event_name}",
            f"LOCATION:{item.venue_name}",
            f"DESCRIPTION:{item.description or 'Scheduled via University Event Planner'}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    ics_text = "\r\n".join(lines) + "\r\n"

    return Response(
        content=ics_text,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=university_events.ics"},
    )
