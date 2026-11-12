from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel, ConfigDict

from app.db.session import get_db
from app.models import Booking, Facility, Venue
from app.schemas.scheduling import VenueOut

router = APIRouter()


class BookingCreate(BaseModel):
    venue_id: int | str
    start_time: datetime
    end_time: datetime
    status: str = "confirmed"


class BookingOut(BaseModel):
    id: int
    venue_id: int
    venue_name: str
    start_time: str
    end_time: str
    status: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/venues", response_model=list[VenueOut], tags=["venues"])
def list_venues(db: Session = Depends(get_db)):
    venues = db.scalars(select(Venue).options(selectinload(Venue.facilities))).all()
    return [
        VenueOut(
            id=v.id,
            name=v.name,
            venue_type=v.venue_type,
            capacity=v.capacity,
            building=v.building,
            facilities=sorted(f.name for f in v.facilities),
        )
        for v in venues
    ]


@router.get("/venues/{venue_id}", response_model=VenueOut, tags=["venues"])
def get_venue(venue_id: int, db: Session = Depends(get_db)):
    venue = db.scalar(
        select(Venue).where(Venue.id == venue_id).options(selectinload(Venue.facilities))
    )
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return VenueOut(
        id=venue.id,
        name=venue.name,
        venue_type=venue.venue_type,
        capacity=venue.capacity,
        building=venue.building,
        facilities=sorted(f.name for f in venue.facilities),
    )


@router.get("/bookings", response_model=list[BookingOut], tags=["bookings"])
def list_bookings(db: Session = Depends(get_db)):
    bookings = db.scalars(select(Booking).options(selectinload(Booking.venue))).all()
    return [
        BookingOut(
            id=b.id,
            venue_id=b.venue_id,
            venue_name=b.venue.name if b.venue else f"Venue {b.venue_id}",
            start_time=b.start_time.isoformat(),
            end_time=b.end_time.isoformat(),
            status=b.status,
        )
        for b in bookings
    ]


@router.post("/bookings", response_model=BookingOut, tags=["bookings"])
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    venue = None
    if isinstance(payload.venue_id, int) or (isinstance(payload.venue_id, str) and payload.venue_id.isdigit()):
        venue = db.scalar(select(Venue).where(Venue.id == int(payload.venue_id)))
    else:
        code_to_name = {
            "b34a": "Block 34 · Hall A",
            "b34b": "Block 34 · Hall B",
            "b32a": "Block 32 · Seminar 1",
            "b32b": "Block 32 · Seminar 2",
            "mall": "Uni Mall · Event Hall",
            "aud": "Main Auditorium",
            "gnd": "Open Ground",
        }
        target_name = code_to_name.get(str(payload.venue_id).lower(), str(payload.venue_id))
        venue = db.scalar(select(Venue).where(Venue.name.ilike(f"%{target_name}%")))

    if not venue:
        # Fallback to first venue
        venue = db.scalar(select(Venue))
        if not venue:
            raise HTTPException(status_code=404, detail="No venues registered in database")

    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be later than start_time")

    new_booking = Booking(
        venue_id=venue.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=payload.status,
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return BookingOut(
        id=new_booking.id,
        venue_id=new_booking.venue_id,
        venue_name=venue.name,
        start_time=new_booking.start_time.isoformat(),
        end_time=new_booking.end_time.isoformat(),
        status=new_booking.status,
    )


@router.delete("/bookings/{booking_id}", tags=["bookings"])
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.scalar(select(Booking).where(Booking.id == booking_id))
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return {"status": "deleted", "id": booking_id}
