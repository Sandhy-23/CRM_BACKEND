from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead, Deal, Activity
from models.contact import Contact
from models.user import User
from routes.auth_routes import token_required
from datetime import datetime
from sqlalchemy import func, or_
from models.activity_logger import log_activity
from models.automation_engine import run_automation_rules

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
    query = Lead.query
    
    # Filter by Organization for everyone (Company-wise isolation)
    query = query.filter_by(company_id=current_user.organization_id)

    # 1. Super Admin: View All in Org
    if current_user.role == 'SUPER_ADMIN':
        return query

    # 2. Admin: View Company Leads
    if current_user.role == 'ADMIN':
        return query
    
    # 3. Manager: View Team Leads (Same Dept)
    if current_user.role == 'MANAGER':
        team_ids = [u.id for u in User.query.filter_by(organization_id=current_user.organization_id, department=current_user.department).all()]
        return query.filter(Lead.owner_id.in_(team_ids))
    
    # 4. Employee/User: View Assigned Leads Only
    if current_user.role in ['EMPLOYEE', 'USER']:
        return query.filter_by(owner_id=current_user.id)
    
    return query.filter_by(id=None) # Fallback

@lead_bp.route('/api/leads', methods=['POST'])
@token_required
def create_lead(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON data'}), 400
    
    # Mandatory Fields
    if not data.get('company') or not data.get('last_name'):
        print(f"❌ Validation Error (Create Lead): Missing company or last_name. Received: {data}")
        return jsonify({'message': 'Company and Last Name are mandatory'}), 400

    # Unique Email Check
    if data.get('email') and Lead.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Lead with this email already exists'}), 409

    new_lead = Lead(
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        company=data.get('company'), # Stores Company Name string
        email=data.get('email'),
        phone=data.get('phone'),
        mobile=data.get('mobile'),
        source=data.get('source'),
        status=data.get('status', 'New'),
        owner_id=current_user.id, # Auto-assign to creator
        company_id=current_user.organization_id, # Use user's org ID
        created_at=datetime.utcnow()
    )
    
    db.session.add(new_lead)
    db.session.commit()
    
    log_activity(
        module="lead",
        action="created",
        description=f"Lead '{new_lead.first_name or ''} {new_lead.last_name}' created.",
        related_id=new_lead.id
    )

    # --- AUTOMATION TRIGGER ---
    run_automation_rules(
        module="lead",
        trigger_event="lead_created",
        record=new_lead,
        company_id=current_user.organization_id,
        user_id=current_user.id
    )

    return jsonify({'message': 'Lead created successfully', 'lead_id': new_lead.id}), 201

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
            "name": f"{l.first_name or ''} {l.last_name}".strip(),
            "company": l.company,
            "email": l.email,
            "phone": l.phone,
            "status": l.status,
            "owner_id": l.owner_id
        })
    return jsonify(result), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@token_required
def get_lead_profile(current_user, lead_id):
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
        
    # Get Activities
    # This should now use the new activity log table and its to_dict method
    activities = [] # Placeholder, main timeline is via /api/activity-timeline
    
    return jsonify({
        "lead": {
            "id": lead.id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company": lead.company,
            "email": lead.email,
            "phone": lead.phone,
            "mobile": lead.mobile,
            "source": lead.source,
            "status": lead.status,
            "owner_id": lead.owner_id
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
        description=f"Lead '{lead.first_name or ''} {lead.last_name}' updated.",
        related_id=lead.id
    )
    return jsonify({'message': 'Lead updated successfully'}), 200

@lead_bp.route('/api/leads/<int:lead_id>/convert', methods=['POST'])
@token_required
def convert_lead(current_user, lead_id):
    print(f"🔍 [DEBUG] Attempting to convert Lead ID: {lead_id} for User: {current_user.email} (Org: {current_user.organization_id})")
    
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()

    if not lead:
        print(f"❌ [DEBUG] Lead {lead_id} not found or access denied.")
        return jsonify({"error": f"Lead {lead_id} not found or you do not have permission to access it."}), 404

    # Create Deal from Lead
    new_deal = Deal(
        title=f"{lead.first_name} {lead.last_name}",
        amount=0, # Default
        stage="New",
        lead_id=lead.id,
        owner_id=lead.owner_id,
        organization_id=lead.company_id
    )

    # Update Lead status
    lead.status = "Converted"

    db.session.add(new_deal)
    
    db.session.commit()

    log_activity(
        module="lead",
        action="converted",
        description=f"Lead '{lead.first_name or ''} {lead.last_name}' converted to Deal ID {new_deal.id}.",
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
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN', 'MANAGER']:
        return jsonify({'message': 'Unauthorized. Only Admin or Manager can assign leads.'}), 403

    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404

    data = request.get_json()
    assigned_to = data.get('assigned_to')

    if not assigned_to:
        return jsonify({'message': 'assigned_to (user_id) is required'}), 400

    # Verify the user exists and is in the same organization
    assignee = User.query.get(assigned_to)
    if not assignee or assignee.organization_id != current_user.organization_id:
        return jsonify({'message': 'User not found in your organization'}), 404

    lead.owner_id = assigned_to
    # Update assigned_to column if it exists (based on app.py migration it does)
    if hasattr(lead, 'assigned_to'):
        lead.assigned_to = assigned_to

    db.session.commit()
    log_activity(
        module="lead",
        action="assigned",
        description=f"Lead assigned to user '{assignee.name}'.",
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