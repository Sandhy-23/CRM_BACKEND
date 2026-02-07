from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead, Deal
from models.user import User
from models.team import Team, LocationTeamMapping
from routes.auth_routes import token_required
from models.activity_logger import log_activity
from services.automation_engine import run_automation
from datetime import datetime

lead_bp = Blueprint('leads', __name__)

# --- Routes ---

@lead_bp.route('/api/leads', methods=['POST'])
def create_lead():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON data'}), 400

    # Determine IP Address (Priority: JSON -> Header -> Remote Addr)
    ip_address = data.get('ip_address')
    if not ip_address:
        # Support for Postman simulation or Proxy headers
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()

    new_lead = Lead(
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        company=data.get('company'),
        source=data.get('source', 'website'),  # Default to 'website'
        ip_address=ip_address,
        city=data.get('city'),
        state=data.get('state'),
        country=data.get('country'),
        status="unassigned",
        created_at=datetime.utcnow()
    )

    try:
        db.session.add(new_lead)
        db.session.commit() # Commit first to get ID
        
        # Run automation
        run_automation("lead_created", new_lead)
        
        return jsonify({"message": "Lead created", "id": new_lead.id, "status": new_lead.status}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error saving lead: {e}")
        return jsonify({'message': 'Error saving lead'}), 500

# STEP 7: APIs you give to frontend team
@lead_bp.route('/api/leads/my', methods=['GET'])
@token_required
def get_my_leads(current_user):
    """View assigned leads for the current user (agent)."""
    leads = Lead.query.filter_by(assigned_user_id=current_user.id).order_by(Lead.created_at.desc()).all()
    result = [serialize_lead(lead) for lead in leads]
    return jsonify(result), 200

@lead_bp.route('/api/leads/unassigned', methods=['GET'])
@token_required
def get_unassigned_leads(current_user):
    """View unassigned leads (for admins)."""
    if current_user.role not in ['admin', 'SUPER_ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403

    leads = Lead.query.filter_by(status='unassigned').order_by(Lead.created_at.desc()).all()
    result = [serialize_lead(lead) for lead in leads]
    return jsonify(result), 200

@lead_bp.route('/api/leads/all', methods=['GET'])
@token_required
def get_all_leads(current_user):
    """View all leads (for superadmins)."""
    if current_user.role != 'SUPER_ADMIN':
        return jsonify({'message': 'Unauthorized'}), 403

    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    result = [serialize_lead(lead) for lead in leads]
    return jsonify(result), 200

# --- Restored Endpoints for Old Postman Files ---

@lead_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@token_required
def get_lead(current_user, lead_id):
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
    return jsonify(serialize_lead(lead)), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['PUT'])
@token_required
def update_lead(current_user, lead_id):
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
    
    data = request.get_json()
    # Update fields if present in request
    if 'name' in data: lead.name = data['name']
    if 'email' in data: lead.email = data['email']
    if 'phone' in data: lead.phone = data['phone']
    if 'company' in data: lead.company = data['company']
    if 'city' in data: lead.city = data['city']
    if 'state' in data: lead.state = data['state']
    if 'country' in data: lead.country = data['country']
    if 'source' in data: lead.source = data['source']
    if 'status' in data: lead.status = data['status']
    
    db.session.commit()
    log_activity("lead", "updated", f"Lead '{lead.name}' updated.", lead.id)
    return jsonify({'message': 'Lead updated successfully', 'lead': serialize_lead(lead)}), 200

@lead_bp.route('/api/leads/<int:lead_id>', methods=['DELETE'])
@token_required
def delete_lead(current_user, lead_id):
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
    
    db.session.delete(lead)
    db.session.commit()
    log_activity("lead", "deleted", f"Lead '{lead.name}' deleted.", lead.id)
    return jsonify({'message': 'Lead deleted successfully'}), 200

@lead_bp.route('/api/leads/<int:lead_id>/status', methods=['PUT'])
@token_required
def update_lead_status(current_user, lead_id):
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
    
    data = request.get_json()
    status = data.get('status')
    if not status:
        return jsonify({'message': 'Status is required'}), 400
        
    lead.status = status
    db.session.commit()
    log_activity("lead", "status_updated", f"Lead status updated to '{status}'.", lead.id)
    return jsonify({'message': 'Lead status updated'}), 200

@lead_bp.route('/api/leads/<int:lead_id>/assign', methods=['PUT'])
@token_required
def assign_lead(current_user, lead_id):
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
        
    data = request.get_json()
    # Support both old 'assigned_user_id' and new 'user_id'/'team_id'
    user_id = data.get('user_id') or data.get('assigned_user_id')
    team_id = data.get('team_id')
    
    if not user_id and not team_id:
        return jsonify({'message': 'user_id or team_id is required'}), 400
        
    if team_id:
        lead.assigned_team_id = team_id
        
    if user_id:
        lead.assigned_user_id = user_id
        lead.status = 'assigned'
        
    db.session.commit()
    
    desc = f"Lead assigned manually to User ID {user_id}" if user_id else f"Lead assigned to Team ID {team_id}"
    log_activity("lead", "assigned", desc, lead.id)
    
    return jsonify({'message': 'Lead assigned successfully'}), 200

@lead_bp.route('/api/leads/<int:lead_id>/convert', methods=['POST'])
@token_required
def convert_lead(current_user, lead_id):
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({'message': 'Lead not found'}), 404
        
    # Create Deal
    new_deal = Deal(
        lead_id=lead.id,
        title=lead.name,
        company=lead.company,
        pipeline='Deals',
        stage='New',
        value=0,
        owner=current_user.name,
        created_at=datetime.utcnow()
    )
    
    lead.status = 'Converted'
    db.session.add(new_deal)
    db.session.commit()
    
    log_activity("lead", "converted", f"Lead converted to Deal ID {new_deal.id}.", lead.id)
    return jsonify({'message': 'Lead converted successfully', 'deal_id': new_deal.id}), 200

def serialize_lead(lead):
    """Helper to serialize a Lead object to a dictionary based on new schema."""
    return {
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "city": lead.city,
        "state": lead.state,
        "country": lead.country,
        "source": lead.source,
        "assigned_team_id": lead.assigned_team_id,
        "assigned_user_id": lead.assigned_user_id,
        "status": lead.status,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }