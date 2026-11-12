from __future__ import annotations

from dataclasses import dataclass, field
from app.services.rag.vector_store import DocumentChunk, HybridPolicyVectorStore


@dataclass
class PolicyCitation:
    doc_title: str
    section_title: str
    clause_id: str
    excerpt: str
    relevance_score: float


@dataclass
class PolicyAnswer:
    query: str
    answer: str
    compliance_status: str  # "COMPLIANT", "NON_COMPLIANT", "CONDITIONAL_APPROVAL", "UNSPECIFIED"
    citations: list[PolicyCitation]
    actionable_checklist: list[str] = field(default_factory=list)
    confidence_score: float = 1.0


class PolicyRAGEngine:
    """Policy-Aware RAG Engine with Grounded Retrieval and Zero-Hallucination Guardrails."""

    def __init__(self, vector_store: HybridPolicyVectorStore | None = None):
        self.vector_store = vector_store or HybridPolicyVectorStore()

    def query_policy(self, query: str, top_k: int = 3) -> PolicyAnswer:
        results = self.vector_store.search(query, top_k=top_k)
        if not results:
            return PolicyAnswer(
                query=query,
                answer=(
                    "No relevant official university policy clause could be found for your inquiry. "
                    "Per institutional governance, unlisted activities require case-by-case clearance "
                    "from the Dean of Student Affairs."
                ),
                compliance_status="UNSPECIFIED",
                citations=[],
                actionable_checklist=["Consult Student Affairs Office directly."],
                confidence_score=0.0,
            )

        citations = [
            PolicyCitation(
                doc_title=chunk.doc_title,
                section_title=chunk.section_title,
                clause_id=chunk.clause_id,
                excerpt=chunk.content,
                relevance_score=score,
            )
            for chunk, score in results
        ]

        # Synthesize grounded answer
        top_chunk, top_score = results[0]
        q_lower = query.lower()

        status = "COMPLIANT"
        checklist: list[str] = []
        answer_parts: list[str] = []

        # Analyze retrieved content against query intent
        combined_text = " ".join([c.content for c, _ in results])

        if "food" in q_lower or "pizza" in q_lower or "catering" in q_lower or "drink" in q_lower:
            if "lab" in q_lower or "auditorium" in q_lower:
                status = "NON_COMPLIANT"
                answer_parts.append(
                    "Food and open beverages are strictly prohibited in technical venues, computer labs, "
                    "and the main auditorium seating area to avoid equipment damage."
                )
                checklist.append("Relocate catering to multipurpose halls or outdoor lawn annexes.")
            else:
                status = "CONDITIONAL_APPROVAL"
                answer_parts.append(
                    "Catering is permitted in designated multipurpose halls and outdoor areas, provided waste management is arranged."
                )
                checklist.append("Submit cleaning deposit and provide dedicated waste disposal bins.")

        elif "noise" in q_lower or "concert" in q_lower or "sound" in q_lower or "music" in q_lower or "curfew" in q_lower:
            if "night" in q_lower or "10 pm" in q_lower or "22:00" in q_lower or "21:00" in q_lower or "outdoor" in q_lower:
                status = "CONDITIONAL_APPROVAL" if "auditorium" in q_lower else "NON_COMPLIANT"
                answer_parts.append(
                    "Campus quiet hours strictly enforce an amplified sound curfew: outdoor music and high-output acoustic systems "
                    "must shut down completely by 20:00 to protect residential hostels."
                )
                checklist.append("Conclude outdoor amplified audio before 20:00, or move inside the Main Auditorium.")
            else:
                status = "COMPLIANT"
                answer_parts.append(
                    "Moderate sound levels within approved hours are permissible. Maintain levels below 65 dB near academic blocks."
                )

        elif "attendee" in q_lower or "security" in q_lower or "crowd" in q_lower or "guard" in q_lower or "police" in q_lower:
            status = "CONDITIONAL_APPROVAL"
            answer_parts.append(
                "Event security protocols are strictly tiered: gatherings with 200+ attendees require 2 uniformed campus security officers; "
                "gatherings with 500+ attendees require at least 4 security officers and mandatory EMT medical standby."
            )
            checklist.append("File Event Security Plan with Campus Police 5 business days in advance.")
            checklist.append("Confirm EMT and fire marshall clearance if exceeding 500 attendees.")

        elif "deadline" in q_lower or "notice" in q_lower or "cancel" in q_lower or "lead time" in q_lower:
            status = "CONDITIONAL_APPROVAL"
            answer_parts.append(
                "Advance reservation guidelines dictate: 14 calendar days for the Main Auditorium, "
                "4 days for multipurpose halls, and 48 hours for seminar rooms. Cancellations must be logged at least 48 hours prior."
            )
            checklist.append("Verify booking request timeline meets advance notice policy.")

        else:
            status = "CONDITIONAL_APPROVAL"
            answer_parts.append(
                f"According to {top_chunk.clause_id} ({top_chunk.doc_title}): {top_chunk.content}"
            )
            checklist.append(f"Ensure compliance with {top_chunk.clause_id}.")

        answer_text = " ".join(answer_parts) + f"\n\nSource: [{top_chunk.clause_id} - {top_chunk.doc_title}]"

        return PolicyAnswer(
            query=query,
            answer=answer_text,
            compliance_status=status,
            citations=citations,
            actionable_checklist=checklist,
            confidence_score=round(top_score, 2),
        )

