from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Booking, Venue
from app.schemas.rules import (
    RuleDetailOut,
    RuleEvaluationRequest,
    RuleEvaluationResponse,
)
from app.services.rules import VenueRuleEngine
from app.services.search.state import EventSpec, TimeSlot, VenueSpec

router = APIRouter(prefix="/rules", tags=["rules"])
rule_engine = VenueRuleEngine()


@router.post("/evaluate", response_model=RuleEvaluationResponse)
def evaluate_venue_rules(payload: RuleEvaluationRequest, db: Session = Depends(get_db)):
    """Evaluates hard constraints and soft campus policies for an event-venue allocation."""
    venue_db = db.scalar(
        select(Venue).where(Venue.id == payload.venue_id).options(selectinload(Venue.facilities))
    )
    if not venue_db:
        raise HTTPException(status_code=404, detail=f"Venue with id {payload.venue_id} not found.")

    venue_spec = VenueSpec(
        id=venue_db.id,
        name=venue_db.name,
        venue_type=venue_db.venue_type,
        capacity=venue_db.capacity,
        facilities=frozenset([f.name for f in venue_db.facilities]),
        building=venue_db.building,
    )

    bookings_db = db.scalars(select(Booking).where(Booking.venue_id == payload.venue_id)).all()
    existing_bookings = [
        (b.venue_id, TimeSlot(b.start_time, b.end_time))
        for b in bookings_db
        if b.status in ("confirmed", "approved")
    ]

    event_spec = EventSpec(
        id=1,
        name=payload.event_name,
        attendees=payload.attendees,
        start_time=payload.start_time,
        end_time=payload.end_time,
        required_facilities=frozenset(payload.required_facilities),
        preferred_venue_type=payload.preferred_venue_type,
        noise_level=payload.noise_level,
        requires_catering=payload.requires_catering,
        setup_buffer_minutes=payload.setup_buffer_minutes,
    )

    report = rule_engine.evaluate(event_spec, venue_spec, existing_bookings)

    details_out = [
        RuleDetailOut(
            rule_id=d.rule_id,
            rule_name=d.rule_name,
            is_hard=d.is_hard,
            passed=d.passed,
            message=d.message,
        )
        for d in report.details
    ]

    return RuleEvaluationResponse(
        venue_id=report.venue_id,
        venue_name=report.venue_name,
        event_name=report.event_name,
        is_feasible=report.is_feasible,
        overall_compliance_score=report.overall_compliance_score,
        hard_violations=report.hard_violations,
        soft_warnings=report.soft_warnings,
        passed_rules=report.passed_rules,
        recommendations=report.recommendations,
        details=details_out,
    )

