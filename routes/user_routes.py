from flask import Blueprint, request, jsonify
from extensions import db
from models.user import User
from routes.auth_routes import token_required
import uuid
from datetime import datetime, timedelta

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

    invite_link = f"https://yourcrm.com/accept-invite/{token}"

    return jsonify({"invite_link": invite_link, "message": "User invited successfully"})