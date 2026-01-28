from flask import Blueprint, request, jsonify
from extensions import db
from routes.auth_routes import token_required
from models.user import User
from models.calendar_event import CalendarEvent
from models.reminder import Reminder
from datetime import datetime, timedelta
from sqlalchemy import or_
from utils.activity_logger import log_activity

calendar_bp = Blueprint('calendar', __name__)

def get_event_query(current_user):
    """Enforce Role Based Access Control for Calendar Events."""
    query = CalendarEvent.query

    if current_user.role == 'SUPER_ADMIN':
        return query
    
    query = query.filter_by(company_id=current_user.organization_id)

    if current_user.role == 'ADMIN':
        return query
    
    return query.filter(
        or_(
            CalendarEvent.created_by == current_user.id,
            CalendarEvent.assigned_to == current_user.id
        )
    )

@calendar_bp.route('/calendar/events', methods=['POST'])
@token_required
def create_event(current_user):
    data = request.get_json()
    title = data.get('title')
    start_datetime_str = data.get('start_datetime')

    if not title or not start_datetime_str:
        return jsonify({'error': 'title and start_datetime are required'}), 400

    try:
        start_datetime = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
        end_datetime = datetime.fromisoformat(data['end_datetime'].replace('Z', '+00:00')) if data.get('end_datetime') else None
    except ValueError:
        return jsonify({'error': 'Invalid datetime format. Use ISO 8601 format.'}), 400

    new_event = CalendarEvent(
        title=title,
        description=data.get('description'),
        event_type=data.get('event_type'),
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        related_type=data.get('related_type'),
        related_id=data.get('related_id'),
        created_by=current_user.id,
        assigned_to=data.get('assigned_to', current_user.id),
        company_id=current_user.organization_id
    )

    try:
        db.session.add(new_event)
        db.session.flush() # Flush to get new_event.id for the reminder

        remind_before_minutes = data.get('remind_before_minutes')
        if remind_before_minutes:
            try:
                remind_at = start_datetime - timedelta(minutes=int(remind_before_minutes))
                new_reminder = Reminder(
                    event_id=new_event.id,
                    remind_at=remind_at,
                    user_id=new_event.assigned_to,
                    company_id=current_user.organization_id
                )
                db.session.add(new_reminder)
            except (ValueError, TypeError) as e:
                # Don't let a bad reminder value stop the event creation, but log it.
                print(f"⚠️ Could not create reminder for event. Invalid 'remind_before_minutes' value. Error: {e}")

        db.session.commit()
        print("✅ DATA COMMITTED: Calendar event and/or reminder created.")
        log_activity(
            module="calendar",
            action="created",
            description=f"Event created: '{new_event.title}'",
            related_id=new_event.id
        )
        return jsonify({'message': 'Event created successfully', 'event': new_event.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR in create_event: {str(e)}")
        return jsonify({'error': 'Database error while creating event', 'message': str(e)}), 500

@calendar_bp.route('/calendar/events', methods=['GET'])
@token_required
def get_events(current_user):
    base_query = get_event_query(current_user)
    events = base_query.order_by(CalendarEvent.start_datetime.asc()).all()
    
    return jsonify([e.to_dict() for e in events]), 200

@calendar_bp.route('/reminders/today', methods=['GET'])
@token_required
def get_today_reminders(current_user):
    now = datetime.utcnow()
    
    query = Reminder.query.filter(
        Reminder.is_sent == False,
        Reminder.remind_at <= now,
        Reminder.user_id == current_user.id,
        Reminder.company_id == current_user.organization_id
    )

    reminders = query.order_by(Reminder.remind_at.asc()).all()
    return jsonify([r.to_dict() for r in reminders]), 200

@calendar_bp.route('/reminders/<int:reminder_id>/sent', methods=['PUT'])
@token_required
def mark_reminder_sent(current_user, reminder_id):
    # Find the reminder by its ID, but scoped to the user's company for security.
    # This allows Admins to mark reminders for others in the same organization.
    reminder = Reminder.query.filter_by(
        id=reminder_id, company_id=current_user.organization_id
    ).first()

    if not reminder:
        return jsonify({'error': 'Reminder not found or permission denied'}), 404

    try:
        reminder.is_sent = True
        db.session.commit()
        print("✅ DATA COMMITTED: Reminder marked as sent.")
        log_activity(
            module="reminder",
            action="completed",
            description=f"Reminder marked as sent for event ID: {reminder.event_id}",
            related_id=reminder.id
        )
        return jsonify({'message': 'Reminder marked as sent'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR in mark_reminder_sent: {str(e)}")
        return jsonify({'error': 'Database error while updating reminder', 'message': str(e)}), 500