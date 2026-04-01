from flask import Blueprint, request, jsonify
from extensions import db
from models.task import Task
from routes.auth_routes import token_required
from datetime import datetime, timedelta

task_bp = Blueprint('tasks', __name__)

@task_bp.route('/tasks', methods=['POST'])
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


    new_task = Task(
            title=title,
            description=data.get('description'),
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'medium'),
            due_date=task_date,
            created_by=current_user.id,
        )
        
    try:
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

@task_bp.route('/tasks', methods=['GET'])
@token_required
def get_tasks(current_user):
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'priority': t.priority.lower() if t.priority else 'medium',
        'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else None,
        'status': t.status.lower() if t.status else 'pending'
    } for t in tasks]), 200

@task_bp.route('/tasks/<int:id>', methods=['PUT'])
@token_required
def update_task(current_user, id):
    data = request.get_json()

    task = Task.query.get(id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    # Update status properly with validation
    if "status" in data:
        status_val = data["status"].lower()
        if status_val not in ["pending", "completed"]:
            return jsonify({"error": "Invalid status. Use 'pending' or 'completed'."}), 400
        task.status = status_val

    # Optional other fields
    if "title" in data: task.title = data["title"]
    if "description" in data: task.description = data["description"]
    if "priority" in data: task.priority = data["priority"]

    if 'due_date' in data:
        due_date_str = data.get('due_date')
        if due_date_str:
            try:
                # Handle "Today", "Tomorrow" logic if sent in update, or standard date
                if due_date_str.lower() == 'today': task.due_date = datetime.utcnow().date()
                elif due_date_str.lower() == 'tomorrow': task.due_date = datetime.utcnow().date() + timedelta(days=1)
                else: task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass # Keep old date if invalid
        else:
            task.due_date = None # Clear date if empty string sent

    db.session.commit()

    return jsonify({"message": "Task updated successfully"})

@task_bp.route('/tasks/<int:id>', methods=['DELETE'])
@token_required
def delete_task(current_user, id):
    task = Task.query.get(id)

    if not task:
        return jsonify({"error": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted"})

@task_bp.route('/tasks/my', methods=['GET'])
@token_required
def get_my_tasks(current_user):
    tasks = Task.query.filter_by(created_by=current_user.id).order_by(Task.created_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'priority': t.priority.lower() if t.priority else 'medium',
        'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else None,
        'description': t.description,
        'status': t.status.lower() if t.status else 'pending'
    } for t in tasks]), 200