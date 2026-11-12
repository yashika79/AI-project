from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from app.services.search.state import (
    Assignment,
    EventSpec,
    SearchResult,
    TimeSlot,
    VenueSpec,
)


@dataclass(order=True)
class AStarNode:
    f_score: float
    g_score: float = field(compare=False)
    state_id: int = field(compare=False)
    assignments: dict[int, int] = field(compare=False)  # event_id -> venue_id
    assigned_count: int = field(compare=False)


def solve_astar(
    events: list[EventSpec],
    venues: list[VenueSpec],
    existing_bookings: list[tuple[int, TimeSlot]] | None = None,
    max_expansions: int = 10000,
) -> SearchResult:
    """A* Heuristic Search for Optimal Venue Scheduling.
    
    Cost Function:
      f(n) = g(n) + h(n)
      g(n) = Cumulative capacity waste + preference penalty of assigned events.
      h(n) = Admissible heuristic: sum over remaining unassigned events of
             min { venue.capacity - event.attendees } over capable venues.
             Since every future event will waste at least its theoretical minimum,
             h(n) <= h*(n) (admissible and monotonic).
    """
    start_clock = time.perf_counter()
    existing = existing_bookings or []

    event_map = {e.id: e for e in events}
    venue_map = {v.id: v for v in venues}

    # Precalculate minimum possible capacity waste per event for admissible heuristic
    min_waste_cache: dict[int, int] = {}
    for event in events:
        possible_wastes = [
            v.capacity - event.attendees
            for v in venues
            if v.capacity >= event.attendees and event.required_facilities.issubset(v.facilities)
        ]
        min_waste_cache[event.id] = min(possible_wastes) if possible_wastes else 0

    def compute_heuristic(unassigned_event_ids: list[int]) -> float:
        return float(sum(min_waste_cache.get(eid, 0) for eid in unassigned_event_ids))

    def events_overlap(e1: EventSpec, e2: EventSpec) -> bool:
        buffer = max(e1.setup_buffer_minutes, e2.setup_buffer_minutes)
        return e1.slot.overlaps(e2.slot, buffer_minutes=buffer)

    # Sort events to create a fixed ordering for search tree levels
    ordered_events = sorted(events, key=lambda e: (-e.priority, -e.attendees))
    event_order_ids = [e.id for e in ordered_events]
    total_events = len(ordered_events)

    if total_events == 0:
        return SearchResult(
            algorithm="A*-StateSpaceSearch",
            success=True,
            assignments=[],
            unassigned_events=[],
            nodes_expanded=0,
            execution_time_ms=0.0,
            total_capacity_waste=0,
            conflict_count=0,
        )

    initial_h = compute_heuristic(event_order_ids)
    counter = 0
    start_node = AStarNode(
        f_score=initial_h,
        g_score=0.0,
        state_id=counter,
        assignments={},
        assigned_count=0,
    )

    open_set: list[AStarNode] = [start_node]
    nodes_expanded = 0
    best_partial_node: AStarNode = start_node

    while open_set and nodes_expanded < max_expansions:
        current = heapq.heappop(open_set)
        nodes_expanded += 1

        if current.assigned_count > best_partial_node.assigned_count:
            best_partial_node = current

        # Goal check: all events assigned
        if current.assigned_count == total_events:
            elapsed_ms = (time.perf_counter() - start_clock) * 1000.0
            assignments: list[Assignment] = []
            total_waste = 0
            for eid, vid in current.assignments.items():
                ev = event_map[eid]
                vn = venue_map[vid]
                w = vn.capacity - ev.attendees
                total_waste += w
                assignments.append(
                    Assignment(
                        event_id=eid,
                        venue_id=vid,
                        slot=ev.slot,
                        waste=w,
                    )
                )

            return SearchResult(
                algorithm="A*-StateSpaceSearch",
                success=True,
                assignments=assignments,
                unassigned_events=[],
                nodes_expanded=nodes_expanded,
                execution_time_ms=round(elapsed_ms, 3),
                total_capacity_waste=total_waste,
                conflict_count=0,
                extra_metrics={
                    "optimal": True,
                    "final_cost": current.g_score,
                },
            )

        # Next event in canonical ordering
        next_event_id = event_order_ids[current.assigned_count]
        next_event = event_map[next_event_id]

        for venue in venues:
            # Hard constraints
            if venue.capacity < next_event.attendees:
                continue
            if not next_event.required_facilities.issubset(venue.facilities):
                continue
            if next_event.preferred_venue_type and venue.venue_type != next_event.preferred_venue_type:
                continue
            if next_event.start_time.time() < venue.open_time or next_event.end_time.time() > venue.close_time:
                continue

            # Check overlap with external bookings
            ext_conflict = any(
                vid == venue.id and slot.overlaps(next_event.slot, buffer_minutes=next_event.setup_buffer_minutes)
                for vid, slot in existing
            )
            if ext_conflict:
                continue

            # Check overlap with already assigned events in this state
            internal_conflict = False
            for assigned_eid, assigned_vid in current.assignments.items():
                if assigned_vid == venue.id and events_overlap(next_event, event_map[assigned_eid]):
                    internal_conflict = True
                    break

            if internal_conflict:
                continue

            # Calculate transition cost
            waste = venue.capacity - next_event.attendees
            pref_penalty = 0.0
            if next_event.preferred_venue_type and venue.venue_type != next_event.preferred_venue_type:
                pref_penalty = 50.0

            step_cost = float(waste) + pref_penalty
            new_g = current.g_score + step_cost

            remaining_ids = event_order_ids[current.assigned_count + 1:]
            new_h = compute_heuristic(remaining_ids)
            new_f = new_g + new_h

            counter += 1
            new_assignments = dict(current.assignments)
            new_assignments[next_event_id] = venue.id

            heapq.heappush(
                open_set,
                AStarNode(
                    f_score=new_f,
                    g_score=new_g,
                    state_id=counter,
                    assignments=new_assignments,
                    assigned_count=current.assigned_count + 1,
                ),
            )

    # If full assignment could not be found, report best partial state
    elapsed_ms = (time.perf_counter() - start_clock) * 1000.0
    partial_assignments: list[Assignment] = []
    total_waste = 0
    for eid, vid in best_partial_node.assignments.items():
        ev = event_map[eid]
        vn = venue_map[vid]
        w = vn.capacity - ev.attendees
        total_waste += w
        partial_assignments.append(
            Assignment(event_id=eid, venue_id=vid, slot=ev.slot, waste=w)
        )

    unassigned_ids = [eid for eid in event_order_ids if eid not in best_partial_node.assignments]

    return SearchResult(
        algorithm="A*-StateSpaceSearch",
        success=(len(unassigned_ids) == 0),
        assignments=partial_assignments,
        unassigned_events=unassigned_ids,
        nodes_expanded=nodes_expanded,
        execution_time_ms=round(elapsed_ms, 3),
        total_capacity_waste=total_waste,
        conflict_count=len(unassigned_ids),
        extra_metrics={
            "optimal": False if unassigned_ids else True,
            "best_partial_count": len(partial_assignments),
        },
    )

