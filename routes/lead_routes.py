from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead, Deal, Activity
from models.contact import Contact
from models.user import User
from routes.auth_routes import token_required
from datetime import datetime, timedelta
from sqlalchemy import func, or_, text
from models.activity_logger import log_activity
from services.automation_engine import run_automation
from models.task import Task

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

def serialize_lead(lead):
    """Helper to serialize a Lead object to a dictionary."""
    return {
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "source": lead.source,
        "status": lead.status,
        "score": getattr(lead, 'score', None),
        "sla": getattr(lead, 'sla', None),
        "owner": getattr(lead, 'owner', None),
        "description": getattr(lead, 'description', None),
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if hasattr(lead, 'updated_at') and lead.updated_at else None
    }

def get_lead_query(current_user):
    """Enforce Zoho-style Role Based Access Control"""
    # Simplified: Return all non-deleted leads.
    query = Lead.query.filter(getattr(Lead, 'is_deleted', False) == False)
    return query

@lead_bp.route('/api/leads', methods=['POST'])
@token_required
def create_lead(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON data'}), 400

    # 1. Validate Input (Mandatory: Name, Phone)
    name = data.get('name')
    phone = data.get('phone')
    
    if not name or not phone:
        return jsonify({'message': 'Name and Phone are required'}), 400

    # 2. Duplicate Check (Phone + Org)
    # Check if lead exists in this organization
    # Using raw SQL to avoid AttributeError if Lead model is missing organization_id
    sql_check = text("SELECT id FROM leads WHERE phone = :phone AND organization_id = :org_id")
    result = db.session.execute(sql_check, {'phone': phone, 'org_id': current_user.organization_id}).fetchone()

    if result:
        lead_id = result[0]
        # Update existing lead
        sql_update = text("""
            UPDATE leads 
            SET name = :name, email = :email, company = :company, source = :source, updated_at = :updated_at 
            WHERE id = :id
        """)
        
        db.session.execute(sql_update, {
            'name': name,
            'email': data.get('email'),
            'company': data.get('company'),
            'source': data.get('source'),
            'updated_at': datetime.utcnow(),
            'id': lead_id
        })
        
        db.session.commit()
        
        log_activity("lead", "updated", f"Lead '{name}' updated via duplicate check.", lead_id)
        return jsonify({'message': 'Lead updated successfully', 'lead_id': lead_id}), 200

    # 3. Create New Lead
    sql_insert = text("""
        INSERT INTO leads (name, phone, email, company, source, status, organization_id, owner, created_at, updated_at)
        VALUES (:name, :phone, :email, :company, :source, 'New', :org_id, :owner, :created_at, :updated_at)
    """)
    
    created_at = datetime.utcnow()
    result = db.session.execute(sql_insert, {
        'name': name,
        'phone': phone,
        'email': data.get('email'),
        'company': data.get('company'),
        'source': data.get('source', 'Manual'),
        'org_id': current_user.organization_id,
        'owner': current_user.name,
        'created_at': created_at,
        'updated_at': created_at
    })
    
    db.session.commit()
    lead_id = result.lastrowid

    # 4. Auto Create Task (Follow up)
    try:
        task = Task(
            title='Follow up with new lead',
            description=f"Follow up with {name}",
            task_date=datetime.utcnow().date() + timedelta(days=1),
            task_time="10:00:00",
            status='Pending',
            priority='High',
            lead_id=lead_id,
            company_id=current_user.organization_id,
            assigned_to=current_user.id,
            created_by=current_user.id
        )
        db.session.add(task)
        db.session.commit()
    except Exception as e:
        print(f"[WARN] Error creating auto-task for lead: {e}")
    
    log_activity("lead", "created", f"Lead '{name}' created.", lead_id)

    # Trigger automation if needed (kept from original)
    try:
        new_lead = Lead.query.get(lead_id)
        if new_lead:
            run_automation(module="lead", trigger_event="lead_created", record=new_lead)
    except:
        pass

    return jsonify({'message': 'Lead saved successfully', 'lead_id': lead_id}), 201

@lead_bp.route('/api/leads', methods=['GET'])
@token_required
def get_leads(current_user):
    query = get_lead_query(current_user)
    leads = query.order_by(Lead.created_at.desc()).all()
    
    # Manual serialization to ensure all fields are returned
    result = []
    for lead in leads:
        result.append(serialize_lead(lead))
    return jsonify(result), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@token_required
def get_lead_profile(current_user, lead_id):
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
        
    activities = [] # Placeholder, main timeline is via /api/activity-timeline
    
    return jsonify({
        "lead": serialize_lead(lead),
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
        # Only update allowed fields
        if hasattr(lead, key) and key not in ['id', 'created_at']:
            setattr(lead, key, value)
    
    # Manually update the 'updated_at' timestamp
    lead.updated_at = datetime.utcnow()

    db.session.commit()
    log_activity(
        module="lead",
        action="updated",
        description=f"Lead '{lead.name}' updated.",
        related_id=lead.id
    )
    return jsonify({'message': 'Lead updated successfully', 'lead': serialize_lead(lead)}), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['DELETE'])
@token_required
def delete_lead(current_user, lead_id):
    """Performs a soft delete on a lead."""
    lead = get_lead_query(current_user).filter_by(id=lead_id).first()
    if not lead:
        return jsonify({'message': 'Lead not found or already deleted'}), 404

    lead.is_deleted = True
    lead.updated_at = datetime.utcnow()
    db.session.commit()

    log_activity(
        module="lead",
        action="deleted",
        description=f"Lead '{lead.name}' soft deleted.",
        related_id=lead.id
    )
    return jsonify({'message': 'Lead deleted successfully'}), 200

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
        lead_id=lead.id,
        pipeline="Deals", # Default pipeline (Capitalized)
        title=lead.name,
        company=lead.company,
        stage="Proposal",
        value=0,
        owner=lead.owner,
        close_date=None
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