from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

venue_facilities = Table(
    "venue_facilities",
    Base.metadata,
    Column("venue_id", ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True),
    Column("facility_id", ForeignKey("facilities.id", ondelete="CASCADE"), primary_key=True),
)


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    venue_type: Mapped[str] = mapped_column(String(30))  # indoor / outdoor
    capacity: Mapped[int] = mapped_column(Integer)
    building: Mapped[str | None] = mapped_column(String(120), nullable=True)
    facilities: Mapped[list["Facility"]] = relationship(
        secondary=venue_facilities, back_populates="venues"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="venue")


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    venues: Mapped[list[Venue]] = relationship(
        secondary=venue_facilities, back_populates="facilities"
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_name: Mapped[str] = mapped_column(String(160))
    attendees: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    required_facilities: Mapped[list["EventFacility"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class EventFacility(Base):
    __tablename__ = "event_facilities"

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), primary_key=True)
    event: Mapped[Event] = relationship(back_populates="required_facilities")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    venue: Mapped[Venue] = relationship(back_populates="bookings")
