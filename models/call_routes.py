from flask import Blueprint, request, jsonify
from extensions import db
from models.call import Call
from routes.auth_routes import token_required

call_bp = Blueprint('call_bp', __name__)


@call_bp.route('/api/calls', methods=['GET'])
@token_required
def get_calls(current_user):
    calls = Call.query.filter_by(
        organization_id=current_user.organization_id
    ).order_by(Call.timestamp.desc()).all()

    return jsonify([{
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "status": c.status,
        "duration": c.duration,
        "notes": c.notes,
        "timestamp": c.timestamp.isoformat() if c.timestamp else None
    } for c in calls]), 200


@call_bp.route('/api/calls', methods=['POST'])
@token_required
def create_call(current_user):
    data = request.get_json()

    new_call = Call(
        name=data.get('name'),
        phone=data.get('phone'),
        status=data.get('status'),
        duration=data.get('duration'),
        notes=data.get('notes'),
        organization_id=current_user.organization_id
    )

    db.session.add(new_call)
    db.session.commit()

    return jsonify({
        "message": "Call logged successfully",
        "id": new_call.id
    }), 201