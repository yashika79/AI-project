from __future__ import annotations

import copy
import time
from typing import Any
from app.services.search.state import (
    Assignment,
    EventSpec,
    SearchResult,
    TimeSlot,
    VenueSpec,
)


class CSPScheduler:
    """Constraint Satisfaction Problem (CSP) Solver for Event Scheduling.
    
    Implements:
    - Minimum Remaining Values (MRV) Variable Ordering
    - Degree Heuristic (Tie breaker for MRV based on temporal overlap degree)
    - Least Constraining Value (LCV) Value Ordering
    - Forward Checking (FC) with immediate domain rollback
    - AC-3 Arc Consistency Pre-filtering
    """

    def __init__(
        self,
        events: list[EventSpec],
        venues: list[VenueSpec],
        existing_bookings: list[tuple[int, TimeSlot]] | None = None,
    ):
        self.events = events
        self.venues = venues
        self.existing_bookings = existing_bookings or []
        self.venue_by_id = {v.id: v for v in venues}
        self.event_by_id = {e.id: e for e in events}

        self.nodes_expanded = 0
        self.backtracks = 0

    def _initial_domains(self) -> dict[int, list[int]]:
        """Compute initial domains for each event satisfying unary constraints."""
        domains: dict[int, list[int]] = {}

        for event in self.events:
            feasible_venues: list[int] = []
            for venue in self.venues:
                # Capacity constraint
                if venue.capacity < event.attendees:
                    continue
                # Facilities constraint
                if not event.required_facilities.issubset(venue.facilities):
                    continue
                # Preferred venue type
                if event.preferred_venue_type and venue.venue_type != event.preferred_venue_type:
                    continue
                # Operating hours constraint
                if event.start_time.time() < venue.open_time or event.end_time.time() > venue.close_time:
                    continue
                # Pre-existing booking collision
                has_external_conflict = any(
                    vid == venue.id and slot.overlaps(event.slot, buffer_minutes=event.setup_buffer_minutes)
                    for vid, slot in self.existing_bookings
                )
                if has_external_conflict:
                    continue

                feasible_venues.append(venue.id)
            domains[event.id] = feasible_venues

        return domains

    def _events_overlap(self, e1: EventSpec, e2: EventSpec) -> bool:
        buffer = max(e1.setup_buffer_minutes, e2.setup_buffer_minutes)
        return e1.slot.overlaps(e2.slot, buffer_minutes=buffer)

    def ac3(self, domains: dict[int, list[int]]) -> bool:
        """Run AC-3 arc consistency. Returns False if a domain becomes empty."""
        queue: list[tuple[int, int]] = []
        for i, e1 in enumerate(self.events):
            for j, e2 in enumerate(self.events):
                if i != j and self._events_overlap(e1, e2):
                    queue.append((e1.id, e2.id))

        while queue:
            xi, xj = queue.pop(0)
            if self._revise(domains, xi, xj):
                if len(domains[xi]) == 0:
                    return False
                e_xi = self.event_by_id[xi]
                for other in self.events:
                    if other.id != xi and other.id != xj and self._events_overlap(other, e_xi):
                        queue.append((other.id, xi))
        return True

    def _revise(self, domains: dict[int, list[int]], xi: int, xj: int) -> bool:
        revised = False
        e_i = self.event_by_id[xi]
        e_j = self.event_by_id[xj]

        if not self._events_overlap(e_i, e_j):
            return False

        to_remove = []
        for v_i in domains[xi]:
            # Is there any value v_j in domains[xj] such that (v_i, v_j) is valid?
            # They conflict if and only if v_i == v_j (since time slots overlap).
            satisfiable = any(v_j != v_i for v_j in domains[xj])
            if not satisfiable:
                to_remove.append(v_i)
                revised = True

        for val in to_remove:
            domains[xi].remove(val)

        return revised

    def _select_unassigned_variable(
        self,
        unassigned: list[int],
        domains: dict[int, list[int]],
    ) -> int:
        """MRV heuristic with Degree Heuristic tie-breaker."""
        def mrv_degree_key(e_id: int):
            domain_size = len(domains[e_id])
            event = self.event_by_id[e_id]
            degree = sum(
                1 for other_id in unassigned
                if other_id != e_id and self._events_overlap(event, self.event_by_id[other_id])
            )
            # Minimize domain size, maximize degree (so negative degree), prioritize high priority
            return (domain_size, -degree, -event.priority)

        return min(unassigned, key=mrv_degree_key)

    def _order_domain_values(
        self,
        var_id: int,
        unassigned: list[int],
        domains: dict[int, list[int]],
    ) -> list[int]:
        """Least Constraining Value (LCV) heuristic."""
        event = self.event_by_id[var_id]

        def count_conflicts(venue_id: int) -> tuple[int, int]:
            eliminated = 0
            for other_id in unassigned:
                if other_id == var_id:
                    continue
                other = self.event_by_id[other_id]
                if self._events_overlap(event, other) and venue_id in domains[other_id]:
                    eliminated += 1
            venue = self.venue_by_id[venue_id]
            waste = venue.capacity - event.attendees
            return (eliminated, waste)

        return sorted(domains[var_id], key=count_conflicts)

    def solve(self) -> SearchResult:
        start_clock = time.perf_counter()
        domains = self._initial_domains()

        # Run AC-3 preprocessing
        if not self.ac3(domains):
            elapsed_ms = (time.perf_counter() - start_clock) * 1000.0
            return SearchResult(
                algorithm="CSP-Backtracking",
                success=False,
                assignments=[],
                unassigned_events=[e.id for e in self.events],
                nodes_expanded=0,
                execution_time_ms=round(elapsed_ms, 3),
                total_capacity_waste=0,
                conflict_count=0,
                extra_metrics={"ac3_pruned_to_empty": True},
            )

        assignment_map: dict[int, int] = {}
        unassigned = [e.id for e in self.events]

        success = self._backtrack(assignment_map, unassigned, domains)
        elapsed_ms = (time.perf_counter() - start_clock) * 1000.0

        assignments: list[Assignment] = []
        total_waste = 0
        for eid, vid in assignment_map.items():
            ev = self.event_by_id[eid]
            vn = self.venue_by_id[vid]
            waste = vn.capacity - ev.attendees
            total_waste += waste
            assignments.append(
                Assignment(
                    event_id=eid,
                    venue_id=vid,
                    slot=ev.slot,
                    waste=waste,
                )
            )

        unassigned_result = [eid for eid in [e.id for e in self.events] if eid not in assignment_map]

        return SearchResult(
            algorithm="CSP-Backtracking-MRV-LCV",
            success=success,
            assignments=assignments,
            unassigned_events=unassigned_result,
            nodes_expanded=self.nodes_expanded,
            execution_time_ms=round(elapsed_ms, 3),
            total_capacity_waste=total_waste,
            conflict_count=0 if success else len(unassigned_result),
            extra_metrics={
                "backtracks": self.backtracks,
                "ac3_prefiltered": True,
            },
        )

    def _backtrack(
        self,
        assignments: dict[int, int],
        unassigned: list[int],
        domains: dict[int, list[int]],
    ) -> bool:
        if not unassigned:
            return True

        self.nodes_expanded += 1
        var_id = self._select_unassigned_variable(unassigned, domains)
        event = self.event_by_id[var_id]

        ordered_values = self._order_domain_values(var_id, unassigned, domains)

        for venue_id in ordered_values:
            # Check consistency with current assignments
            consistent = True
            for assigned_eid, assigned_vid in assignments.items():
                if assigned_vid == venue_id and self._events_overlap(event, self.event_by_id[assigned_eid]):
                    consistent = False
                    break

            if not consistent:
                continue

            # Forward checking: clone domains and prune
            saved_domains = {k: list(v) for k, v in domains.items()}
            assignments[var_id] = venue_id
            new_unassigned = [e for e in unassigned if e != var_id]

            # Prune venue_id from overlapping unassigned variables
            domain_wipeout = False
            for other_id in new_unassigned:
                if self._events_overlap(event, self.event_by_id[other_id]):
                    if venue_id in domains[other_id]:
                        domains[other_id].remove(venue_id)
                        if len(domains[other_id]) == 0:
                            domain_wipeout = True
                            break

            if not domain_wipeout:
                if self._backtrack(assignments, new_unassigned, domains):
                    return True

            # Undo assignment and restore domains
            self.backtracks += 1
            del assignments[var_id]
            domains = saved_domains

        return False


def solve_csp(
    events: list[EventSpec],
    venues: list[VenueSpec],
    existing_bookings: list[tuple[int, TimeSlot]] | None = None,
) -> SearchResult:
    solver = CSPScheduler(events, venues, existing_bookings)
    return solver.solve()

