from flask import Blueprint, request, jsonify
from routes.auth_routes import token_required
from models.contact import Contact
from models.user import User
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from models.activity_logger import log_activity

contact_bp = Blueprint('contacts', __name__)

# --- Helpers ---

def send_email(to_email, subject, body):
    """Mock email sender."""
    print(f"--- Sending Email ---\nTo: {to_email}\nSubject: {subject}\nBody: {body}\n-----------------------")

def get_contact_query(current_user):
    """Returns a base query for contacts filtered by role."""
    query = Contact.query

    if current_user.role == 'SUPER_ADMIN':
        return query
    
    # Filter by Organization for everyone else
    query = query.filter_by(organization_id=current_user.organization_id)

    if current_user.role in ['ADMIN', 'HR']:
        return query
    
    if current_user.role == 'MANAGER':
        # Manager sees contacts assigned to their team (same department)
        team_user_ids = db.session.query(User.id).filter_by(
            organization_id=current_user.organization_id, 
            department=current_user.department
        ).all()
        team_ids = [uid[0] for uid in team_user_ids]
        
        return query.filter(Contact.assigned_to.in_(team_ids))

    if current_user.role == 'EMPLOYEE':
        return query.filter_by(assigned_to=current_user.id)
    
    return query.filter_by(id=None) # Fallback

# --- Routes ---

@contact_bp.route('/api/contacts', methods=['POST'])
@token_required
def create_contact(current_user):
    data = request.get_json()
    email = data.get("email")
    mobile = data.get("mobile")

    if not data.get('first_name') or not email or not mobile:
        return jsonify({'message': 'First Name, Email, and Mobile are required'}), 400

    # Unique Check for email OR mobile (Per Company)
    existing = Contact.query.filter(
        Contact.organization_id == current_user.organization_id,
        or_(Contact.email == email, Contact.mobile == mobile)
    ).first()

    if existing:
        return jsonify({
            "error": "Duplicate contact detected",
            "message": "A contact with this email or mobile already exists in your organization.",
            "existing_contact_id": existing.id
        }), 409

    new_contact = Contact(
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        name=f"{data.get('first_name')} {data.get('last_name') or ''}".strip(),
        email=email,
        mobile=mobile,
        phone=data.get('phone'),
        company=data.get('company'),
        status=data.get('status', 'Active'),
        source=data.get('source', 'Manual'),
        assigned_to=data.get('assigned_to', current_user.id), # Default to creator if not assigned
        owner_id=current_user.id,
        created_by=current_user.id,
        organization_id=current_user.organization_id if current_user.role != 'SUPER_ADMIN' else data.get('organization_id', 1)
    )
    
    db.session.add(new_contact)
    db.session.commit()
    
    log_activity(
        module="contact",
        action="created",
        description=f"Contact '{new_contact.name}' created.",
        related_id=new_contact.id
    )
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
    
    if 'first_name' in data: contact.first_name = data['first_name']
    if 'last_name' in data: contact.last_name = data['last_name']
    # Update full name composite
    if 'first_name' in data or 'last_name' in data:
        contact.name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
        
    if 'email' in data: contact.email = data['email']
    if 'phone' in data: contact.phone = data['phone']
    if 'mobile' in data: contact.mobile = data['mobile']
    if 'company' in data: contact.company = data['company']
    if 'status' in data: contact.status = data['status']
    if 'source' in data: contact.source = data['source']
    if 'assigned_to' in data: contact.assigned_to = data['assigned_to']

    db.session.commit()
    
    log_activity(
        module="contact",
        action="updated",
        description=f"Contact '{contact.name}' updated.",
        related_id=contact.id
    )
    send_email(contact.email, "Profile Updated", "Your contact details have been updated.")
    return jsonify({'message': 'Contact updated successfully', 'contact': contact.to_dict()}), 200

@contact_bp.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
@token_required
def delete_contact(current_user, contact_id):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Permission denied. Only Admins can delete contacts.'}), 403

    query = get_contact_query(current_user)
    contact = query.filter_by(id=contact_id).first()
    
    if not contact:
        return jsonify({'message': 'Contact not found'}), 404
        
    # Soft Delete
    contact.status = 'Inactive'
    db.session.commit()
    
    log_activity(
        module="contact",
        action="deleted",
        description=f"Contact '{contact.name}' (ID: {contact_id}) deleted (set to inactive).",
        related_id=contact_id
    )
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

@contact_bp.route('/api/contacts/search', methods=['GET'])
@token_required
def search_contacts(current_user):
    query_param = request.args.get("q")
    if not query_param:
        return jsonify({'message': 'Search query parameter "q" is required.'}), 400

    base_query = get_contact_query(current_user)

    search_filter = or_(
        Contact.first_name.ilike(f"%{query_param}%"),
        Contact.last_name.ilike(f"%{query_param}%"),
        Contact.email.ilike(f"%{query_param}%"),
        Contact.mobile.ilike(f"%{query_param}%"),
        Contact.company.ilike(f"%{query_param}%")
    )

    contacts = base_query.filter(search_filter).all()

    # Using the model's to_dict method for serialization
    return jsonify([c.to_dict() for c in contacts])

@contact_bp.route('/api/contacts/duplicates', methods=['GET'])
@token_required
def find_duplicates(current_user):
    """
    Scans for duplicate contacts accessible by the user based on email and mobile.
    """
    # Base query for the user's organization/role
    base_query = get_contact_query(current_user)
    
    # Get all contact IDs accessible by the user
    accessible_contact_ids = [c.id for c in base_query.with_entities(Contact.id).all()]

    if not accessible_contact_ids:
        return jsonify({"duplicate_emails": [], "duplicate_mobiles": []})

    # Find duplicate emails within accessible contacts
    email_dupes_query = db.session.query(
        Contact.email,
        func.count(Contact.id).label('count')
    ).filter(
        Contact.id.in_(accessible_contact_ids)
    ).group_by(Contact.email).having(func.count(Contact.id) > 1)
    
    # Find duplicate mobiles within accessible contacts
    mobile_dupes_query = db.session.query(
        Contact.mobile,
        func.count(Contact.id).label('count')
    ).filter(
        Contact.id.in_(accessible_contact_ids)
    ).group_by(Contact.mobile).having(func.count(Contact.id) > 1)

    duplicate_emails = [row[0] for row in email_dupes_query.all()]
    duplicate_mobiles = [row[0] for row in mobile_dupes_query.all()]

    return jsonify({
        "duplicate_emails": duplicate_emails,
        "duplicate_mobiles": duplicate_mobiles
    })