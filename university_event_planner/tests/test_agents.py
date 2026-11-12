from datetime import datetime, time
from app.services.agents import CoordinatorAgent
from app.services.search.state import EventSpec, VenueSpec


def dt(hour: int) -> datetime:
    return datetime(2026, 12, 1, hour, 0)


def test_coordinator_agent_workflow():
    venues = [
        VenueSpec(
            id=1,
            name="Main Auditorium",
            venue_type="indoor",
            capacity=1000,
            facilities=frozenset(["projector", "wifi", "audio", "stage"]),
            open_time=time(8, 0),
            close_time=time(22, 0),
            noise_allowed=True,
            catering_allowed=False,
        ),
        VenueSpec(
            id=2,
            name="Seminar Room A",
            venue_type="indoor",
            capacity=80,
            facilities=frozenset(["projector", "wifi"]),
            open_time=time(8, 0),
            close_time=time(20, 0),
            noise_allowed=False,
            catering_allowed=True,
        ),
    ]

    coordinator = CoordinatorAgent(venues=venues, existing_bookings=[])

    event = EventSpec(
        id=1,
        name="Annual Tech Keynote",
        attendees=600,
        start_time=dt(10),
        end_time=dt(13),
        required_facilities=frozenset(["stage", "audio"]),
        requires_catering=False,
        noise_level="medium",
    )

    plan = coordinator.plan_event(event)

    assert plan.is_feasible is True
    assert plan.assigned_venue_id == 1
    assert plan.assigned_venue_name == "Main Auditorium"
    assert len(plan.agent_dialogue) >= 5
    # Verify Coordinator, Scheduling, Policy, Logistics messages exist
    senders = {m.sender for m in plan.agent_dialogue}
    assert "CoordinatorAgent" in senders
    assert "SchedulingAgent" in senders
    assert "PolicyComplianceAgent" in senders
    assert "LogisticsAgent" in senders
    # Large crowd requirement (600 attendees) should trigger EMT / security action items
    assert any("security" in item.lower() or "emt" in item.lower() or "staging" in item.lower() for item in plan.action_items)


def test_multi_turn_negotiation_resolves_policy_veto():
    venues = [
        VenueSpec(
            id=10,
            name="Advanced Computing Lab",
            venue_type="indoor",
            capacity=40,
            facilities=frozenset(["computers", "wifi"]),
            open_time=time(8, 0),
            close_time=time(22, 0),
            catering_allowed=False,  # Policy prohibits catering in computer lab
        ),
        VenueSpec(
            id=20,
            name="Innovation Dining Seminar Hall",
            venue_type="indoor",
            capacity=70,
            facilities=frozenset(["wifi", "projector"]),
            open_time=time(8, 0),
            close_time=time(22, 0),
            catering_allowed=True,  # Catering allowed
        ),
    ]

    coordinator = CoordinatorAgent(venues=venues, existing_bookings=[], max_negotiation_rounds=3)

    event = EventSpec(
        id=2,
        name="Hackathon Lunch & Pitch",
        attendees=35,
        start_time=dt(12),
        end_time=dt(14),
        required_facilities=frozenset(["wifi"]),
        requires_catering=True,
        noise_level="low",
    )

    plan = coordinator.plan_event(event)

    # First candidate would be id=10 (capacity 40, waste 5)
    # But Policy vetoes id=10 for catering, so Coordinator re-negotiates and allocates id=20!
    assert plan.is_feasible is True
    assert plan.assigned_venue_id == 20
    assert plan.assigned_venue_name == "Innovation Dining Seminar Hall"
    # Ensure negotiation dialogue contains critique and retry
    critiques = [m for m in plan.agent_dialogue if m.message_type == "CRITIQUE"]
    assert len(critiques) > 0
    assert any("veto" in m.content.lower() or "policy" in m.content.lower() for m in critiques)
