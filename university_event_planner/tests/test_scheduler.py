from datetime import datetime

from app.services.scheduler import VenueCandidate, ExistingBooking, recommend_venues


def dt(hour: int) -> datetime:
    return datetime(2026, 12, 1, hour, 0)


def test_filters_capacity_and_facilities_and_sorts_by_capacity_waste():
    venues = [
        VenueCandidate(1, "Large", "indoor", 200, {"projector", "wifi"}),
        VenueCandidate(2, "Right-sized", "indoor", 90, {"projector", "wifi"}),
        VenueCandidate(3, "Too-small", "indoor", 40, {"projector", "wifi"}),
        VenueCandidate(4, "No-wifi", "indoor", 100, {"projector"}),
    ]
    result, rejected = recommend_venues(
        venues, [], 75, dt(10), dt(12), {"projector", "wifi"}
    )
    assert [v.name for v in result] == ["Right-sized", "Large"]
    assert rejected == 2


def test_overlapping_booking_blocks_venue_but_adjacent_booking_does_not():
    venues = [VenueCandidate(1, "Room", "indoor", 100, {"wifi"})]
    bookings = [ExistingBooking(1, dt(10), dt(11))]
    blocked, _ = recommend_venues(venues, bookings, 50, dt(10), dt(12), {"wifi"})
    adjacent, _ = recommend_venues(venues, bookings, 50, dt(11), dt(12), {"wifi"})
    assert blocked == []
    assert len(adjacent) == 1
