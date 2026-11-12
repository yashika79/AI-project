from __future__ import annotations

from app.services.agents.base import AgentMessage
from app.services.rules import VenueRuleEngine
from app.services.rag import PolicyRAGEngine
from app.services.search.state import EventSpec, VenueSpec, TimeSlot


class PolicyComplianceAgent:
    name = "PolicyComplianceAgent"
    role = "Campus Regulations & Policy Compliance Officer"

    def __init__(
        self,
        rule_engine: VenueRuleEngine | None = None,
        rag_engine: PolicyRAGEngine | None = None,
        existing_bookings: list[tuple[int, TimeSlot]] | None = None,
    ):
        self.rule_engine = rule_engine or VenueRuleEngine()
        self.rag_engine = rag_engine or PolicyRAGEngine()
        self.existing_bookings = existing_bookings or []

    def process(self, message: AgentMessage) -> AgentMessage:
        event = message.data.get("event_spec")
        venue = message.data.get("venue_spec")

        if not event or not venue:
            return AgentMessage(
                sender=self.name,
                recipient=message.sender,
                message_type="REJECT",
                content="Missing event or venue specification to evaluate policy compliance.",
            )

        # 1. Rule Engine Evaluation
        report = self.rule_engine.evaluate(event, venue, self.existing_bookings)

        # 2. RAG query for specific event characteristics (noise, catering, crowd size)
        rag_queries = []
        if event.noise_level == "high":
            rag_queries.append("campus noise quiet hours curfew regulations")
        if event.requires_catering:
            rag_queries.append(f"food and catering policy for {venue.name}")
        if event.attendees >= 200:
            rag_queries.append("crowd security personnel requirements")

        rag_answers = [self.rag_engine.query_policy(q) for q in rag_queries]
        citations = [c for ans in rag_answers for c in ans.citations]

        if not report.is_feasible:
            return AgentMessage(
                sender=self.name,
                recipient=message.sender,
                message_type="CRITIQUE",
                content=(
                    f"Policy Veto: Hard rule violations detected for '{venue.name}'. "
                    f"Violations: {'; '.join(report.hard_violations)}"
                ),
                data={
                    "is_feasible": False,
                    "compliance_score": report.overall_compliance_score,
                    "hard_violations": report.hard_violations,
                    "soft_warnings": report.soft_warnings,
                    "recommendations": report.recommendations,
                    "citations": citations,
                },
            )

        msg_type = "APPROVAL" if not report.soft_warnings else "CRITIQUE"
        warning_summary = f" Warnings: {'; '.join(report.soft_warnings)}" if report.soft_warnings else " Full compliance."
        return AgentMessage(
            sender=self.name,
            recipient=message.sender,
            message_type=msg_type,
            content=(
                f"Policy Evaluation Complete. Feasible: True. Compliance Score: {report.overall_compliance_score}/100.{warning_summary}"
            ),
            data={
                "is_feasible": True,
                "compliance_score": report.overall_compliance_score,
                "hard_violations": [],
                "soft_warnings": report.soft_warnings,
                "recommendations": report.recommendations,
                "citations": citations,
            },
        )

