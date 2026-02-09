from flask import Blueprint, request, jsonify
from models.crm import Lead
from extensions import db
from .auth_routes import token_required

lead_bp = Blueprint("lead_bp", __name__, url_prefix="/api/leads")


@lead_bp.route("/", methods=["GET"])
@token_required
def get_leads(current_user):
    # Filter soft-deleted leads (handle False or NULL)
    leads = Lead.query.filter(
        (Lead.is_deleted == False) | (Lead.is_deleted.is_(None))
    ).all()

    data = []
    for lead in leads:
        data.append({
            "id": lead.id,
            "name": lead.name,
            "phone": lead.phone,
            "email": lead.email,
            "status": lead.status,
            "owner": lead.owner,
            "created_at": lead.created_at
        })

    return jsonify(data), 200

@lead_bp.route("/", methods=["POST"])
@token_required
def create_lead(current_user):
    data = request.get_json()

    if not data.get("name") or not data.get("phone"):
        return jsonify({"error": "Name and phone are required"}), 400

    lead = Lead(
        name=data["name"],
        phone=data["phone"],
        is_deleted=False,
        organization_id=current_user.organization_id
    )

    db.session.add(lead)
    db.session.commit()

    return jsonify({
        "message": "Lead created successfully",
        "lead_id": lead.id
    }), 201