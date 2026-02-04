from flask import Blueprint, request, jsonify
from extensions import db
from models.task import Task
from models.user import User
from routes.auth_routes import token_required
from models.activity_logger import log_activity
from datetime import datetime, timedelta
from sqlalchemy import text, event
from models.calendar_event import CalendarEvent

task_bp = Blueprint('tasks', __name__)

@task_bp.route('/api/tasks', methods=['POST'])
@token_required
def create_task(current_user):
    data = request.get_json()
    
    if not data.get('title'):
        return jsonify({'message': 'Title is required'}), 400

    # Parse Due Date
    due_date = None
    if data.get('due_date'):
        try:
            due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Validate Assigned User (Must be in same Org)
    assigned_to = data.get('assigned_to')
    if assigned_to:
        assignee = User.query.get(assigned_to)
        if not assignee:
            return jsonify({'message': 'Assigned user not found'}), 400
        if assignee.organization_id != current_user.organization_id:
            return jsonify({'message': 'Invalid assigned user: User belongs to a different organization'}), 400

    new_task = Task(
        title=data['title'],
        description=data.get('description'),
        due_date=due_date,
        priority=data.get('priority', 'Medium'),
        status='Pending',
        assigned_to=assigned_to,
        created_by=current_user.id,
        lead_id=data.get('lead_id'),
        deal_id=data.get('deal_id'),
        company_id=current_user.organization_id
    )

    db.session.add(new_task)
    db.session.commit()

    log_activity(
        module="task",
        action="created",
        description=f"Task '{new_task.title}' created.",
        related_id=new_task.id
    )

    return jsonify({'message': 'Task created successfully', 'task': new_task.to_dict()}), 201

@task_bp.route('/api/tasks/my', methods=['GET'])
@token_required
def get_my_tasks(current_user):
    tasks = Task.query.filter_by(
        assigned_to=current_user.id,
        company_id=current_user.organization_id
    ).order_by(Task.due_date.asc()).all()
    
    return jsonify([t.to_dict() for t in tasks]), 200

@task_bp.route('/api/leads/<int:lead_id>/tasks', methods=['GET'])
@token_required
def get_lead_tasks(current_user, lead_id):
    tasks = Task.query.filter_by(
        lead_id=lead_id,
        company_id=current_user.organization_id
    ).order_by(Task.created_at.desc()).all()
    
    return jsonify([t.to_dict() for t in tasks]), 200

@task_bp.route('/api/deals/<int:deal_id>/tasks', methods=['GET'])
@token_required
def get_deal_tasks(current_user, deal_id):
    tasks = Task.query.filter_by(
        deal_id=deal_id,
        company_id=current_user.organization_id
    ).order_by(Task.created_at.desc()).all()
    
    return jsonify([t.to_dict() for t in tasks]), 200

@task_bp.route('/api/tasks/<int:task_id>/complete', methods=['PUT'])
@token_required
def complete_task(current_user, task_id):
    task = Task.query.filter_by(
        id=task_id,
        company_id=current_user.organization_id
    ).first()

    if not task:
        return jsonify({'message': 'Task not found'}), 404

    # Permission Check: Assigned User, Creator, or Admin
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN'] and \
       task.assigned_to != current_user.id and \
       task.created_by != current_user.id:
        return jsonify({'message': 'Permission denied'}), 403

    task.status = 'Completed'
    db.session.commit()

    log_activity(
        module="task",
        action="completed",
        description=f"Task '{task.title}' marked as completed.",
        related_id=task.id
    )
    return jsonify({'message': 'Task marked as completed'}), 200

@task_bp.route('/api/calendar/task', methods=['POST'])
@token_required
def create_calendar_task(current_user):
    """
    Creates a Calendar Event AND a Task from the Calendar UI.
    Handles the specific payload sent by the frontend calendar widget.
    """
    # 1. Log the request body (Debug Step)
    data = request.get_json()
    print(f"[DEBUG] /api/calendar/task Body: {data}")

    title = data.get('title')
    start_datetime_str = data.get('start_datetime')
    end_datetime_str = data.get('end_datetime')
    description = data.get('description')
    event_type = data.get('event_type', 'Task')
    
    # 2. Validate required fields
    if not title or not start_datetime_str:
        return jsonify({'message': 'Title and Start Datetime are required'}), 400

    try:
        # 3. Parse Dates
        start_datetime = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
        if end_datetime_str:
            end_datetime = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
        else:
            end_datetime = start_datetime + timedelta(minutes=30)

        # 4. Create Calendar Event
        new_event = CalendarEvent(
            title=title,
            description=description,
            event_type=event_type,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            created_by=current_user.id,
            assigned_to=current_user.id, # Force assign to self
            company_id=current_user.organization_id
        )
        db.session.add(new_event)
        db.session.flush() # Get ID
        
        # 5. Auto-create Task
        task_date = start_datetime.date()
        task_time = start_datetime.time().strftime('%H:%M:%S')

        new_task = Task(
            title=title,
            description=description or f"Event: {title}",
            task_date=task_date,
            task_time=task_time,
            status='Pending',
            company_id=current_user.organization_id,
            assigned_to=current_user.id,
            created_by=current_user.id,
            due_date=task_date,
            source_type='calendar',
            source_id=new_event.id
        )
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            'message': 'Event and task created successfully',
            'event': new_event.to_dict(),
            'task': new_task.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"[FAIL] Calendar Task Create Error: {e}")
        return jsonify({'error': str(e)}), 500

# --- EVENT LISTENER: Auto-create Task from Calendar Event ---
# def create_task_from_calendar_event(mapper, connection, target):
#     """
#     Automatically creates a Task when a CalendarEvent is inserted.
#     Extracts date/time and links it via source_type/source_id.
#     """
#     if not target.start_datetime:
#         return
# 
#     try:
#         # Extract Date and Time from start_datetime
#         # Handle both string (ISO format) and datetime object
#         if isinstance(target.start_datetime, str):
#             dt = datetime.fromisoformat(target.start_datetime.replace('Z', '+00:00'))
#         else:
#             dt = target.start_datetime
#             
#         task_date = dt.date()
#         task_time = dt.time().strftime('%H:%M:%S')
# 
#         # Insert Task directly using SQL to avoid session conflicts during flush
#         sql = text("""
#             INSERT INTO tasks (
#                 title, description, task_date, task_time, 
#                 status, company_id, assigned_to, created_by, 
#                 due_date, created_at, source_type, source_id
#             ) VALUES (
#                 :title, :description, :task_date, :task_time, 
#                 'Pending', :company_id, :assigned_to, :created_by, 
#                 :due_date, :created_at, 'calendar', :source_id
#             )
#         """)
#         
#         connection.execute(sql, {
#             'title': target.title,
#             'description': target.description or f"Event: {target.title}",
#             'task_date': task_date,
#             'task_time': task_time,
#             'company_id': target.company_id,
#             'assigned_to': target.assigned_to,
#             'created_by': target.created_by,
#             'due_date': task_date,
#             'created_at': datetime.utcnow(),
#             'source_id': target.id
#         })
#         print(f"[INFO] Auto-created task for Event ID {target.id}")
#     except Exception as e:
#         print(f"[FAIL] Error auto-creating task from event: {e}")
# 
# # Register the listener
# event.listen(CalendarEvent, 'after_insert', create_task_from_calendar_event)