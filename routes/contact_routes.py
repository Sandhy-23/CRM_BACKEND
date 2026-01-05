from flask import Blueprint, request, jsonify
from routes.auth_routes import token_required
from models.contact import Contact
from models.user import User
from models.activity_log import ActivityLog
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func

contact_bp = Blueprint('contacts', __name__)

# --- Helpers ---

def log_activity(user_id, action, entity_type=None, entity_id=None):
    """Helper to log activity to the database."""
    log = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()

def send_email(to_email, subject, body):
    """Mock email sender."""
    print(f"--- Sending Email ---\nTo: {to_email}\nSubject: {subject}\nBody: {body}\n-----------------------")

def get_contact_query(current_user):
    """Returns a base query for contacts filtered by role."""
    query = Contact.query

    if current_user.role == 'Super Admin':
        return query
    
    # Filter by Organization for everyone else
    query = query.filter_by(organization_id=current_user.organization_id)

    if current_user.role in ['Admin', 'HR']:
        return query
    
    if current_user.role == 'Manager':
        # Manager sees contacts assigned to their team (same department)
        team_user_ids = db.session.query(User.id).filter_by(
            organization_id=current_user.organization_id, 
            department=current_user.department
        ).all()
        team_ids = [uid[0] for uid in team_user_ids]
        
        return query.filter(Contact.assigned_to.in_(team_ids))

    if current_user.role == 'Employee':
        return query.filter_by(assigned_to=current_user.id)
    
    return query.filter_by(id=None) # Fallback

# --- Routes ---

@contact_bp.route('/api/contacts', methods=['POST'])
@token_required
def create_contact(current_user):
    data = request.get_json()
    
    if not data.get('name') or not data.get('email'):
        return jsonify({'message': 'Name and Email are required'}), 400

    new_contact = Contact(
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        company=data.get('company'),
        status=data.get('status', 'Lead'),
        assigned_to=data.get('assigned_to'),
        created_by=current_user.id,
        organization_id=current_user.organization_id if current_user.role != 'Super Admin' else data.get('organization_id', 1)
    )
    
    db.session.add(new_contact)
    db.session.commit()
    
    log_activity(current_user.id, f"Created contact: {new_contact.name}", "Contact", new_contact.id)
    send_email(new_contact.email, "Welcome!", "Your contact profile has been created in our CRM.")
    
    return jsonify({'message': 'Contact created successfully', 'contact': new_contact.to_dict()}), 201

@contact_bp.route('/api/contacts', methods=['GET'])
@token_required
def get_contacts(current_user):
    query = get_contact_query(current_user)
    contacts = query.order_by(Contact.created_at.desc()).all()
    return jsonify([c.to_dict() for c in contacts]), 200

@contact_bp.route('/api/contacts/<int:contact_id>', methods=['GET'])
@token_required
def get_single_contact(current_user, contact_id):
    query = get_contact_query(current_user)
    contact = query.filter_by(id=contact_id).first()
    
    if not contact:
        return jsonify({'message': 'Contact not found or permission denied'}), 404
        
    return jsonify(contact.to_dict()), 200

@contact_bp.route('/api/contacts/<int:contact_id>', methods=['PUT'])
@token_required
def update_contact(current_user, contact_id):
    query = get_contact_query(current_user)
    contact = query.filter_by(id=contact_id).first()
    
    if not contact:
        return jsonify({'message': 'Contact not found or permission denied'}), 404
    
    data = request.get_json()
    
    if 'name' in data: contact.name = data['name']
    if 'email' in data: contact.email = data['email']
    if 'phone' in data: contact.phone = data['phone']
    if 'company' in data: contact.company = data['company']
    if 'status' in data: contact.status = data['status']
    if 'assigned_to' in data: contact.assigned_to = data['assigned_to']

    db.session.commit()
    
    log_activity(current_user.id, f"Updated contact: {contact.name}", "Contact", contact.id)
    return jsonify({'message': 'Contact updated successfully', 'contact': contact.to_dict()}), 200

@contact_bp.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
@token_required
def delete_contact(current_user, contact_id):
    if current_user.role not in ['Super Admin', 'Admin']:
        return jsonify({'message': 'Permission denied. Only Admins can delete contacts.'}), 403

    query = get_contact_query(current_user)
    contact = query.filter_by(id=contact_id).first()
    
    if not contact:
        return jsonify({'message': 'Contact not found'}), 404
        
    db.session.delete(contact)
    db.session.commit()
    
    log_activity(current_user.id, f"Deleted contact {contact_id}", "Contact", contact_id)
    return jsonify({'message': 'Contact deleted successfully'}), 200

@contact_bp.route('/api/contacts/<int:contact_id>/profile', methods=['GET'])
@token_required
def get_contact_profile(current_user, contact_id):
    query = get_contact_query(current_user)
    contact = query.filter_by(id=contact_id).first()
    
    if not contact:
        return jsonify({'message': 'Contact not found or permission denied'}), 404
    
    activities = ActivityLog.query.filter_by(entity_type='Contact', entity_id=contact.id)\
        .order_by(ActivityLog.timestamp.desc()).all()
    
    activity_data = [{
        'action': log.action,
        'user_id': log.user_id,
        'timestamp': log.timestamp.isoformat()
    } for log in activities]

    profile = {
        "details": contact.to_dict(),
        "tasks": [], # Placeholder as Task model linking is not verified in context
        "activities": activity_data
    }
    
    return jsonify(profile), 200

@contact_bp.route('/api/dashboard/contact-stats', methods=['GET'])
@token_required
def get_contact_stats(current_user):
    query = get_contact_query(current_user)
    total_contacts = query.count()
    today = datetime.utcnow().date()
    new_contacts_today = query.filter(func.date(Contact.created_at) == today).count()
    
    status_counts = db.session.query(Contact.status, func.count(Contact.id))\
        .filter(Contact.id.in_([c.id for c in query.with_entities(Contact.id).all()]))\
        .group_by(Contact.status).all()
        
    stats = {
        "total_contacts": total_contacts,
        "new_contacts_today": new_contacts_today,
        "by_status": {s[0]: s[1] for s in status_counts}
    }
    return jsonify(stats), 200