from flask import Blueprint, request, jsonify
from extensions import db
from models.task import Task
from routes.auth_routes import token_required
from datetime import datetime, timedelta

task_bp = Blueprint('tasks', __name__)

@task_bp.route('/api/tasks', methods=['POST'])
@token_required
def create_task(current_user):
    data = request.get_json()
    
    # Validate Title
    title = data.get('title')
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    # Handle Due Date (Support 'Today', 'Tomorrow', and YYYY-MM-DD)
    due_date_str = data.get('due_date')
    task_date = None
    
    if due_date_str:
        clean_date = str(due_date_str).strip().lower()
        if clean_date == 'today':
            task_date = datetime.utcnow().date()
        elif clean_date == 'tomorrow':
            task_date = datetime.utcnow().date() + timedelta(days=1)
        else:
            try:
                task_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                # Return 400 if the date format is completely invalid
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD, "Today", or "Tomorrow"'}), 400

    # Handle Related To (Sanitize input)
    # If 'related_to' is garbage like "haha", we ignore it to prevent DB errors.
    related_to = data.get('related_to')
    lead_id = None
    
    if related_to and str(related_to).isdigit():
        lead_id = int(related_to)

    try:
        new_task = Task(
            title=title,
            description=data.get('description'),
            priority=data.get('priority', 'Medium'),
            due_date=task_date,
            status='Pending',
            company_id=current_user.organization_id,
            created_by=current_user.id,
            lead_id=lead_id,
            assigned_to=data.get('assigned_to')
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            'message': 'Task created successfully',
            'task': {
                'id': new_task.id,
                'title': new_task.title,
                'priority': new_task.priority,
                'due_date': str(new_task.due_date) if new_task.due_date else None,
                'status': new_task.status
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"[FAIL] Task Creation Error: {e}")
        return jsonify({'error': 'Database error', 'message': str(e)}), 500

@task_bp.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks(current_user):
    tasks = Task.query.filter_by(company_id=current_user.organization_id).order_by(Task.created_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'priority': t.priority,
        'due_date': str(t.due_date) if t.due_date else None,
        'status': t.status
    } for t in tasks]), 200

@task_bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user, task_id):
    task = Task.query.filter_by(id=task_id, company_id=current_user.organization_id).first()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
        
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'}), 200

@task_bp.route('/api/tasks/my', methods=['GET'])
@token_required
def get_my_tasks(current_user):
    tasks = Task.query.filter_by(assigned_to=current_user.id, company_id=current_user.organization_id).order_by(Task.created_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'priority': t.priority,
        'due_date': str(t.due_date) if t.due_date else None,
        'status': t.status,
        'description': t.description
    } for t in tasks]), 200