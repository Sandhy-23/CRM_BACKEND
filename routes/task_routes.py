from flask import Blueprint, request, jsonify
from extensions import db
from models.task import Task
from models.user import User
from routes.auth_routes import token_required
from datetime import datetime

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

    return jsonify({'message': 'Task marked as completed'}), 200