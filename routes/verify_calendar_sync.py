from app import app
from extensions import db
from models.task import Task
from models.calendar_event import CalendarEvent
from datetime import datetime

def verify_calendar_sync():
    with app.app_context():
        print("\n--- 🕵️‍♀️ Verifying Calendar-Task Sync ---")
        
        # 1. Get the most recent calendar event
        last_event = CalendarEvent.query.order_by(CalendarEvent.id.desc()).first()
        
        if not last_event:
            print("❌ No calendar events found in DB.")
            return

        print(f"📅 Latest Event Found: '{last_event.title}' (ID: {last_event.id})")
        print(f"   - Start Time: {last_event.start_datetime}")

        # 2. Check if a corresponding task exists
        # We look for a task with source_type='calendar' and source_id=event.id
        task = Task.query.filter_by(source_type='calendar', source_id=last_event.id).first()

        if task:
            print(f"✅ SUCCESS: Found linked Task (ID: {task.id})")
            print(f"   - Title: {task.title}")
            print(f"   - Task Date: {task.task_date}")
            print(f"   - Task Time: {task.task_time}")
            print(f"   - Status: {task.status}")
        else:
            print("❌ FAILURE: No linked task found for this event.")
            print("   - Did you create this event AFTER applying the backend fix?")

if __name__ == "__main__":
    verify_calendar_sync()