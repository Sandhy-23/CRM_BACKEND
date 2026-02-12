from flask import Blueprint, request, jsonify
from models.crm import Lead
from extensions import db
from .auth_routes import token_required
from flask_cors import cross_origin
import requests
from datetime import datetime
from services.automation_engine import run_workflow

lead_bp = Blueprint("lead_bp", __name__, url_prefix="/api/leads")


@lead_bp.route("", methods=["GET", "OPTIONS"], strict_slashes=False)
@cross_origin()
@token_required
def get_leads(current_user):
    if request.method == "OPTIONS":
        return "", 200

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
            "company": lead.company,
            "city": lead.city,
            "state": lead.state,
            "country": lead.country,
            "status": lead.status,
            "created_at": lead.created_at
        })

    return jsonify(data), 200

@lead_bp.route("", methods=["POST"], strict_slashes=False)
@token_required
def create_lead(current_user):
    data = request.get_json()

    if not data.get("name") or not data.get("phone"):
        return jsonify({"error": "Name and phone are required"}), 400

    # STEP 2: Get IP Address
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip_address and "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    
    print(f"[DEBUG] Incoming Lead IP: {ip_address}")

    # STEP 3: Get Geo Location (Fallback to data provided in request)
    city = data.get("city")
    state = data.get("state")
    country = data.get("country")

    if not city and ip_address and ip_address != "127.0.0.1":
        try:
            # Using a free IP-API (Rate limited, but good for dev/testing)
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            if response.status_code == 200:
                geo = response.json()
                if geo.get("status") == "success":
                    city = city or geo.get("city")
                    state = state or geo.get("regionName")
                    country = country or geo.get("country")
                    print(f"[DEBUG] Geo found: {city}, {state}, {country}")
        except Exception as e:
            print(f"[WARN] Geo lookup failed: {e}")

    # STEP 4: Assign to Lead Model
    lead = Lead(
        name=data["name"],
        phone=data["phone"],
        email=data.get("email"),
        company=data.get("company"),
        source=data.get("source", "Manual"),
        status=data.get("status", "New"),
        city=city,
        state=state,
        country=country,
        ip_address=ip_address,
        is_deleted=False,
        organization_id=current_user.organization_id
    )

    # STEP 5: Commit
    db.session.add(lead)
    db.session.commit()
    
    print(f"[OK] Saved Lead: {lead.name} | Location: {lead.city}, {lead.country}")

    # AUTOMATION HOOK
    run_workflow("lead_created", lead)

    return jsonify({
        "message": "Lead created successfully",
        "lead_id": lead.id
    }), 201

@lead_bp.route("/<int:lead_id>", methods=["DELETE", "OPTIONS"])
@cross_origin()
@token_required
def delete_lead(current_user, lead_id):
    if request.method == "OPTIONS":
        return "", 200

    lead = Lead.query.get(lead_id)

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    # Soft delete (recommended)
    lead.is_deleted = True
    lead.deleted_at = datetime.utcnow()

    db.session.commit()

    return jsonify({"message": "Lead deleted successfully"}), 200

@lead_bp.route("/<int:lead_id>", methods=["PUT", "OPTIONS"])
@cross_origin()
@token_required
def update_lead(current_user, lead_id):
    if request.method == "OPTIONS":
        return "", 200

    lead = Lead.query.get(lead_id)

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    data = request.get_json()

    lead.name = data.get("name", lead.name)
    lead.email = data.get("email", lead.email)
    lead.phone = data.get("phone", lead.phone)
    lead.company = data.get("company", lead.company)
    lead.source = data.get("source", lead.source)
    lead.status = data.get("status", lead.status)
    lead.score = data.get("score", lead.score)
    lead.sla = data.get("sla", lead.sla)
    lead.description = data.get("description", lead.description)

    db.session.commit()

    return jsonify({
        "message": "Lead updated successfully",
        "lead_id": lead.id
    }), 200