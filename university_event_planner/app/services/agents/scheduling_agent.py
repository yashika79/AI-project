from __future__ import annotations

from app.services.agents.base import AgentMessage
from app.services.search import EventSpec, VenueSpec, TimeSlot, solve_csp, solve_astar, solve_greedy


class SchedulingAgent:
    name = "SchedulingAgent"
    role = "State-Space Scheduling & Allocation Specialist"

    def __init__(self, venues: list[VenueSpec], existing_bookings: list[tuple[int, TimeSlot]]):
        self.venues = venues
        self.existing_bookings = existing_bookings
        self.venue_by_id = {v.id: v for v in venues}

    def process(self, message: AgentMessage) -> AgentMessage:
        event_dict = message.data.get("event")
        if not event_dict:
            return AgentMessage(
                sender=self.name,
                recipient=message.sender,
                message_type="REJECT",
                content="No event specification provided for scheduling.",
            )

        event = event_dict if isinstance(event_dict, EventSpec) else EventSpec(**event_dict)
        excluded_ids = set(message.data.get("exclude_venue_ids", []))

        # Filter candidate venues by excluding previously rejected venue IDs
        candidate_venues = [v for v in self.venues if v.id not in excluded_ids]

        if not candidate_venues:
            return AgentMessage(
                sender=self.name,
                recipient=message.sender,
                message_type="REJECT",
                content=f"No further alternative venues available in candidate state space for '{event.name}'.",
                data={"candidate_pool_empty": True},
            )

        # Run CSP Backtracking with MRV to find feasible venue(s)
        csp_result = solve_csp([event], candidate_venues, self.existing_bookings)

        if not csp_result.success or not csp_result.assignments:
            # Fallback to A* search to check if a valid path exists
            astar_result = solve_astar([event], candidate_venues, self.existing_bookings)
            if not astar_result.success or not astar_result.assignments:
                return AgentMessage(
                    sender=self.name,
                    recipient=message.sender,
                    message_type="REJECT",
                    content=(
                        f"Search concluded: No remaining candidate venue satisfies hard constraints for '{event.name}' "
                        f"({event.attendees} attendees, {event.start_time.strftime('%H:%M')}-{event.end_time.strftime('%H:%M')})."
                    ),
                    data={"search_result": csp_result},
                )
            assigned_venue_id = astar_result.assignments[0].venue_id
            waste = astar_result.assignments[0].waste
            nodes = astar_result.nodes_expanded
            algo_used = "A*-HeuristicSearch"
        else:
            assigned_venue_id = csp_result.assignments[0].venue_id
            waste = csp_result.assignments[0].waste
            nodes = csp_result.nodes_expanded
            algo_used = "CSP-Backtracking"

        venue = self.venue_by_id[assigned_venue_id]

        exclusion_note = f" (excluding {len(excluded_ids)} previously vetoed venues)" if excluded_ids else ""
        return AgentMessage(
            sender=self.name,
            recipient=message.sender,
            message_type="PROPOSAL",
            content=(
                f"Proposed Venue: '{venue.name}' (Capacity: {venue.capacity}, Type: {venue.venue_type}){exclusion_note}. "
                f"State-space search ({algo_used}) expanded {nodes} nodes. Unused capacity waste: {waste} seats."
            ),
            data={
                "venue_id": venue.id,
                "venue_name": venue.name,
                "waste": waste,
                "venue_spec": venue,
                "event_spec": event,
                "algorithm": algo_used,
            },
        )
