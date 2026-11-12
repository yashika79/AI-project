from __future__ import annotations

import random
import time
from app.services.search.state import (
    Assignment,
    EventSpec,
    SearchResult,
    TimeSlot,
    VenueSpec,
)


def solve_min_conflicts(
    events: list[EventSpec],
    venues: list[VenueSpec],
    existing_bookings: list[tuple[int, TimeSlot]] | None = None,
    max_steps: int = 1500,
    random_walk_prob: float = 0.15,
) -> SearchResult:
    """Min-Conflicts Local Search Algorithm for Event Scheduling.
    
    1. Initializes an initial assignment (best-fit ignoring collisions).
    2. Repeatedly selects a conflicted variable and reassigns it to the venue
       that minimizes total constraint conflicts.
    3. Employs random walk to escape local minima traps.
    """
    start_clock = time.perf_counter()
    existing = existing_bookings or []

    event_map = {e.id: e for e in events}
    venue_map = {v.id: v for v in venues}

    def events_overlap(e1: EventSpec, e2: EventSpec) -> bool:
        buffer = max(e1.setup_buffer_minutes, e2.setup_buffer_minutes)
        return e1.slot.overlaps(e2.slot, buffer_minutes=buffer)

    # Initial Assignment: assign each event to a capable venue that minimizes capacity waste
    current_assignment: dict[int, int] = {}
    for event in events:
        capable = [
            v for v in venues
            if v.capacity >= event.attendees and event.required_facilities.issubset(v.facilities)
        ]
        if capable:
            best_v = min(capable, key=lambda v: v.capacity - event.attendees)
            current_assignment[event.id] = best_v.id
        else:
            # Fallback to largest venue
            fallback = max(venues, key=lambda v: v.capacity)
            current_assignment[event.id] = fallback.id

    def count_var_conflicts(event_id: int, venue_id: int, assignment: dict[int, int]) -> int:
        event = event_map[event_id]
        venue = venue_map[venue_id]
        conflicts = 0

        # Capacity violation
        if venue.capacity < event.attendees:
            conflicts += 10
        # Facility violation
        missing_fac = len(event.required_facilities - venue.facilities)
        conflicts += missing_fac * 5
        # Operating hours
        if event.start_time.time() < venue.open_time or event.end_time.time() > venue.close_time:
            conflicts += 8
        # External booking overlap
        for vid, slot in existing:
            if vid == venue_id and slot.overlaps(event.slot, buffer_minutes=event.setup_buffer_minutes):
                conflicts += 10

        # Overlap with other events assigned to the same venue
        for other_id, other_vid in assignment.items():
            if other_id != event_id and other_vid == venue_id:
                if events_overlap(event, event_map[other_id]):
                    conflicts += 10

        return conflicts

    def get_conflicted_events(assignment: dict[int, int]) -> list[int]:
        conflicted = []
        for eid, vid in assignment.items():
            if count_var_conflicts(eid, vid, assignment) > 0:
                conflicted.append(eid)
        return conflicted

    steps = 0
    rng = random.Random(42)

    for step in range(max_steps):
        steps = step + 1
        conflicted = get_conflicted_events(current_assignment)
        if not conflicted:
            break

        # Pick a conflicted event
        chosen_event_id = rng.choice(conflicted)

        if rng.random() < random_walk_prob:
            # Random walk: pick random venue
            new_venue = rng.choice(venues)
            current_assignment[chosen_event_id] = new_venue.id
        else:
            # Min-conflicts: choose venue with minimum conflicts
            best_venues: list[int] = []
            min_c = float("inf")
            for v in venues:
                c = count_var_conflicts(chosen_event_id, v.id, current_assignment)
                if c < min_c:
                    min_c = c
                    best_venues = [v.id]
                elif c == min_c:
                    best_venues.append(v.id)
            current_assignment[chosen_event_id] = rng.choice(best_venues)

    final_conflicted = get_conflicted_events(current_assignment)
    elapsed_ms = (time.perf_counter() - start_clock) * 1000.0

    assignments: list[Assignment] = []
    total_waste = 0
    unassigned: list[int] = []

    for eid, vid in current_assignment.items():
        ev = event_map[eid]
        vn = venue_map[vid]
        c = count_var_conflicts(eid, vid, current_assignment)
        if c == 0:
            w = vn.capacity - ev.attendees
            total_waste += w
            assignments.append(Assignment(event_id=eid, venue_id=vid, slot=ev.slot, waste=w))
        else:
            unassigned.append(eid)

    return SearchResult(
        algorithm="Min-Conflicts-LocalSearch",
        success=(len(final_conflicted) == 0),
        assignments=assignments,
        unassigned_events=unassigned,
        nodes_expanded=steps,
        execution_time_ms=round(elapsed_ms, 3),
        total_capacity_waste=total_waste,
        conflict_count=len(final_conflicted),
        extra_metrics={
            "iterations": steps,
            "resolved_all": (len(final_conflicted) == 0),
        },
    )

