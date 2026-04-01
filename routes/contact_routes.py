from flask import Blueprint, request, jsonify
from extensions import db
from models.contact import Contact
from routes.auth_routes import token_required
from sqlalchemy import or_

contact_bp = Blueprint('contact_bp', __name__)

# ✅ STEP 1: VERIFY ROUTE EXISTS (GET Single Contact)
@contact_bp.route("/<int:contact_id>", methods=["GET", "PUT", "DELETE"])
@token_required
def get_contact(current_user, contact_id):
    try:
        # Ensure contact belongs to organization and is not already deleted
        contact = Contact.query.filter(
            Contact.id == contact_id,
            Contact.organization_id == current_user.organization_id,
            or_(Contact.is_deleted == False, Contact.is_deleted.is_(None))
        ).first()

        if not contact:
            return jsonify({"error": "Contact not found"}), 404

        if request.method == "DELETE":
            contact.is_deleted = True
            db.session.commit()
            return jsonify({"message": "Contact deleted successfully"}), 200

        if request.method == "PUT":
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Update fields
            contact.name = data.get("name", contact.name)
            contact.email = data.get("email", contact.email)
            contact.phone = data.get("phone", contact.phone)
            contact.company = data.get("company", contact.company)
            contact.owner = data.get("owner", contact.owner)
            contact.status = data.get("status", contact.status)
            
            db.session.commit()
            return jsonify({"message": "Contact updated successfully"}), 200

        # Default: GET
        return jsonify({
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "company": contact.company,
            "owner": contact.owner,
            "status": contact.status,
            "lastContact": contact.last_contact
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Get All Contacts
@contact_bp.route("", methods=["GET"])
@token_required
def get_contacts(current_user):
    try:
        # FIX: Handle NULL values for organization_id and is_deleted as per Option 2 (Messy Data Fix)
        contacts = Contact.query.filter(
            or_(Contact.organization_id == current_user.organization_id, Contact.organization_id.is_(None)),
            or_(Contact.is_deleted == False, Contact.is_deleted.is_(None))
        ).all()

        print(f"DEBUG CONTACTS FOUND: {len(contacts)}")
        
        result = [{
            "id": c.id,
            "name": c.name,
            "company": c.company,
            "email": c.email,
            "phone": c.phone,
            "owner": c.owner if c.owner else "Unassigned",
            "lastContact": c.last_contact if c.last_contact else "Never",
            "status": c.status if c.status else "New"
        } for c in contacts]

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create Contact
@contact_bp.route("", methods=["POST"])
@token_required
def create_contact(current_user):
    try:
        data = request.get_json()
        
        new_contact = Contact(
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            company=data.get("company"),
            owner=data.get("owner"),
            status=data.get("status", "New"),
            last_contact=data.get("lastContact"),
            organization_id=current_user.organization_id
        )

        db.session.add(new_contact)
        db.session.commit()

        return jsonify({"message": "Contact created", "id": new_contact.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Search Contacts
@contact_bp.route("/search", methods=["GET"])
@token_required
def search_contacts(current_user):
    query = request.args.get("q", "")
    if not query:
        return jsonify([])

    contacts = Contact.query.filter(
        Contact.organization_id == current_user.organization_id,
        Contact.is_deleted == False,
        or_(
            Contact.name.ilike(f"%{query}%"),
            Contact.email.ilike(f"%{query}%"),
            Contact.company.ilike(f"%{query}%")
        )
    ).limit(10).all()

    result = [{
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "company": c.company
    } for c in contacts]

    return jsonify(result)