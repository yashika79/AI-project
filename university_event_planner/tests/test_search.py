from datetime import datetime
from app.services.search import (
    EventSpec,
    VenueSpec,
    TimeSlot,
    solve_schedule,
    solve_csp,
    solve_astar,
    solve_greedy,
    solve_min_conflicts,
)


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 12, 1, hour, minute)


def sample_venues() -> list[VenueSpec]:
    return [
        VenueSpec(1, "Seminar Hall A", "indoor", 100, frozenset(["projector", "wifi"])),
        VenueSpec(2, "Main Auditorium", "indoor", 500, frozenset(["projector", "wifi", "audio", "stage"])),
        VenueSpec(3, "Computer Lab", "indoor", 40, frozenset(["computers", "wifi"])),
        VenueSpec(4, "Campus Lawn", "outdoor", 300, frozenset(["power"])),
    ]


def test_greedy_search():
    venues = sample_venues()
    events = [
        EventSpec(101, "AI Seminar", 80, dt(10), dt(12), frozenset(["projector"])),
        EventSpec(102, "Coding Contest", 35, dt(10), dt(13), frozenset(["computers"])),
    ]
    res = solve_greedy(events, venues)
    assert res.success is True
    assert len(res.assignments) == 2
    # Event 101 should pick Seminar Hall A (cap 100, waste 20) instead of Auditorium (cap 500)
    a101 = next(a for a in res.assignments if a.event_id == 101)
    assert a101.venue_id == 1
    # Event 102 should pick Computer Lab
    a102 = next(a for a in res.assignments if a.event_id == 102)
    assert a102.venue_id == 3


def test_csp_search_with_conflict():
    venues = sample_venues()
    # Two overlapping events that both need a 500-seat auditorium
    events = [
        EventSpec(201, "Keynote 1", 450, dt(10), dt(12), frozenset(["stage"])),
        EventSpec(202, "Keynote 2", 400, dt(11), dt(13), frozenset(["stage"])),
    ]
    # Only 1 venue has stage & capacity >= 400 (Main Auditorium). Since times overlap, both cannot be scheduled.
    res = solve_csp(events, venues)
    assert res.success is False
    assert len(res.unassigned_events) > 0


def test_csp_search_success_with_alternative_venues():
    venues = sample_venues()
    events = [
        EventSpec(301, "Workshop A", 70, dt(9), dt(11), frozenset(["projector", "wifi"])),
        EventSpec(302, "Workshop B", 85, dt(9), dt(11), frozenset(["projector", "wifi"])),
    ]
    # Both can be scheduled: one in Seminar Hall A (cap 100), one in Main Auditorium (cap 500)
    res = solve_csp(events, venues)
    assert res.success is True
    assert len(res.assignments) == 2
    venue_ids = {a.venue_id for a in res.assignments}
    assert venue_ids == {1, 2}


def test_astar_search_finds_optimal_waste():
    venues = sample_venues()
    events = [
        EventSpec(401, "Workshop A", 70, dt(14), dt(16), frozenset(["projector"])),
        EventSpec(402, "Keynote", 400, dt(14), dt(16), frozenset(["stage"])),
    ]
    res = solve_astar(events, venues)
    assert res.success is True
    assert len(res.assignments) == 2
    # Event 401 must get venue 1 (waste 30), Event 402 must get venue 2 (waste 100). Total waste 130.
    assert res.total_capacity_waste == 130


def test_min_conflicts_local_search():
    venues = sample_venues()
    events = [
        EventSpec(501, "Event 1", 30, dt(10), dt(12), frozenset(["wifi"])),
        EventSpec(502, "Event 2", 30, dt(10), dt(12), frozenset(["wifi"])),
        EventSpec(503, "Event 3", 30, dt(10), dt(12), frozenset(["wifi"])),
    ]
    res = solve_min_conflicts(events, venues)
    assert res.success is True
    assert len(res.assignments) == 3

