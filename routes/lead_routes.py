from flask import Blueprint, jsonify, request
from routes.auth_routes import token_required, permission_required
from models.crm import Lead
from extensions import db
from db import get_engine
from sqlalchemy import text
from datetime import datetime, date

lead_bp = Blueprint('lead_bp', __name__)

@lead_bp.route("/", methods=["GET"], strict_slashes=False)
@lead_bp.route("/all", methods=["GET", "OPTIONS"])
@token_required
@permission_required("Leads", "view")
def get_leads(current_user):
    """
    Get all leads for the user's organization, ensuring data isolation.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        # ✅ Dynamic DB Switching
        engine = get_engine(current_user.tenant_db)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM leads WHERE is_deleted = 0")).fetchall()
            # Convert row objects to dictionaries manually since we are using raw SQL for tenant isolation
            leads_list = []
            for row in result:
                row_dict = dict(row._mapping)
                # Serialize dates for JSON compatibility
                for k, v in row_dict.items():
                    if isinstance(v, (datetime, date)):
                        row_dict[k] = str(v)
                leads_list.append(row_dict)

        return jsonify(leads_list)
    except Exception as e:
        print(f"[FAIL] Error fetching leads: {e}")
        return jsonify({"error": "An internal error occurred while fetching leads."}), 500

@lead_bp.route("/", methods=["POST", "OPTIONS"], strict_slashes=False)
@token_required
def create_lead(current_user):
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json()
    print("[DEBUG] /api/leads Body:", data)

    # ✅ Insert into Tenant DB
    engine = get_engine(current_user.tenant_db)
    
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO leads (name, email, phone, source, status, score, sla, owner, description, ip_address, city, state, country, organization_id)
            VALUES (:name, :email, :phone, :source, :status, :score, :sla, :owner, :description, :ip_address, :city, :state, :country, :org_id)
        """), {
            "name": data.get("name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "source": data.get("source"),
            "status": data.get("status"),
            "score": data.get("score"),
            "sla": data.get("sla"),
            "owner": data.get("owner"),
            "description": data.get("description"),
            "ip_address": data.get("ip_address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "country": data.get("country"),
            "org_id": current_user.organization_id
        })

    return jsonify({"message": "Lead created successfully"}), 201

@lead_bp.route("/<int:lead_id>", methods=["GET", "OPTIONS"])
@token_required
def get_lead(current_user, lead_id):
    """
    Get a single lead by its ID.
    """
    if request.method == 'OPTIONS':
        return '', 200

    engine = get_engine(current_user.tenant_db)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM leads WHERE id = :id AND organization_id = :org_id AND is_deleted = 0"), 
                              {"id": lead_id, "org_id": current_user.organization_id}).fetchone()
        if not result:
            return jsonify({"error": "Lead not found"}), 404
        
        lead_data = dict(result._mapping)
        for key, value in lead_data.items():
            if isinstance(value, (datetime, date)):
                lead_data[key] = str(value)
        return jsonify(lead_data)

@lead_bp.route("/<int:lead_id>", methods=["PUT", "OPTIONS"], strict_slashes=False)
@token_required
def update_lead(current_user, lead_id):
    """
    Update a single lead by its ID.
    """
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    engine = get_engine(current_user.tenant_db)
    with engine.begin() as conn:
        # Check existence
        check = conn.execute(text("SELECT id FROM leads WHERE id = :id AND organization_id = :org_id"), 
                             {"id": lead_id, "org_id": current_user.organization_id}).fetchone()
        if not check:
            return jsonify({"error": "Lead not found"}), 404

        conn.execute(text("""
            UPDATE leads SET 
                name = :name, email = :email, phone = :phone, source = :source, 
                status = :status, score = :score, sla = :sla, owner = :owner, 
                description = :description, city = :city, state = :state, country = :country
            WHERE id = :id
        """), {
            "name": data.get("name"), "email": data.get("email"), "phone": data.get("phone"),
            "source": data.get("source"), "status": data.get("status"), "score": data.get("score"),
            "sla": data.get("sla"), "owner": data.get("owner"), "description": data.get("description"),
            "city": data.get("city"), "state": data.get("state"), "country": data.get("country"),
            "id": lead_id
        })

    return jsonify({"message": "Lead updated successfully"})

@lead_bp.route("/<int:lead_id>", methods=["DELETE", "OPTIONS"], strict_slashes=False)
@token_required
def delete_lead(current_user, lead_id):
    """
    Hard delete a lead by its ID.
    """
    if request.method == 'OPTIONS':
        return '', 200

    engine = get_engine(current_user.tenant_db)
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM leads WHERE id = :id AND organization_id = :org_id"), 
                              {"id": lead_id, "org_id": current_user.organization_id})
        if result.rowcount == 0:
            return jsonify({"error": "Lead not found"}), 404

    return jsonify({"message": "Lead deleted successfully"})