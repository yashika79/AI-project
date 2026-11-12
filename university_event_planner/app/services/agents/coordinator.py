from __future__ import annotations

from datetime import datetime
from app.services.agents.base import AgentMessage, CoordinatedEventPlan
from app.services.agents.scheduling_agent import SchedulingAgent
from app.services.agents.policy_agent import PolicyComplianceAgent
from app.services.agents.logistics_agent import LogisticsAgent
from app.services.search.state import EventSpec, VenueSpec, TimeSlot


class CoordinatorAgent:
    name = "CoordinatorAgent"
    role = "Lead Event Planning Orchestrator"

    def __init__(
        self,
        venues: list[VenueSpec],
        existing_bookings: list[tuple[int, TimeSlot]] | None = None,
        max_negotiation_rounds: int = 4,
    ):
        self.venues = venues
        self.existing_bookings = existing_bookings or []
        self.max_negotiation_rounds = max_negotiation_rounds
        self.scheduling_agent = SchedulingAgent(self.venues, self.existing_bookings)
        self.policy_agent = PolicyComplianceAgent(existing_bookings=self.existing_bookings)
        self.logistics_agent = LogisticsAgent()

    def plan_event(self, event: EventSpec) -> CoordinatedEventPlan:
        dialogue: list[AgentMessage] = []

        # Step 1: User Request to Coordinator
        user_msg = AgentMessage(
            sender="User",
            recipient=self.name,
            message_type="REQUEST",
            content=f"Plan event '{event.name}' for {event.attendees} attendees from {event.start_time.isoformat()} to {event.end_time.isoformat()}.",
            data={"event": event},
        )
        dialogue.append(user_msg)

        excluded_venue_ids: set[int] = set()
        chosen_venue: VenueSpec | None = None
        chosen_waste: int = 0
        final_policy_data: dict = {}
        final_logistics_data: dict = {}
        negotiation_success = False

        # Multi-turn negotiation loop
        for round_idx in range(self.max_negotiation_rounds):
            round_num = round_idx + 1

            # Request SchedulingAgent to search scheduling states
            sched_content = (
                f"Search scheduling state space to find feasible venue for '{event.name}'."
                if round_num == 1
                else f"Negotiation Round {round_num}: Re-search state space excluding vetoed venue IDs: {sorted(excluded_venue_ids)}."
            )
            sched_request = AgentMessage(
                sender=self.name,
                recipient=self.scheduling_agent.name,
                message_type="REQUEST",
                content=sched_content,
                data={"event": event, "exclude_venue_ids": list(excluded_venue_ids)},
            )
            dialogue.append(sched_request)

            sched_response = self.scheduling_agent.process(sched_request)
            dialogue.append(sched_response)

            if sched_response.message_type == "REJECT":
                # No more viable venues in state space
                break

            candidate_venue: VenueSpec = sched_response.data["venue_spec"]
            candidate_waste: int = sched_response.data["waste"]

            # Request Policy Agent verification
            policy_request = AgentMessage(
                sender=self.name,
                recipient=self.policy_agent.name,
                message_type="REQUEST",
                content=f"Evaluate policy and rule compliance for candidate venue '{candidate_venue.name}'.",
                data={"event_spec": event, "venue_spec": candidate_venue},
            )
            dialogue.append(policy_request)

            policy_response = self.policy_agent.process(policy_request)
            dialogue.append(policy_response)

            is_feasible = policy_response.data.get("is_feasible", False)
            soft_warnings = policy_response.data.get("soft_warnings", [])
            strict_policy_issue = any(
                ("Catering requested" in w and event.requires_catering) or
                ("quiet hours" in w and event.noise_level == "high")
                for w in soft_warnings
            )

            # Check if Policy Agent vetoed or strictly objected to this venue
            if (not is_feasible or strict_policy_issue) and round_num < self.max_negotiation_rounds:
                violations = policy_response.data.get("hard_violations", []) or [w for w in soft_warnings if "Catering" in w or "quiet hours" in w]
                veto_msg = (
                    f"Policy Veto on '{candidate_venue.name}': {'; '.join(violations)}. "
                    f"Initiating state-space re-allocation."
                )
                coordinator_critique = AgentMessage(
                    sender=self.name,
                    recipient=self.scheduling_agent.name,
                    message_type="CRITIQUE",
                    content=veto_msg,
                    data={"vetoed_venue_id": candidate_venue.id, "violations": violations},
                )
                dialogue.append(coordinator_critique)
                excluded_venue_ids.add(candidate_venue.id)
                continue  # Try next round

            if not is_feasible:
                # If still infeasible on final round
                break

            # If policy passed, request Logistics Agent verification
            logistics_request = AgentMessage(
                sender=self.name,
                recipient=self.logistics_agent.name,
                message_type="REQUEST",
                content=f"Verify facilities, AV setup, and buffers for '{candidate_venue.name}'.",
                data={"event_spec": event, "venue_spec": candidate_venue},
            )
            dialogue.append(logistics_request)

            logistics_response = self.logistics_agent.process(logistics_request)
            dialogue.append(logistics_response)

            # Success! Both scheduling, policy, and logistics have agreed
            chosen_venue = candidate_venue
            chosen_waste = candidate_waste
            final_policy_data = policy_response.data
            final_logistics_data = logistics_response.data
            negotiation_success = True
            break

        if not negotiation_success or chosen_venue is None:
            summary = (
                f"Multi-agent negotiation concluded with REJECTION: No venue could satisfy both hard scheduling "
                f"constraints and campus policy rules for '{event.name}'."
            )
            coordinator_fail = AgentMessage(
                sender=self.name,
                recipient="User",
                message_type="SUMMARY",
                content=summary,
                data={"status": "REJECTED"},
            )
            dialogue.append(coordinator_fail)

            return CoordinatedEventPlan(
                event_name=event.name,
                assigned_venue_id=None,
                assigned_venue_name=None,
                start_time=event.start_time.isoformat(),
                end_time=event.end_time.isoformat(),
                is_feasible=False,
                status="REJECTED",
                capacity_waste=0,
                compliance_score=0.0,
                hard_violations=["All candidate venues failed either spatial capacity, time buffers, or policy regulations."],
                soft_warnings=[],
                action_items=["Shift event time, reduce attendees, or remove restricted activities (e.g., catering/high-noise) to unlock venues."],
                agent_dialogue=dialogue,
                executive_summary=summary,
            )

        # Build coordinated plan
        hard_violations = final_policy_data.get("hard_violations", [])
        soft_warnings = final_policy_data.get("soft_warnings", [])
        compliance_score = final_policy_data.get("compliance_score", 100.0)
        action_items = []
        action_items.extend(final_policy_data.get("recommendations", []))
        action_items.extend(final_logistics_data.get("logistics_checklist", []))

        negotiation_note = f" (reached after {round_num} negotiation round{'s' if round_num > 1 else ''})" if round_num > 1 else ""
        status = "APPROVED" if (not soft_warnings) else "CONDITIONALLY_APPROVED"
        summary = (
            f"Consensus achieved{negotiation_note}! Venue '{chosen_venue.name}' allocated with {chosen_waste} unused seats. "
            f"Status: {status} (Compliance Score: {compliance_score}%). All agent requirements synchronized."
        )

        coordinator_summary = AgentMessage(
            sender=self.name,
            recipient="User",
            message_type="SUMMARY",
            content=summary,
            data={"status": status, "venue": chosen_venue.name, "rounds": round_num},
        )
        dialogue.append(coordinator_summary)

        return CoordinatedEventPlan(
            event_name=event.name,
            assigned_venue_id=chosen_venue.id,
            assigned_venue_name=chosen_venue.name,
            start_time=event.start_time.isoformat(),
            end_time=event.end_time.isoformat(),
            is_feasible=True,
            status=status,
            capacity_waste=chosen_waste,
            compliance_score=compliance_score,
            hard_violations=hard_violations,
            soft_warnings=soft_warnings,
            action_items=action_items,
            agent_dialogue=dialogue,
            executive_summary=summary,
        )
