from flask import Blueprint, request, jsonify
from extensions import db
from models.user import User
from routes.auth_routes import token_required
from datetime import datetime
from services.rbac import role_required

team_management_bp = Blueprint('team_management', __name__)

@team_management_bp.route('/api/branches/<int:branch_id>/team', methods=['GET'])
@token_required
@role_required('MANAGER')
def get_branch_team(current_user, branch_id):
    # Additional check for Manager to only see their branch
    if current_user.role == 'MANAGER' and getattr(current_user, 'branch_id', None) != branch_id:
         return jsonify({"error": "Unauthorized access to other branch"}), 403
        
    # Assuming branch_id column exists on User (added via app.py migration)
    members = User.query.filter_by(organization_id=current_user.organization_id)
    if hasattr(User, 'branch_id'):
        members = members.filter_by(branch_id=branch_id)
        
    members = members.all()
    return jsonify([{
        "id": u.id, "name": u.name, "email": u.email, "role": u.role,
        "last_active": u.last_active.isoformat() if getattr(u, 'last_active', None) else None
    } for u in members]), 200

@team_management_bp.route('/api/branches/<int:branch_id>/invite', methods=['POST'])
@token_required
@role_required('MANAGER')
def invite_member(current_user, branch_id):
    data = request.get_json()
    # Logic to create user or send invite email would go here
    # For now, simulating success
    return jsonify({"message": f"Invite sent to {data.get('email')}"}), 200

@team_management_bp.route('/api/team/<int:member_id>', methods=['PATCH'])
@token_required
@role_required('ADMIN')
def update_member(current_user, member_id):
    member = User.query.get_or_404(member_id)
    data = request.get_json()
    if 'role' in data: member.role = data['role']
    db.session.commit()
    return jsonify({"message": "Member updated"}), 200

@team_management_bp.route('/api/heartbeat', methods=['POST'])
@token_required
def heartbeat(current_user):
    if hasattr(current_user, 'last_active'):
        current_user.last_active = datetime.utcnow()
        db.session.commit()
    else:
        # Fallback if column not yet migrated
        pass
    return jsonify({"status": "ok"}), 200