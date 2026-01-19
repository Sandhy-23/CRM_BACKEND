from flask import Blueprint, request, jsonify
from routes.auth_routes import token_required
from models.crm import Lead, Activity
from models.task import Task
from models.activity_log import ActivityLog
from models.user import User
from extensions import db
from datetime import datetime

quick_actions_bp = Blueprint('quick_actions', __name__)

def log_activity(user_id, action, entity_type=None, entity_id=None):
    """Helper to log activity to the database."""
    log = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()

# 1. Add a Task Quickly (Admin, Super Admin)
@quick_actions_bp.route('/quick-actions/task', methods=['POST'])
@token_required
def quick_add_task(current_user):
    if current_user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return jsonify({'message': 'Permission denied. Admin access required.'}), 403
    
    data = request.get_json()
    if not data.get('title'):
        return jsonify({'message': 'Title is required'}), 400

    new_task = Task(
        title=data.get('title'),
        description=data.get('description'),
        assigned_to=data.get('assigned_to'),
        status='Pending',
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        organization_id=current_user.organization_id
    )
    db.session.add(new_task)
    db.session.commit()
    
    log_activity(current_user.id, f"Created task: {new_task.title}", "Task", new_task.id)
    return jsonify({'message': 'Task created successfully', 'task_id': new_task.id}), 201

# 2. Assign a Lead to a User (Admin, Super Admin)
@quick_actions_bp.route('/quick-actions/lead/<int:lead_id>/assign', methods=['PUT'])
@token_required
def assign_lead(current_user, lead_id):
    if current_user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return jsonify({'message': 'Permission denied. Admin access required.'}), 403
    
    data = request.get_json()
    user_id = data.get('assigned_to')
    
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
        
    lead.assigned_to = user_id
    db.session.commit()
    
    log_activity(current_user.id, f"Assigned lead {lead_id} to user {user_id}", "Lead", lead.id)
    return jsonify({'message': 'Lead assigned successfully'}), 200

# 3. Add a Note (Admin, Super Admin, HR, Manager)
@quick_actions_bp.route('/quick-actions/note', methods=['POST'])
@token_required
def add_note(current_user):
    allowed_roles = ['ADMIN', 'SUPER_ADMIN', 'HR', 'MANAGER']
    if current_user.role not in allowed_roles:
        return jsonify({'message': 'Permission denied.'}), 403
        
    data = request.get_json()
    note_content = data.get('note')
    
    if not note_content:
        return jsonify({'message': 'Note content is required'}), 400

    # Using Activity table to store notes
    activity = Activity(
        description=f"Note: {note_content}",
        status="Note",
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        created_at=datetime.utcnow()
    )
    db.session.add(activity)
    db.session.commit()
    
    log_activity(current_user.id, "Added a note", "Activity", activity.id)
    return jsonify({'message': 'Note added successfully'}), 201

# 4. Change Status (Active / Inactive) (Admin, Super Admin, HR, Manager)
@quick_actions_bp.route('/quick-actions/user/<int:user_id>/status', methods=['PUT'])
@token_required
def change_user_status(current_user, user_id):
    allowed_roles = ['ADMIN', 'SUPER_ADMIN', 'HR', 'MANAGER']
    if current_user.role not in allowed_roles:
        return jsonify({'message': 'Permission denied.'}), 403
        
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['Active', 'Inactive']:
        return jsonify({'message': 'Invalid status. Use Active or Inactive.'}), 400
        
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'message': 'User not found'}), 404
             
    target_user.status = new_status
    db.session.commit()
    
    log_activity(current_user.id, f"Changed status of user {user_id} to {new_status}", "User", target_user.id)
    return jsonify({'message': 'Status updated successfully'}), 200

# 5. Log an Activity (All Roles) & 6. Mark Own Task Completed (Employee)
@quick_actions_bp.route('/quick-actions/activity', methods=['POST'])
@token_required
def log_manual_activity(current_user):
    data = request.get_json()
    log_activity(current_user.id, data.get('action'), data.get('entity_type'), data.get('entity_id'))
    return jsonify({'message': 'Activity logged successfully'}), 201

@quick_actions_bp.route('/quick-actions/task/<int:task_id>/complete', methods=['PUT'])
@token_required
def complete_own_task(current_user, task_id):
    task = Task.query.get(task_id)
    if not task or task.assigned_to != current_user.id:
        return jsonify({'message': 'Task not found or permission denied.'}), 403
    task.status = 'Completed'
    db.session.commit()
    log_activity(current_user.id, f"Marked task {task_id} as completed", "Task", task.id)
    return jsonify({'message': 'Task marked as completed'}), 200