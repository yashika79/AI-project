from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VenueCandidate:
    id: int
    name: str
    venue_type: str
    capacity: int
    facilities: set[str]


@dataclass(frozen=True)
class ExistingBooking:
    venue_id: int
    start_time: datetime
    end_time: datetime
    status: str = "confirmed"


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    # Half-open intervals: an event ending at 11:00 does not conflict with one
    # starting at 11:00.
    return start_a < end_b and start_b < end_a


def recommend_venues(
    venues: list[VenueCandidate],
    bookings: list[ExistingBooking],
    attendees: int,
    start_time: datetime,
    end_time: datetime,
    required_facilities: set[str],
    preferred_venue_type: str | None = None,
) -> tuple[list[VenueCandidate], int]:
    """Return feasible venues, ranked by smallest capacity waste.

    Hard constraints: capacity, facilities, no overlapping active booking.
    Preferred venue type is treated as a filter only when explicitly supplied.
    """
    feasible: list[VenueCandidate] = []
    rejected = 0

    for venue in venues:
        active_conflict = any(
            b.venue_id == venue.id
            and b.status in {"confirmed", "approved"}
            and overlaps(start_time, end_time, b.start_time, b.end_time)
            for b in bookings
        )
        valid = (
            venue.capacity >= attendees
            and required_facilities.issubset(venue.facilities)
            and not active_conflict
            and (preferred_venue_type is None or venue.venue_type == preferred_venue_type)
        )
        if valid:
            feasible.append(venue)
        else:
            rejected += 1

    feasible.sort(key=lambda v: (v.capacity - attendees, v.name.lower()))
    return feasible, rejected
