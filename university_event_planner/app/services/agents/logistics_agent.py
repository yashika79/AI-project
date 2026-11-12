from __future__ import annotations

from app.services.agents.base import AgentMessage
from app.services.search.state import EventSpec, VenueSpec


class LogisticsAgent:
    name = "LogisticsAgent"
    role = "Facilities, Audio-Visual & Buffer Operations Manager"

    def process(self, message: AgentMessage) -> AgentMessage:
        event: EventSpec | None = message.data.get("event_spec")
        venue: VenueSpec | None = message.data.get("venue_spec")

        if not event or not venue:
            return AgentMessage(
                sender=self.name,
                recipient=message.sender,
                message_type="REJECT",
                content="Logistics review requires both event and venue specifications.",
            )

        checklist: list[str] = []
        required_buffer = event.setup_buffer_minutes

        # Compute recommended buffer dynamically
        if event.attendees >= 500 or "stage" in event.required_facilities:
            required_buffer = max(required_buffer, 45)
            checklist.append("Deploy staging crew 45 minutes prior for audio soundcheck and lighting.")
        elif event.attendees >= 200:
            required_buffer = max(required_buffer, 30)
            checklist.append("Conduct 30-minute pre-event entry verification setup.")
        else:
            checklist.append("Standard 15-minute equipment turn-around buffer active.")

        # Facility verification
        matched_facilities = sorted(list(event.required_facilities & venue.facilities))
        extra_facilities = sorted(list(venue.facilities - event.required_facilities))

        if "projector" in event.required_facilities:
            checklist.append("IT Media Center notified for projector input testing (HDMI/DisplayPort).")
        if "wifi" in event.required_facilities:
            checklist.append("Campus IT guest Wi-Fi provisioning confirmed.")
        if event.requires_catering:
            checklist.append("Facilities Management dispatched for waste disposal bins and recycling stations.")

        return AgentMessage(
            sender=self.name,
            recipient=message.sender,
            message_type="APPROVAL",
            content=(
                f"Logistics clearance approved. Matched facilities: {', '.join(matched_facilities) or 'none'}. "
                f"Required operational buffer: {required_buffer} minutes. Action items logged."
            ),
            data={
                "buffer_minutes": required_buffer,
                "matched_facilities": matched_facilities,
                "additional_facilities": extra_facilities,
                "logistics_checklist": checklist,
            },
        )

