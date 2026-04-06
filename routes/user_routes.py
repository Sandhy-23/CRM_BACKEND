from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models.user import User
from routes.auth_routes import token_required, permission_required, ROLE_HIERARCHY
import uuid
from datetime import datetime, timedelta
from routes.email_service import send_user_email
import os
import json

user_bp = Blueprint('user_routes', __name__)

@user_bp.route('/api/invite', methods=['POST'])
@token_required
def invite_user(current_user):
    data = request.json
    
    if not data.get('email') or not data.get('name'):
        return jsonify({"error": "Email and Name are required"}), 400

    token = str(uuid.uuid4())

    new_user = User(
        name=data["name"],
        email=data["email"],
        role=data.get("role", "agent"),
        organization_id=current_user.organization_id,
        invite_token=token,
        invite_expiry=datetime.utcnow() + timedelta(hours=24),
        status="Pending",
        is_approved=False,
        is_verified=False
    )

    db.session.add(new_user)
    db.session.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://100.104.233.79:5173/")
    invite_link = f"{frontend_url.rstrip('/')}/accept-invite/{token}"

    return jsonify({"invite_link": invite_link, "message": "User invited successfully"})

@user_bp.route('/api/users', methods=['POST'])
@token_required
@permission_required("Users", "create")
def create_user_rbac(current_user):
    data = request.json
    name = data.get("name") or data.get("Full Name")
    email = data.get("email")
    password = data.get("password")
    new_role = data.get("role")
    permissions = data.get("permissions", {})

    if not all([name, email, password]):
        return jsonify({"error": "Name, Email and Password are required"}), 400

    # 🔹 ROLE HIERARCHY CHECK
    allowed_roles = ROLE_HIERARCHY.get(current_user.role, [])
    if new_role not in allowed_roles:
        return jsonify({
            "error": f"You ({current_user.role}) are not allowed to create a user with the role '{new_role}'"
        }), 403

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 409

    # Hash password using bcrypt as requested
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(
        name=name,
        email=email,
        password=hashed_password,
        role=new_role,
        permissions=permissions,
        organization_id=current_user.organization_id,
        status="Active",
        is_approved=True,
        is_verified=True,
        must_change_password=True
    )

    db.session.add(new_user)
    db.session.commit()

    # Send welcome email using existing service
    send_user_email(email, name, password)

    return jsonify({"message": "User created successfully", "user_id": new_user.id}), 201

@user_bp.route('/api/team', methods=['GET'])
@token_required
def get_team_rbac(current_user):
    users = User.query.filter_by(organization_id=current_user.organization_id, is_deleted=False).all()
    return jsonify([{
        "name": u.name,
        "email": u.email,
        "role": u.role
    } for u in users]), 200