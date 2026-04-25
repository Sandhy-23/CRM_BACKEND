from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.calendar import CalendarEvent
from app.models.user import User
from app.utils.email import send_email
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/calendar")

class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: str = "Meeting"
    location: Optional[str] = None
    is_all_day: bool = False
    start_datetime: datetime
    end_datetime: datetime
    related_type: Optional[str] = None
    related_id: Optional[int] = None
    recurrence: str = "None"
    remind_before_minutes: int = 15
    status: str = "Planned"

def fix_datetime(dt):
    """Converts datetime/string with Z to naive datetime object."""
    return datetime.fromisoformat(str(dt).replace("Z", ""))

# ✅ Create Event (Correct Version)
@router.post("/events")
def create_event(data: CalendarEventCreate, db: Session = Depends(get_db)):
    try:
        # 🔥 Fix datetime (VERY IMPORTANT)
        start = fix_datetime(data.start_datetime)
        end = fix_datetime(data.end_datetime)

        # 🔥 Validate time
        if start >= end:
            raise HTTPException(status_code=400, detail="End time must be after start time")

        # 🔥 Validate related
        if data.related_type and not data.related_id:
            raise HTTPException(status_code=400, detail="related_id required")

        event = CalendarEvent(
            title=data.title,
            description=data.description,
            event_type=data.event_type,
            location=data.location,
            is_all_day=data.is_all_day,
            start_datetime=start,
            end_datetime=end,
            related_type=data.related_type,
            related_id=data.related_id,
            recurrence=data.recurrence,
            remind_before_minutes=data.remind_before_minutes,
            status=data.status
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        return event

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ Get Events
@router.get("/events")
def get_events(db: Session = Depends(get_db)):
    return db.query(CalendarEvent).all()

# ✅ UPDATE API
@router.put("/events/{id}")
def update_event(id: int, data: dict, db: Session = Depends(get_db)):
    event = db.query(CalendarEvent).filter(CalendarEvent.id == id).first()

    if not event:
        raise HTTPException(404, "Not found")

    for key, value in data.items():
        if key in ["start_datetime", "end_datetime"]:
            value = fix_datetime(value) if value else None
        setattr(event, key, value)

    db.commit()
    return event

# ✅ DELETE API
@router.delete("/events/{id}")
def delete_event(id: int, db: Session = Depends(get_db)):
    event = db.query(CalendarEvent).filter(CalendarEvent.id == id).first()

    if not event:
        raise HTTPException(404, "Not found")

    db.delete(event)
    db.commit()

    return {"message": "Deleted"}