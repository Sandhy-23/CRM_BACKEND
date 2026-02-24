from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead
from routes.auth_routes import token_required
from services.payment_service import create_cashfree_order
from services.email_service import send_email
from datetime import datetime

lead_bp = Blueprint('lead', __name__)

# NOTE: This file was created to implement the payment automation feature.
# Other lead-related routes might exist elsewhere or can be added here.

@lead_bp.route('/api/leads/<int:lead_id>', methods=['PUT'])
@token_required
def update_lead(current_user, lead_id):
    """
    Updates a lead and triggers payment automation if status is 'Converted'.
    """
    lead = Lead.query.get_or_404(lead_id)

    # Authorization check (simplified: user must be in the same org)
    if lead.organization_id != current_user.organization_id and current_user.role != 'SUPER_ADMIN':
        return jsonify({"error": "Unauthorized to access this lead"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400
        
    original_status = lead.status

    # Update lead fields from request data
    for key, value in data.items():
        if hasattr(lead, key) and key not in ['id', 'organization_id', 'created_at']:
            setattr(lead, key, value)
    
    db.session.commit()

    # --- PAYMENT AUTOMATION (Cashfree) ---
    # Trigger only if status changes to 'Converted'
    if data.get("status") == "Converted" and original_status != "Converted":
        # 1. Create Cashfree Order (Amount hardcoded to 999 for subscription)
        checkout_url, order_id = create_cashfree_order(lead.id, lead.email, lead.phone, 999)

        if checkout_url:
            # 2. Send Email with Frontend Checkout Link
            subject = "Complete Your CRM Subscription Payment"
            body = f"Congratulations! Your lead status is now Converted.\n\nPlease complete your payment to proceed:\n{checkout_url}"
            send_email(lead.email, subject, body)
            print(f"[INFO] Payment Order Created: {order_id} | Email Sent to {lead.email}")
    
    return jsonify({"message": "Lead updated successfully"}), 200

# Placeholder for other lead routes from Postman collection for completeness
@lead_bp.route('/api/leads', methods=['POST'])
@token_required
def create_lead(current_user):
    data = request.get_json()

    new_lead = Lead(
        name=data.get("name"),
        email=data.get("email"),
        phone=data.get("phone"),
        company=data.get("company"),
        source=data.get("source"),
        ip_address=data.get("ip_address"),
        city=data.get("city"),
        state=data.get("state"),
        country=data.get("country"),
        status="New",
        organization_id=current_user.organization_id
    )

    db.session.add(new_lead)
    db.session.commit()

    return jsonify({"message": "Lead created successfully"}), 201

@lead_bp.route('/api/leads', methods=['GET'])
@token_required
def get_leads(current_user):
    leads = Lead.query.filter_by(
        organization_id=current_user.organization_id,
        is_deleted=False
    ).order_by(Lead.created_at.desc()).all()

    return jsonify([{
        "id": l.id,
        "name": l.name,
        "email": l.email,
        "phone": l.phone,
        "company": l.company,
        "source": l.source,
        "status": l.status,
        "city": l.city,
        "state": l.state,
        "country": l.country,
        "created_at": l.created_at.isoformat() if l.created_at else None
    } for l in leads]), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@token_required
def get_lead(current_user, lead_id):
    lead = Lead.query.filter_by(id=lead_id, organization_id=current_user.organization_id, is_deleted=False).first_or_404()
    return jsonify({
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "source": lead.source,
        "status": lead.status,
        "city": lead.city,
        "state": lead.state,
        "country": lead.country,
        "created_at": lead.created_at.isoformat() if lead.created_at else None
    }), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['DELETE'])
@token_required
def delete_lead(current_user, lead_id):
    lead = Lead.query.filter_by(id=lead_id, organization_id=current_user.organization_id).first_or_404()
    lead.is_deleted = True
    lead.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Lead deleted successfully"}), 200