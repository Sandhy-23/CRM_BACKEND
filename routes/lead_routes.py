from flask import Blueprint, jsonify, request
from routes.auth_routes import token_required
from models.crm import Lead
from extensions import db
from datetime import datetime

lead_bp = Blueprint('lead_bp', __name__)

@lead_bp.route("/", methods=["GET"], strict_slashes=False)
@lead_bp.route("/all", methods=["GET"])
@token_required
def get_leads(current_user):
    """
    Get all leads for the user's organization, ensuring data isolation.
    """
    try:
        leads = Lead.query.filter_by(is_deleted=False).all()

        return jsonify([lead.to_dict() for lead in leads])
    except Exception as e:
        print(f"[FAIL] Error fetching leads: {e}")
        return jsonify({"error": "An internal error occurred while fetching leads."}), 500

@lead_bp.route("/", methods=["POST"], strict_slashes=False)
@token_required
def create_lead(current_user):
    data = request.get_json()
    print("[DEBUG] /api/leads Body:", data)

    new_lead = Lead(
        name=data.get("name"),
        email=data.get("email"),
        phone=data.get("phone"),
        source=data.get("source"),
        status=data.get("status"),
        score=data.get("score"),
        sla=data.get("sla"),
        owner=data.get("owner"),
        description=data.get("description"),
        ip_address=data.get("ip_address"),
        city=data.get("city"),
        state=data.get("state"),
        country=data.get("country"),
        organization_id=current_user.organization_id
    )

    db.session.add(new_lead)
    db.session.commit()

    return jsonify({"message": "Lead created successfully"}), 201

@lead_bp.route("/<int:lead_id>", methods=["GET"])
@token_required
def get_lead(current_user, lead_id):
    """
    Get a single lead by its ID.
    """
    lead = Lead.query.filter_by(id=lead_id, organization_id=current_user.organization_id, is_deleted=False).first_or_404()
    return jsonify(lead.to_dict())

@lead_bp.route("/<int:lead_id>", methods=["PUT"], strict_slashes=False)
@token_required
def update_lead(current_user, lead_id):
    """
    Update a single lead by its ID.
    """
    lead = Lead.query.filter_by(id=lead_id, organization_id=current_user.organization_id).first()

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    data = request.get_json()

    lead.name = data.get("name", lead.name)
    lead.email = data.get("email", lead.email)
    lead.phone = data.get("phone", lead.phone)
    lead.source = data.get("source", lead.source)
    lead.status = data.get("status", lead.status)
    lead.score = data.get("score", lead.score)
    lead.sla = data.get("sla", lead.sla)
    lead.owner = data.get("owner", lead.owner)
    lead.description = data.get("description", lead.description)
    lead.city = data.get("city", lead.city)
    lead.state = data.get("state", lead.state)
    lead.country = data.get("country", lead.country)

    db.session.commit()

    return jsonify({"message": "Lead updated successfully"})

@lead_bp.route("/<int:lead_id>", methods=["DELETE"], strict_slashes=False)
@token_required
def delete_lead(current_user, lead_id):
    """
    Hard delete a lead by its ID.
    """
    lead = Lead.query.filter_by(id=lead_id, organization_id=current_user.organization_id).first()

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    db.session.delete(lead)
    db.session.commit()

    return jsonify({"message": "Lead deleted successfully"})