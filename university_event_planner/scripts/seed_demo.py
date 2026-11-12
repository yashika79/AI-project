from datetime import datetime, timedelta
from sqlalchemy import select

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models import Facility, Venue, Booking

# Lovely Professional University (LPU) Campus Venues Topology
LPU_CAMPUS_VENUES = [
    {
        "name": "Block 34 · Hall A",
        "venue_type": "indoor",
        "capacity": 200,
        "building": "Block 34",
        "facilities": ["projector", "wifi", "audio", "whiteboard", "mic"],
    },
    {
        "name": "Block 34 · Hall B",
        "venue_type": "indoor",
        "capacity": 200,
        "building": "Block 34",
        "facilities": ["projector", "wifi", "audio", "whiteboard", "mic"],
    },
    {
        "name": "Block 32 · Seminar 1",
        "venue_type": "indoor",
        "capacity": 80,
        "building": "Block 32",
        "facilities": ["projector", "wifi", "video_conferencing", "audio"],
    },
    {
        "name": "Block 32 · Seminar 2",
        "venue_type": "indoor",
        "capacity": 80,
        "building": "Block 32",
        "facilities": ["projector", "wifi", "video_conferencing", "audio"],
    },
    {
        "name": "Uni Mall · Event Hall",
        "venue_type": "indoor",
        "capacity": 400,
        "building": "Uni Mall",
        "facilities": ["stage", "lighting", "audio", "catering_station"],
    },
    {
        "name": "Main Auditorium",
        "venue_type": "indoor",
        "capacity": 1500,
        "building": "Main Auditorium",
        "facilities": ["projector", "wifi", "audio", "stage", "lighting", "green_room"],
    },
    {
        "name": "Open Ground",
        "venue_type": "outdoor",
        "capacity": 5000,
        "building": "Open Ground",
        "facilities": ["stage", "power", "lighting", "open_space"],
    },
    {
        "name": "Robotics Lab · Block 38",
        "venue_type": "indoor",
        "capacity": 45,
        "building": "Block 38",
        "facilities": ["computers", "wifi", "projector", "power"],
    },
    {
        "name": "Executive Conference Room · Block 30",
        "venue_type": "indoor",
        "capacity": 35,
        "building": "Block 30",
        "facilities": ["projector", "wifi", "video_conferencing", "catering_station"],
    },
]


def seed_database():
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        facilities_by_name = {
            f.name: f for f in db.scalars(select(Facility)).all()
        }

        for item in LPU_CAMPUS_VENUES:
            existing_venue = db.scalar(
                select(Venue).where(Venue.name == item["name"])
            )
            if existing_venue:
                continue

            venue = Venue(
                name=item["name"],
                venue_type=item["venue_type"],
                capacity=item["capacity"],
                building=item["building"],
            )

            for fac_name in item["facilities"]:
                facility = facilities_by_name.get(fac_name)
                if facility is None:
                    facility = Facility(name=fac_name)
                    db.add(facility)
                    facilities_by_name[fac_name] = facility
                venue.facilities.append(facility)

            db.add(venue)

        db.commit()

        # Seed sample confirmed bookings for testing collision detection
        now = datetime.now()
        tomorrow_10am = datetime(now.year, now.month, now.day, 10, 0) + timedelta(days=1)
        tomorrow_12pm = tomorrow_10am + timedelta(hours=2)

        main_aud = db.scalar(select(Venue).where(Venue.name.ilike("%Auditorium%")))
        if main_aud:
            existing_b = db.scalar(select(Booking).where(Booking.venue_id == main_aud.id))
            if not existing_b:
                sample_booking = Booking(
                    venue_id=main_aud.id,
                    start_time=tomorrow_10am,
                    end_time=tomorrow_12pm,
                    status="confirmed",
                )
                db.add(sample_booking)
                db.commit()

        print(f"Database seeded with {len(LPU_CAMPUS_VENUES)} Lovely Professional University venues and initial bookings.")


if __name__ == "__main__":
    seed_database()
