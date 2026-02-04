from flask import Blueprint, request, jsonify
from routes.auth_routes import token_required
from models.contact import Contact
from extensions import db
from sqlalchemy import text

contact_bp = Blueprint('contacts', __name__)

# --- Helper for backward compatibility ---
def get_contact_query(current_user):
    return Contact.query

# ➕ 1. Create Contact
@contact_bp.route('/api/contacts', methods=['POST'])
@token_required
def create_contact(current_user):
    data = request.get_json()

    new_contact = Contact(
        name=data.get("name"),
        company=data.get("company"),
        email=data.get("email"),
        phone=data.get('phone'),
        owner=data.get("owner"),
        last_contact=data.get("lastContact"),
        status=data.get("status"),
    )
    
    db.session.add(new_contact)
    db.session.commit()
    
    return jsonify({"message": "Contact created", "id": new_contact.id}), 201

# 📥 2. Get All Contacts
@contact_bp.route('/api/contacts', methods=['GET'])
@token_required
def get_contacts(current_user):
    contacts = Contact.query.order_by(Contact.id.desc()).all()
    
    return jsonify([{
        "id": c.id,
        "name": c.name,
        "company": c.company,
        "email": c.email,
        "phone": c.phone,
        "owner": c.owner,
        "lastContact": c.last_contact,
        "status": c.status
    } for c in contacts])

# 👤 3. Get Contact Profile
@contact_bp.route('/api/contacts/<int:contact_id>', methods=['GET'])
@token_required
def get_contact(current_user, contact_id):
    c = Contact.query.filter_by(id=contact_id).first_or_404()
    return jsonify({
        "id": c.id,
        "name": c.name,
        "company": c.company,
        "email": c.email,
        "phone": c.phone,
        "owner": c.owner,
        "lastContact": c.last_contact,
        "status": c.status
    })

# ✏️ 4. Update Contact
@contact_bp.route('/api/contacts/<int:contact_id>', methods=['PUT'])
@token_required
def update_contact(current_user, contact_id):
    c = Contact.query.get_or_404(contact_id)
    data = request.get_json()

    for field in ["name", "company", "email", "phone", "owner", "status"]:
        if field in data:
            setattr(c, field, data[field])

    if "lastContact" in data:
        c.last_contact = data["lastContact"]
    
    db.session.commit()
    return jsonify({"message": "Contact updated"})

# 🗑️ 5. Delete Contact (HARD DELETE)
@contact_bp.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
@token_required
def delete_contact(current_user, contact_id):
    c = Contact.query.get_or_404(contact_id)
    db.session.delete(c)
    db.session.commit()
    return jsonify({"message": "Contact deleted"})

# 🔍 6. Search Contacts
@contact_bp.route('/api/contacts/search', methods=['GET'])
@token_required
def search_contacts(current_user):
    q = request.args.get("q", "")
    contacts = Contact.query.filter(
        Contact.name.ilike(f"%{q}%")
    ).all()

    return jsonify([{"id": c.id, "name": c.name} for c in contacts])

@contact_bp.route('/api/contacts/duplicates', methods=['GET'])
@token_required
def find_duplicates(current_user):
    sql = text("""
        SELECT email, COUNT(*) FROM contacts
        GROUP BY email HAVING COUNT(*) > 1
    """)
    duplicates = db.session.execute(sql).fetchall()

    return jsonify([{"email": d[0], "count": d[1]} for d in duplicates])