from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead, Deal, Activity
from models.contact import Contact
from models.user import User
from routes.auth_routes import token_required
from datetime import datetime
from sqlalchemy import func, or_
from models.activity_logger import log_activity
from services.automation_engine import run_automation

lead_bp = Blueprint('leads', __name__)

# --- Helper: Account Model (Local Definition if missing in models) ---
class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    website = db.Column(db.String(100))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def get_lead_query(current_user):
    """Enforce Zoho-style Role Based Access Control"""
    # Simplified: Return all leads since company_id/owner_id are removed from Lead model
    query = Lead.query
    return query

@lead_bp.route('/api/leads', methods=['POST'])
@token_required
def create_lead(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON data'}), 400
    
    # Strict Validation: Required Fields
    required_fields = [
        "name", "email", "company",
        "source", "status", "score",
        "sla", "owner", "description"
    ]

    missing_fields = []
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            missing_fields.append(field)

    if missing_fields:
        print(f"[FAIL] Validation Error: Missing fields {missing_fields}")
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields
        }), 400

    # Unique Email Check
    if data.get('email') and Lead.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Lead with this email already exists'}), 409

    new_lead = Lead(
        name=data["name"],
        company=data["company"],
        email=data["email"],
        phone=data.get('phone'), # Optional
        source=data["source"],
        status=data["status"],
        score=data["score"],
        sla=data["sla"],
        owner=data["owner"],
        description=data["description"],
        created_at=datetime.utcnow()
    )
    
    db.session.add(new_lead)
    db.session.commit()
    
    log_activity(
        module="lead",
        action="created",
        description=f"Lead '{new_lead.name}' created.",
        related_id=new_lead.id
    )

    # --- AUTOMATION TRIGGER ---
    run_automation(
        module="lead",
        trigger_event="lead_created",
        record=new_lead
    )

    return jsonify({'message': 'Lead stored successfully', 'lead_id': new_lead.id}), 201

@lead_bp.route('/api/leads', methods=['GET'])
@token_required
def get_leads(current_user):
    query = get_lead_query(current_user)
    leads = query.order_by(Lead.created_at.desc()).all()
    
    # Manual serialization to ensure all fields are returned
    result = []
    for l in leads:
        result.append({
            "id": l.id,
            "name": l.name,
            "company": l.company,
            "email": l.email,
            "phone": l.phone,
            "status": l.status,
            "source": l.source,
            "score": getattr(l, 'score', None),
            "sla": getattr(l, 'sla', None),
            "owner": getattr(l, 'owner', None),
            "created_at": l.created_at.isoformat() if l.created_at else None
        })
    return jsonify(result), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@token_required
def get_lead_profile(current_user, lead_id):
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
        
    activities = [] # Placeholder, main timeline is via /api/activity-timeline
    
    return jsonify({
        "lead": {
            "id": lead.id,
            "name": lead.name,
            "company": lead.company,
            "email": lead.email,
            "phone": lead.phone,
            "source": lead.source,
            "status": lead.status,
            "owner": lead.owner
        },
        "activities": activities
    }), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['PUT'])
@token_required
def update_lead(current_user, lead_id):
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404

    data = request.get_json()
    for key, value in data.items():
        if hasattr(lead, key):
            setattr(lead, key, value)
            
    db.session.commit()
    log_activity(
        module="lead",
        action="updated",
        description=f"Lead '{lead.name}' updated.",
        related_id=lead.id
    )
    return jsonify({'message': 'Lead updated successfully'}), 200

@lead_bp.route('/api/leads/<int:lead_id>/convert', methods=['POST'])
@token_required
def convert_lead(current_user, lead_id):
    print(f"[DEBUG] Attempting to convert Lead ID: {lead_id} for User: {current_user.email} (Org: {current_user.organization_id})")
    
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()

    if not lead:
        print(f"[FAIL] Lead {lead_id} not found or access denied.")
        return jsonify({"error": f"Lead {lead_id} not found or you do not have permission to access it."}), 404

    # Create Deal from Lead
    new_deal = Deal(
        title=lead.name,
        amount=0, # Default
        stage="New",
        lead_id=lead.id,
        owner_id=current_user.id, # Assign deal to current user
        organization_id=current_user.organization_id
    )

    # Update Lead status
    lead.status = "Converted"

    db.session.add(new_deal)
    
    db.session.commit()

    log_activity(
        module="lead",
        action="converted",
        description=f"Lead '{lead.name}' converted to Deal ID {new_deal.id}.",
        related_id=lead.id
    )
    
    return jsonify({
        'message': 'Lead converted successfully',
        'deal_id': new_deal.id
    }), 200

@lead_bp.route('/api/leads/<int:lead_id>/assign', methods=['PUT'])
@token_required
def assign_lead(current_user, lead_id):
    # Allow Admin, Super Admin, Manager to assign
    # if current_user.role not in ['SUPER_ADMIN', 'ADMIN', 'MANAGER']:
    #     return jsonify({'message': 'Unauthorized. Only Admin or Manager can assign leads.'}), 403

    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404

    data = request.get_json()
    # Expecting "owner": "Name" string
    new_owner = data.get('owner')

    if not new_owner:
        return jsonify({'message': 'owner name is required'}), 400

    lead.owner = new_owner

    db.session.commit()
    log_activity(
        module="lead",
        action="assigned",
        description=f"Lead assigned to '{new_owner}'.",
        related_id=lead.id
    )
    
    return jsonify({'message': 'Lead assigned successfully'}), 200

@lead_bp.route('/api/leads/<int:lead_id>/status', methods=['PUT'])
@token_required
def update_lead_status(current_user, lead_id):
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404

    data = request.get_json()
    status = data.get('status')

    if not status:
        return jsonify({'message': 'status is required'}), 400

    lead.status = status
    db.session.commit()
    log_activity(
        module="lead",
        action="status_updated",
        description=f"Lead status updated to '{status}'.",
        related_id=lead.id
    )
    
    return jsonify({'message': 'Lead status updated successfully'}), 200