from flask import Blueprint, request, jsonify
from extensions import db
from routes.auth_routes import token_required
from models.calendar_event import CalendarEvent
from models.reminder import Reminder
from models.task import Task
from models.activity_logger import log_activity
from datetime import datetime, timedelta

calendar_bp = Blueprint('calendar', __name__)

# 🔥 ROLE-BASED ACCESS (NO company_id)
def get_event_query(current_user):
    query = CalendarEvent.query

    if current_user.role == 'Super Admin':
        return query

    if current_user.role == 'Admin':
        return query

    return query.filter(CalendarEvent.created_by == current_user.id)


# ✅ CREATE EVENT
@calendar_bp.route('/calendar/events', methods=['POST'])
@token_required
def create_event(current_user):
    try:
        data = request.get_json()

        # 🔥 Validation
        required_fields = ["title", "start_datetime", "end_datetime"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        # 🔥 Datetime parsing
        try:
            start_datetime = datetime.fromisoformat(
                data['start_datetime'].replace('Z', '+00:00')
            )
            end_datetime = datetime.fromisoformat(
                data['end_datetime'].replace('Z', '+00:00')
            )
        except:
            return jsonify({"error": "Invalid datetime format"}), 400

        # 🔥 Create Event (NO company_id)
        new_event = CalendarEvent(
            title=data['title'],
            description=data.get('description'),
            event_type=data.get('event_type'),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            related_type=data.get('related_type'),
            related_id=data.get('related_id'),
            created_by=current_user.id
        )

        db.session.add(new_event)
        db.session.flush()

        # 🔥 Auto-create Task
        try:
            new_task = Task(
                title=new_event.title,
                description=new_event.description or f"Event: {new_event.title}",
                created_by=current_user.id,
                due_date=start_datetime.date()
            )
            db.session.add(new_task)
        except Exception as e:
            print("Task creation failed:", e)

        # 🔥 Reminder
        remind_before = data.get("remind_before_minutes")
        if remind_before:
            try:
                remind_at = start_datetime - timedelta(minutes=int(remind_before))

                reminder = Reminder(
                    event_id=new_event.id,
                    remind_at=remind_at,
                    user_id=current_user.id
                )
                db.session.add(reminder)
            except Exception as e:
                print("Reminder error:", e)

        db.session.commit()

        log_activity(
            module="calendar",
            action="created",
            description=f"Event created: {new_event.title}",
            related_id=new_event.id
        )

        return jsonify({
            "message": "Event created",
            "event": {
                "id": new_event.id,
                "title": new_event.title,
                "start_datetime": new_event.start_datetime.isoformat(),
                "end_datetime": new_event.end_datetime.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print("CREATE EVENT ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ✅ GET EVENTS
@calendar_bp.route('/calendar/events', methods=['GET'])
@token_required
def get_events(current_user):
    try:
        events = get_event_query(current_user) \
            .order_by(CalendarEvent.start_datetime.asc()) \
            .all()

        result = []
        for e in events:
            result.append({
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "start_datetime": e.start_datetime.isoformat() if e.start_datetime else None,
                "end_datetime": e.end_datetime.isoformat() if e.end_datetime else None,
                "event_type": e.event_type
            })

        return jsonify(result), 200

    except Exception as e:
        print("GET EVENTS ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ✅ GET TODAY REMINDERS
@calendar_bp.route('/reminders/today', methods=['GET'])
@token_required
def get_today_reminders(current_user):
    try:
        now = datetime.utcnow()

        reminders = Reminder.query.filter(
            Reminder.is_sent == False,
            Reminder.remind_at <= now,
            Reminder.user_id == current_user.id
        ).order_by(Reminder.remind_at.asc()).all()

        return jsonify([{
            "id": r.id,
            "event_id": r.event_id,
            "remind_at": r.remind_at.isoformat() if r.remind_at else None,
            "user_id": r.user_id,
            "is_sent": r.is_sent
        } for r in reminders]), 200

    except Exception as e:
        print("REMINDER FETCH ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ✅ MARK REMINDER SENT
@calendar_bp.route('/reminders/<int:reminder_id>/sent', methods=['PUT'])
@token_required
def mark_reminder_sent(current_user, reminder_id):
    try:
        reminder = Reminder.query.filter_by(
            id=reminder_id,
            user_id=current_user.id
        ).first()

        if not reminder:
            return jsonify({"error": "Reminder not found"}), 404

        reminder.is_sent = True
        db.session.commit()

        log_activity(
            module="reminder",
            action="completed",
            description=f"Reminder sent for event {reminder.event_id}",
            related_id=reminder.id
        )

        return jsonify({"message": "Reminder marked as sent"}), 200

    except Exception as e:
        db.session.rollback()
        print("REMINDER UPDATE ERROR:", e)
        return jsonify({"error": str(e)}), 500