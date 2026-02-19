from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead
from models.payment import Payment
from routes.auth_routes import token_required
from services.payment_service import create_payment_link
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

    # --- PAYMENT AUTOMATION TRIGGER ---
    # Trigger only if status changes to 'Converted'
    if data.get("status") == "Converted":
        # 1. Create Razorpay Payment Link (amount is hardcoded as per example)
        payment_url, payment_id = create_payment_link(999, lead.email)

        if payment_url and payment_id:
            # 2. Save Payment Record to DB
            new_payment = Payment(
                lead_id=lead.id,
                email=lead.email,
                razorpay_payment_link_id=payment_id,
                razorpay_payment_link_url=payment_url,
                amount=999,
                status="created"
            )
            db.session.add(new_payment)
            db.session.commit()

            # 3. Send Email with Payment Link
            send_email(lead.email, "Complete Your CRM Subscription Payment", f"Please complete your payment: {payment_url}")
    
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
    # Logic for getting leads would go here
    return jsonify({"message": "Get leads endpoint not fully implemented in this task."}), 501

@lead_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@token_required
def get_lead(current_user, lead_id):
    # Logic for getting a single lead would go here
    return jsonify({"message": "Get lead endpoint not fully implemented in this task."}), 501

@lead_bp.route('/api/leads/<int:lead_id>', methods=['DELETE'])
@token_required
def delete_lead(current_user, lead_id):
    # Logic for deleting a lead would go here
    return jsonify({"message": "Delete lead endpoint not fully implemented in this task."}), 501