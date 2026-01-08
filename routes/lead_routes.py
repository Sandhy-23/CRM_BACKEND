from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead, Deal, Activity
from models.contact import Contact
from models.user import User
from models.activity_log import ActivityLog
from routes.auth_routes import token_required
from datetime import datetime
from sqlalchemy import func

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

def log_activity(user_id, action, entity_type, entity_id):
    log = ActivityLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, timestamp=datetime.utcnow())
    db.session.add(log)
    db.session.commit()

def get_lead_query(current_user):
    """Enforce Zoho-style Role Based Access Control"""
    query = Lead.query
    
    # Filter by Organization for everyone (Company-wise isolation)
    query = query.filter_by(company_id=current_user.organization_id)

    # 1. Super Admin: View All in Org
    if current_user.role == 'Super Admin':
        return query

    # 2. Admin: View Company Leads
    if current_user.role == 'Admin':
        return query
    
    # 3. Manager: View Team Leads (Same Dept)
    if current_user.role == 'Manager':
        team_ids = [u.id for u in User.query.filter_by(organization_id=current_user.organization_id, department=current_user.department).all()]
        return query.filter(Lead.owner_id.in_(team_ids))
    
    # 4. Employee: View Assigned Leads Only
    if current_user.role == 'Employee':
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
    
    log_activity(current_user.id, f"Created Lead: {new_lead.last_name}", "Lead", new_lead.id)
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
    activities = ActivityLog.query.filter_by(entity_type='Lead', entity_id=lead.id).order_by(ActivityLog.timestamp.desc()).all()
    
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
        "activities": [{"action": a.action, "time": a.timestamp.isoformat()} for a in activities]
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
    log_activity(current_user.id, f"Updated Lead: {lead.last_name}", "Lead", lead.id)
    return jsonify({'message': 'Lead updated successfully'}), 200

@lead_bp.route('/api/leads/<int:lead_id>/convert', methods=['POST'])
@token_required
def convert_lead(current_user, lead_id):
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
        
    if lead.status == 'Converted':
        return jsonify({'message': 'Lead is already converted'}), 400

    # 1. Create Account (Company)
    new_account = Account(
        account_name=lead.company,
        phone=lead.phone,
        owner_id=lead.owner_id,
        organization_id=lead.company_id
    )
    db.session.add(new_account)
    db.session.flush() # Get ID

    # 2. Create Contact
    new_contact = Contact(
        name=f"{lead.first_name or ''} {lead.last_name}".strip(),
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        assigned_to=lead.owner_id,
        organization_id=lead.company_id,
        status='Active'
    )
    db.session.add(new_contact)
    db.session.flush()

    # 3. Create Deal
    new_deal = Deal(
        deal_name=f"{lead.company} Deal",
        amount=0, # Default
        stage="New",
        probability=10,
        owner_id=lead.owner_id,
        # account_id=new_account.id, # Assuming Deal model has account_id
        # contact_id=new_contact.id,
        created_at=datetime.utcnow()
    )
    # Manually set IDs if model doesn't have them explicitly defined in context
    new_deal.account_id = new_account.id
    new_deal.contact_id = new_contact.id
    new_deal.company_id = lead.company_id # Organization
    
    db.session.add(new_deal)

    # 4. Update Lead
    lead.status = 'Converted'
    
    db.session.commit()
    
    log_activity(current_user.id, f"Converted Lead: {lead.last_name}", "Lead", lead.id)
    
    return jsonify({
        'message': 'Lead converted successfully',
        'account_id': new_account.id,
        'contact_id': new_contact.id,
        'deal_id': new_deal.id
    }), 200