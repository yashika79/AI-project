from datetime import datetime, time
from app.services.rules import VenueRuleEngine
from app.services.search.state import EventSpec, VenueSpec, TimeSlot


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 12, 1, hour, minute)


def test_rule_engine_passes_valid_event():
    venue = VenueSpec(
        id=1,
        name="Auditorium",
        venue_type="indoor",
        capacity=500,
        facilities=frozenset(["projector", "wifi", "audio"]),
        open_time=time(8, 0),
        close_time=time(22, 0),
        noise_allowed=True,
        catering_allowed=False,
    )
    event = EventSpec(
        id=1,
        name="Tech Talk",
        attendees=250,
        start_time=dt(10),
        end_time=dt(12),
        required_facilities=frozenset(["projector"]),
        requires_catering=False,
        noise_level="low",
    )
    engine = VenueRuleEngine()
    report = engine.evaluate(event, venue, [])
    assert report.is_feasible is True
    assert len(report.hard_violations) == 0
    assert report.overall_compliance_score >= 90.0


def test_rule_engine_catches_capacity_and_catering_violations():
    venue = VenueSpec(
        id=2,
        name="Computer Lab",
        venue_type="indoor",
        capacity=30,
        facilities=frozenset(["computers"]),
        open_time=time(8, 0),
        close_time=time(20, 0),
        noise_allowed=False,
        catering_allowed=False,
    )
    event = EventSpec(
        id=2,
        name="Hackathon & Pizza",
        attendees=50,  # exceeds 30
        start_time=dt(18),
        end_time=dt(21),  # exceeds 20:00
        required_facilities=frozenset(["computers"]),
        requires_catering=True,  # catering forbidden in lab
        noise_level="high",  # noise forbidden in lab
    )
    engine = VenueRuleEngine()
    report = engine.evaluate(event, venue, [])
    assert report.is_feasible is False
    assert any("Capacity violation" in v for v in report.hard_violations)
    assert any("Operating hours violation" in v for v in report.hard_violations)
    assert any("Catering requested" in w for w in report.soft_warnings)
    assert any("High noise" in w for w in report.soft_warnings)

