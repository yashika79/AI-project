from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.services.agents.base import AgentMessage, CoordinatedEventPlan
from app.services.agents.coordinator import CoordinatorAgent
from app.services.agents.nlu import IntentParser, NLUParseResult
from app.services.rag import PolicyRAGEngine, PolicyAnswer
from app.services.search.state import EventSpec, TimeSlot, VenueSpec


@dataclass
class ChatTurnResponse:
    reply: str
    intent: str
    algorithm_selected: str
    routing_reason: str
    plan: CoordinatedEventPlan | None = None
    policy_answer: PolicyAnswer | None = None
    subagent_dialogue: list[AgentMessage] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    suggested_followups: list[str] = field(default_factory=list)


class OrchestratorAgent:
    """Central router and conversational decision-maker for the University Event Planner.
    
    Parses natural language requests, abstracts the underlying AI engine, and
    dynamically delegates to:
    - CSP Solver (when hard capacity, equipment, and zero-overlap constraints must be satisfied)
    - A* Heuristic Search (when optimization, minimal capacity waste, or best-fit pairing is requested)
    - Policy RAG (when institutional rules, quiet hours, catering, or security guidelines are queried)
    - Logistics & Policy Sub-Agents (for equipment, buffers, and compliance verification)
    """

    def __init__(
        self,
        venues: list[VenueSpec],
        existing_bookings: list[tuple[int, TimeSlot]] | None = None,
    ):
        self.venues = venues
        self.existing_bookings = existing_bookings or []
        self.nlu = IntentParser()
        self.coordinator = CoordinatorAgent(self.venues, self.existing_bookings)
        self.rag_engine = PolicyRAGEngine()

    def process_message(self, message: str) -> ChatTurnResponse:
        parsed: NLUParseResult = self.nlu.parse(message)

        # ----------------------------------------------------
        # ROUTE 1: POLICY RAG ASSISTANCE
        # ----------------------------------------------------
        if parsed.intent == "POLICY_QUERY":
            ans = self.rag_engine.query_policy(parsed.policy_query or message)
            citations_md = "\n".join(
                [f"- **[{c.clause_id}]** {c.doc_title} ({c.section_title}): _{c.excerpt}_" for c in ans.citations]
            )
            checklist_md = "\n".join([f"- [ ] {item}" for item in ans.actionable_checklist])

            reply = (
                f"### 📋 Campus Policy Guidance\n\n"
                f"**Status:** `{ans.compliance_status}` (Confidence: {int(ans.confidence_score * 100)}%)\n\n"
                f"{ans.answer}\n\n"
                f"#### Verified Policy Citations\n{citations_md}\n\n"
                f"{('#### Actionable Checklist\n' + checklist_md) if ans.actionable_checklist else ''}"
            )

            return ChatTurnResponse(
                reply=reply,
                intent="POLICY_QUERY",
                algorithm_selected="Policy-RAG (Hybrid BM25 + Dense Semantic)",
                routing_reason=parsed.routing_reason,
                policy_answer=ans,
                action_items=ans.actionable_checklist,
                suggested_followups=[
                    "Would you like me to find a compliant venue for this event?",
                    "What are the security requirements if attendance exceeds 200?",
                ],
            )

        # ----------------------------------------------------
        # ROUTE 2: BENCHMARK INQUIRY
        # ----------------------------------------------------
        if parsed.intent == "BENCHMARK":
            reply = (
                f"### ⚡ AI Algorithm Evaluation Suite\n\n"
                f"I can evaluate our four scheduling approaches:\n"
                f"1. **CSP Backtracking (MRV + LCV + FC)**: Exact hard constraint satisfaction.\n"
                f"2. **A* Heuristic Search**: Optimal venue fit minimizing seat waste ($h(n) \\le h^*(n)$).\n"
                f"3. **Min-Conflicts Local Search**: Iterative timetable conflict repair.\n"
                f"4. **Greedy Best-Fit**: Rapid $O(N \\cdot V)$ baseline.\n\n"
                f"You can trigger benchmarks directly from the **'AI Benchmark'** tab or ask me: _'Run benchmark on fest scenario'_."
            )
            return ChatTurnResponse(
                reply=reply,
                intent="BENCHMARK",
                algorithm_selected="AI Benchmarking Engine",
                routing_reason=parsed.routing_reason,
                suggested_followups=["Run benchmark on light scenario", "Run benchmark on contested scenario"],
            )

        # ----------------------------------------------------
        # ROUTE 3: VENUE DIRECTORY INSPECTION
        # ----------------------------------------------------
        if parsed.intent == "INSPECT_VENUES":
            venues_list_md = "\n".join([
                f"- **{v.name}** (Capacity: {v.capacity} | {v.venue_type.title()} | Facilities: {', '.join(sorted(v.facilities))})"
                for v in self.venues[:8]
            ])
            reply = (
                f"### 🏛️ University Campus Venues\n\n"
                f"Here are the primary spaces available for scheduling:\n\n"
                f"{venues_list_md}\n\n"
                f"Tell me what event you are planning (e.g., _'I need a hall for 150 people with a projector tomorrow afternoon'_), and I will allocate the optimal space!"
            )
            return ChatTurnResponse(
                reply=reply,
                intent="INSPECT_VENUES",
                algorithm_selected="Directory Registry",
                routing_reason=parsed.routing_reason,
                suggested_followups=[
                    "Book a hall for 80 attendees with projector and wifi",
                    "Can we hold a concert in the Amphitheatre?",
                ],
            )

        # ----------------------------------------------------
        # ROUTE 4: DYNAMIC MULTI-AGENT EVENT SCHEDULING (CSP vs A*)
        # ----------------------------------------------------
        ext = parsed.extracted_event
        if ext is None:
            return ChatTurnResponse(
                reply="I couldn't quite extract the event details. Please tell me your estimated attendees, required equipment (e.g. projector, wifi, stage), and preferred time!",
                intent="GENERAL",
                algorithm_selected="None",
                routing_reason="Unspecified details in query.",
            )

        event_spec = EventSpec(
            id=101,
            name=ext.event_name,
            attendees=ext.attendees,
            start_time=ext.start_time,
            end_time=ext.end_time,
            required_facilities=frozenset(ext.required_facilities),
            preferred_venue_type=ext.preferred_venue_type,
            priority=ext.priority,
            noise_level=ext.noise_level,
            requires_catering=ext.requires_catering,
            setup_buffer_minutes=ext.setup_buffer_minutes,
        )

        # Execute coordinated planning with sub-agents (Coordinator, Scheduling, Policy, Logistics)
        plan = self.coordinator.plan_event(event_spec)

        date_str = event_spec.start_time.strftime("%A, %b %d, %Y")
        time_str = f"{event_spec.start_time.strftime('%I:%M %p')} – {event_spec.end_time.strftime('%I:%M %p')}"

        if plan.is_feasible and plan.assigned_venue_name:
            reply_lines = [
                f"### 🎉 Event Allocation Confirmed: **{event_spec.name}**",
                f"",
                f"I've analyzed your requirements and coordinated our sub-agents to reserve the optimal venue:",
                f"",
                f"- **Allocated Venue:** `{plan.assigned_venue_name}`",
                f"- **Date & Time:** {date_str} from {time_str}",
                f"- **Expected Attendees:** {event_spec.attendees} (Capacity Waste: {plan.capacity_waste} unused seats)",
                f"- **Status:** `{plan.status}` (Compliance Score: {plan.compliance_score}%)",
                f"- **Selected Algorithm:** `{parsed.algorithm_route}` ({parsed.routing_reason})",
            ]

            if plan.soft_warnings:
                reply_lines.append("\n**⚠️ Compliance Considerations:**")
                for w in plan.soft_warnings:
                    reply_lines.append(f"- {w}")

            if plan.action_items:
                reply_lines.append("\n**📋 Logistical Action Items:**")
                for item in plan.action_items:
                    reply_lines.append(f"- [x] {item}")

            reply_lines.append(
                f"\n_Sub-agents synchronized: SchedulingAgent (State Search), PolicyComplianceAgent (RAG & Rules), LogisticsAgent (AV & Buffers)._"
            )
            reply = "\n".join(reply_lines)
        else:
            reply_lines = [
                f"### ❌ Scheduling Conflict: **{event_spec.name}**",
                f"",
                f"None of our campus venues currently satisfy all hard constraints for **{event_spec.attendees} attendees** during {time_str}.",
                f"",
                f"**Reasons:**",
            ]
            for v in plan.hard_violations:
                reply_lines.append(f"- {v}")
            reply_lines.append("\n**Recommended Adjustments:**")
            for a in plan.action_items:
                reply_lines.append(f"- {a}")
            reply = "\n".join(reply_lines)

        return ChatTurnResponse(
            reply=reply,
            intent="PLAN_EVENT",
            algorithm_selected=f"{parsed.algorithm_route} via Multi-Agent Coordination",
            routing_reason=parsed.routing_reason,
            plan=plan,
            subagent_dialogue=plan.agent_dialogue,
            action_items=plan.action_items,
            suggested_followups=[
                f"Can we serve refreshments in {plan.assigned_venue_name or 'the venue'}?",
                f"What is the cancellation deadline for this booking?",
                f"Show me alternative time slots on {date_str}",
            ],
        )
