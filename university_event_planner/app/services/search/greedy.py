from __future__ import annotations

import time
from app.services.search.state import (
    Assignment,
    EventSpec,
    SearchResult,
    TimeSlot,
    VenueSpec,
)


def solve_greedy(
    events: list[EventSpec],
    venues: list[VenueSpec],
    existing_bookings: list[tuple[int, TimeSlot]] | None = None,
) -> SearchResult:
    """Baseline Greedy Best-Fit Algorithm.
    
    Sorts events by priority descending, then attendee count descending.
    For each event, assigns the feasible venue that minimizes unused capacity (waste).
    """
    start_clock = time.perf_counter()
    nodes_expanded = 0
    existing = existing_bookings or []

    # Map venue_id -> list of occupied slots (including external bookings)
    venue_occupied: dict[int, list[TimeSlot]] = {v.id: [] for v in venues}
    for vid, slot in existing:
        if vid in venue_occupied:
            venue_occupied[vid].append(slot)

    assignments: list[Assignment] = []
    unassigned: list[int] = []
    total_waste = 0

    sorted_events = sorted(events, key=lambda e: (-e.priority, -e.attendees))

    for event in sorted_events:
        nodes_expanded += 1
        best_venue: VenueSpec | None = None
        best_waste = float("inf")

        for venue in venues:
            # Hard constraints check
            if venue.capacity < event.attendees:
                continue
            if not event.required_facilities.issubset(venue.facilities):
                continue
            if event.preferred_venue_type and venue.venue_type != event.preferred_venue_type:
                continue

            # Operating hours check
            if event.start_time.time() < venue.open_time or event.end_time.time() > venue.close_time:
                continue

            # Time collision check with buffer
            conflict = any(
                slot.overlaps(event.slot, buffer_minutes=event.setup_buffer_minutes)
                for slot in venue_occupied[venue.id]
            )
            if conflict:
                continue

            waste = venue.capacity - event.attendees
            if waste < best_waste:
                best_waste = waste
                best_venue = venue

        if best_venue is not None:
            assignments.append(
                Assignment(
                    event_id=event.id,
                    venue_id=best_venue.id,
                    slot=event.slot,
                    waste=int(best_waste),
                )
            )
            venue_occupied[best_venue.id].append(event.slot)
            total_waste += int(best_waste)
        else:
            unassigned.append(event.id)

    elapsed_ms = (time.perf_counter() - start_clock) * 1000.0
    return SearchResult(
        algorithm="Greedy-BestFit",
        success=(len(unassigned) == 0),
        assignments=assignments,
        unassigned_events=unassigned,
        nodes_expanded=nodes_expanded,
        execution_time_ms=round(elapsed_ms, 3),
        total_capacity_waste=total_waste,
        conflict_count=0,
        extra_metrics={"assigned_count": len(assignments), "total_events": len(events)},
    )

