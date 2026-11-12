from __future__ import annotations

from datetime import datetime, time
from app.services.search.state import EventSpec, TimeSlot, VenueSpec


def dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 12, day, hour, minute)


def get_benchmark_venues() -> list[VenueSpec]:
    return [
        VenueSpec(1, "Main Auditorium", "indoor", 1200, frozenset(["projector", "wifi", "audio", "stage", "lighting"])),
        VenueSpec(2, "Science Lecture Theatre 1", "indoor", 250, frozenset(["projector", "wifi", "audio", "whiteboard"])),
        VenueSpec(3, "Science Lecture Theatre 2", "indoor", 150, frozenset(["projector", "wifi", "audio"])),
        VenueSpec(4, "Innovation Seminar Hall", "indoor", 90, frozenset(["projector", "wifi", "video_conferencing"])),
        VenueSpec(5, "Executive Conference Room", "indoor", 35, frozenset(["projector", "wifi", "video_conferencing", "catering_station"])),
        VenueSpec(6, "Computer Lab A", "indoor", 45, frozenset(["computers", "wifi", "projector"])),
        VenueSpec(7, "Central Amphitheatre", "outdoor", 600, frozenset(["stage", "power", "lighting"])),
        VenueSpec(8, "Campus Activity Lawn", "outdoor", 500, frozenset(["power", "open_space"])),
    ]


def get_scenario_events(scenario_name: str) -> list[EventSpec]:
    name = scenario_name.lower()
    
    if "light" in name:
        return [
            EventSpec(1, "AI Research Talk", 120, dt(1, 10), dt(1, 12), frozenset(["projector", "audio"])),
            EventSpec(2, "Python Hands-on Lab", 35, dt(1, 14), dt(1, 16), frozenset(["computers"])),
            EventSpec(3, "Faculty Senate Meeting", 25, dt(1, 11), dt(1, 13), frozenset(["video_conferencing"])),
            EventSpec(4, "Drama Society Rehearsal", 80, dt(1, 16), dt(1, 18), frozenset(["stage"])),
        ]

    elif "contested" in name or "prime" in name:
        # High contention for auditorium and lecture theatre at 10:00 - 12:00
        return [
            EventSpec(10, "University Keynote Address", 850, dt(2, 10), dt(2, 12), frozenset(["stage", "audio"]), priority=3),
            EventSpec(11, "Dean's Honor Convocation", 500, dt(2, 10), dt(2, 12), frozenset(["stage", "audio"]), priority=2),
            EventSpec(12, "Engineering Guest Lecture", 220, dt(2, 10), dt(2, 12), frozenset(["projector", "audio"])),
            EventSpec(13, "Data Science Seminar", 140, dt(2, 10), dt(2, 12), frozenset(["projector", "wifi"])),
            EventSpec(14, "Robotics Club Showcase", 80, dt(2, 10), dt(2, 12), frozenset(["power", "projector"])),
            EventSpec(15, "Student Council Debate", 85, dt(2, 10), dt(2, 12), frozenset(["audio"])),
        ]

    elif "fest" in name or "medium" in name:
        # Campus Fest with 12 events scheduled across two days
        return [
            EventSpec(20, "Inaugural Ceremony", 900, dt(3, 9), dt(3, 11), frozenset(["stage", "audio"]), priority=3),
            EventSpec(21, "Hackathon Kickoff", 200, dt(3, 11), dt(3, 13), frozenset(["wifi", "projector"])),
            EventSpec(22, "Competitive Coding Sprint", 40, dt(3, 11), dt(3, 15), frozenset(["computers", "wifi"])),
            EventSpec(23, "Alumni Networking Lunch", 30, dt(3, 12), dt(3, 14), frozenset(["video_conferencing"])),
            EventSpec(24, "Venture Pitch Competition", 80, dt(3, 14), dt(3, 16), frozenset(["projector", "wifi"])),
            EventSpec(25, "Rock Band Soundcheck", 400, dt(3, 15), dt(3, 17), frozenset(["stage", "power"])),
            EventSpec(26, "Evening Cultural Fest", 550, dt(3, 17), dt(3, 20), frozenset(["stage", "lighting"])),
            EventSpec(27, "Robotics Exhibition", 70, dt(3, 10), dt(3, 13), frozenset(["power"])),
            EventSpec(28, "Guest Author Reading", 130, dt(3, 13), dt(3, 15), frozenset(["audio", "projector"])),
            EventSpec(29, "Game Dev Workshop", 42, dt(3, 15), dt(3, 18), frozenset(["computers"])),
            EventSpec(30, "Closing Ceremony", 800, dt(4, 16), dt(4, 18), frozenset(["stage", "audio"])),
            EventSpec(31, "Awards Reception", 180, dt(4, 18), dt(4, 20), frozenset(["audio"])),
        ]

    else:
        # Stress test scenario (20 events)
        events = []
        for i in range(1, 21):
            day = 5 + (i % 2)
            hour = 9 + (i % 7)
            events.append(
                EventSpec(
                    id=100 + i,
                    name=f"Stress Event {i}",
                    attendees=30 + (i * 25) % 300,
                    start_time=dt(day, hour),
                    end_time=dt(day, hour + 2),
                    required_facilities=frozenset(["projector", "wifi"]) if i % 2 == 0 else frozenset(["audio"]),
                    priority=(i % 3) + 1,
                )
            )
        return events

