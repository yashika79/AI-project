from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from typing import Literal

IntentType = Literal["PLAN_EVENT", "POLICY_QUERY", "INSPECT_VENUES", "BENCHMARK", "GENERAL"]
AlgorithmRoute = Literal["CSP", "ASTAR", "RAG", "LOGISTICS_ONLY", "NONE"]


@dataclass
class ExtractedEventIntent:
    event_name: str
    attendees: int
    start_time: datetime
    end_time: datetime
    required_facilities: list[str] = field(default_factory=list)
    preferred_venue_type: str | None = None
    priority: int = 1
    noise_level: str = "low"
    requires_catering: bool = False
    setup_buffer_minutes: int = 15
    optimization_requested: bool = False


@dataclass
class NLUParseResult:
    raw_query: str
    intent: IntentType
    algorithm_route: AlgorithmRoute
    routing_reason: str
    extracted_event: ExtractedEventIntent | None = None
    policy_query: str | None = None
    venue_filter: dict | None = None


class IntentParser:
    """Deterministic, grounded Natural Language Understanding engine.
    
    Extracts intents, entities (attendees, dates, equipment), and determines
    whether the Orchestrator should route to CSP (hard constraints),
    A* (optimization), Policy RAG (rules), or Sub-Agents.
    """

    FACILITY_KEYWORDS = {
        "projector": ["projector", "screen", "slides", "display"],
        "wifi": ["wifi", "wi-fi", "internet", "network"],
        "audio": ["audio", "sound", "microphone", "mic", "speakers", "pa system"],
        "stage": ["stage", "podium", "platform"],
        "computers": ["computer", "computers", "workstation", "pc", "lab pc", "coding"],
        "video_conferencing": ["zoom", "teams", "video call", "video conferencing", "webinar"],
        "power": ["power", "high voltage", "generators", "rig"],
        "lighting": ["lighting", "lights", "stage light", "spotlight"],
    }

    POLICY_TRIGGERS = [
        "can we", "can a", "is it allowed", "is it permitted", "policy", "rule", "rules",
        "allowed", "forbidden", "prohibited", "curfew", "quiet hours", "guideline",
        "guidelines", "regulations", "deadline", "cancellation", "deposit", "exemption",
        "security requirement", "how many guards", "how many security"
    ]

    OPTIMIZATION_TRIGGERS = [
        "optimal", "best fit", "minimize waste", "least waste", "optimize", "most efficient",
        "closest size", "best match", "energy", "walking distance", "ideal"
    ]

    BENCHMARK_TRIGGERS = [
        "benchmark", "evaluate", "compare algorithms", "compare ai", "run benchmark",
        "performance test"
    ]

    VENUE_INSPECTION_TRIGGERS = [
        "show venues", "list venues", "what venues", "available venues", "all venues",
        "hall directory", "venue list", "show me all halls", "rooms"
    ]

    def parse(self, text: str) -> NLUParseResult:
        query = text.strip()
        q_lower = query.lower()

        # 1. Detect Benchmark Intent
        if any(b in q_lower for b in self.BENCHMARK_TRIGGERS):
            return NLUParseResult(
                raw_query=query,
                intent="BENCHMARK",
                algorithm_route="NONE",
                routing_reason="User explicitly requested an AI algorithm comparative benchmark.",
            )

        # 2. Detect Policy RAG Intent
        is_explicit_policy = any(q_lower.startswith(t) or f" {t} " in f" {q_lower} " for t in self.POLICY_TRIGGERS)
        is_question = "?" in query or q_lower.startswith("what ") or q_lower.startswith("can ") or q_lower.startswith("is ") or q_lower.startswith("how ")
        has_direct_booking_command = any(k in q_lower for k in ["i need a", "i want to book", "please schedule", "reserve a", "plan an event for", "allocate a hall", "allocate a room"])

        if (is_explicit_policy or (is_question and not has_direct_booking_command)):
            return NLUParseResult(
                raw_query=query,
                intent="POLICY_QUERY",
                algorithm_route="RAG",
                routing_reason="User is inquiring about institutional campus policies, acoustic limits, catering rules, or security thresholds. Routing directly to Policy RAG.",
                policy_query=query,
            )

        # 3. Detect Venue Directory Inspection Intent
        if any(v in q_lower for v in self.VENUE_INSPECTION_TRIGGERS) and not any(k in q_lower for k in ["people", "attendees", "book for", "schedule"]):
            return NLUParseResult(
                raw_query=query,
                intent="INSPECT_VENUES",
                algorithm_route="NONE",
                routing_reason="User requested the directory of campus facilities and venue specifications.",
                venue_filter={"search": query},
            )

        # 4. Detect Event Planning Intent (or Default to Planning)
        extracted = self._extract_event_details(query)
        
        # Determine Algorithm Routing
        if extracted.optimization_requested:
            route: AlgorithmRoute = "ASTAR"
            reason = (
                "Orchestrator selected A* Heuristic Search: User requested optimization (minimal capacity waste / best fit). "
                "A* computes an admissible lower-bound heuristic h(n) <= h*(n) to find the provably minimal waste venue."
            )
        else:
            route: AlgorithmRoute = "CSP"
            reason = (
                f"Orchestrator selected CSP (Constraint Satisfaction Problem): The request imposes hard feasibility constraints "
                f"(capacity >= {extracted.attendees}, facilities: {extracted.required_facilities or 'standard'}, zero temporal collisions). "
                f"CSP Backtracking with MRV, LCV, and Forward Checking guarantees sound, conflict-free assignments."
            )

        return NLUParseResult(
            raw_query=query,
            intent="PLAN_EVENT",
            algorithm_route=route,
            routing_reason=reason,
            extracted_event=extracted,
        )

    def _extract_event_details(self, text: str) -> ExtractedEventIntent:
        q_lower = text.lower()

        # Extract Attendees count
        attendees = 50  # Default reasonable crowd
        attendee_match = re.search(r"(\d+)\s*(people|attendees|students|participants|members|guests|seats|capacity|persons)", q_lower)
        if attendee_match:
            attendees = int(attendee_match.group(1))
        else:
            # Fallback check standalone numbers like "for 200"
            for_num_match = re.search(r"for\s+(\d+)", q_lower)
            if for_num_match:
                attendees = int(for_num_match.group(1))

        # Extract Required Facilities
        facilities: set[str] = set()
        for fac_key, aliases in self.FACILITY_KEYWORDS.items():
            if any(alias in q_lower for alias in aliases):
                facilities.add(fac_key)

        # Extract Preferred Venue Type
        venue_type = None
        if "outdoor" in q_lower or "lawn" in q_lower or "amphitheatre" in q_lower or "ground" in q_lower:
            venue_type = "outdoor"
        elif "indoor" in q_lower or "hall" in q_lower or "auditorium" in q_lower or "room" in q_lower or "lab" in q_lower:
            venue_type = "indoor"

        # Catering Detection
        requires_catering = any(c in q_lower for c in ["pizza", "catering", "food", "lunch", "dinner", "buffet", "snacks", "drinks", "refreshments"])

        # Noise Level Detection
        noise_level = "low"
        if any(n in q_lower for n in ["concert", "band", "loud", "dj", "party", "music fest", "live sound", "high noise"]):
            noise_level = "high"
        elif any(n in q_lower for n in ["microphone", "qa", "debate", "talk"]):
            noise_level = "medium"

        # Event Priority
        priority = 1
        if any(p in q_lower for p in ["convocation", "exam", "board of trustees", "commencement", "institutional"]):
            priority = 3
        elif any(p in q_lower for p in ["department", "faculty", "conference", "symposium", "academic"]):
            priority = 2

        # Optimization Flag
        optimization = any(o in q_lower for o in self.OPTIMIZATION_TRIGGERS)

        # Dates & Times Calculation
        now = datetime.now()
        start_date = now + timedelta(days=1)  # Default tomorrow

        if "today" in q_lower:
            start_date = now
        elif "next thursday" in q_lower:
            days_ahead = (3 - now.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_date = now + timedelta(days=days_ahead)
        elif "next friday" in q_lower:
            days_ahead = (4 - now.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_date = now + timedelta(days=days_ahead)
        elif "next monday" in q_lower:
            days_ahead = (0 - now.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_date = now + timedelta(days=days_ahead)
        elif "weekend" in q_lower or "saturday" in q_lower:
            days_ahead = (5 - now.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_date = now + timedelta(days=days_ahead)

        # Time extraction (e.g. 2pm to 5pm, 10:00 to 12:00, morning, evening)
        start_hour = 10
        end_hour = 12

        time_range_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to|-)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", q_lower)
        if time_range_match:
            h1 = int(time_range_match.group(1))
            m1 = int(time_range_match.group(2) or 0)
            ampm1 = time_range_match.group(3)

            h2 = int(time_range_match.group(4))
            m2 = int(time_range_match.group(5) or 0)
            ampm2 = time_range_match.group(6)

            if ampm1 == "pm" and h1 < 12:
                h1 += 12
            if ampm2 == "pm" and h2 < 12:
                h2 += 12
            elif not ampm2 and h2 < 8 and h1 >= 12:
                h2 += 12  # e.g. "2pm to 5" means 2pm to 5pm

            start_hour, end_hour = h1, max(h1 + 1, h2)
        elif "afternoon" in q_lower or "2pm" in q_lower or "14:00" in q_lower:
            start_hour, end_hour = 14, 16
        elif "evening" in q_lower or "5pm" in q_lower or "17:00" in q_lower:
            start_hour, end_hour = 17, 19
        elif "morning" in q_lower:
            start_hour, end_hour = 9, 11

        start_time = datetime(start_date.year, start_date.month, start_date.day, start_hour, 0)
        end_time = datetime(start_date.year, start_date.month, start_date.day, end_hour, 0)

        # Infer Clean Event Name
        name = "Campus Event"
        name_match = re.search(r"(?:plan|host|organize|schedule|for)\s+(?:a|an)?\s*([a-zA-Z0-9\s&'-]{3,40}?)(?:\s+for|\s+with|\s+on|\s+at|\s+next|\.|$)", text, re.IGNORECASE)
        if name_match:
            candidate_name = name_match.group(1).strip()
            if len(candidate_name) > 3 and not candidate_name.lower().startswith("hall") and not candidate_name.lower().startswith("room"):
                name = candidate_name.title()

        if name == "Campus Event":
            if "hackathon" in q_lower:
                name = "Campus Hackathon"
            elif "seminar" in q_lower or "lecture" in q_lower:
                name = "Guest Lecture Seminar"
            elif "workshop" in q_lower:
                name = "Hands-on Technical Workshop"
            elif "symposium" in q_lower or "conference" in q_lower:
                name = "Academic Symposium"
            elif "concert" in q_lower or "fest" in q_lower:
                name = "Cultural Music Festival"
            elif "meeting" in q_lower:
                name = "Departmental Meeting"

        return ExtractedEventIntent(
            event_name=name,
            attendees=attendees,
            start_time=start_time,
            end_time=end_time,
            required_facilities=sorted(list(facilities)),
            preferred_venue_type=venue_type,
            priority=priority,
            noise_level=noise_level,
            requires_catering=requires_catering,
            setup_buffer_minutes=15,
            optimization_requested=optimization,
        )
