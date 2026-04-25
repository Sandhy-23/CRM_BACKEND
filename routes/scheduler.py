from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.calendar import CalendarEvent
from app.utils.email import send_email
import time

def run_scheduler():
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()

            events = db.query(CalendarEvent).all()

            for e in events:
                if not e.remind_before_minutes:
                    continue

                remind_time = e.start_datetime - timedelta(minutes=e.remind_before_minutes)

                if now >= remind_time and now <= remind_time + timedelta(minutes=1):
                    print(f"Reminder: {e.title} starts soon")
        finally:
            db.close()
        
        time.sleep(60)