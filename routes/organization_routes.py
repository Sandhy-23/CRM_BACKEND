from flask import Blueprint, request, jsonify
from extensions import db
from models.organization import Organization
from routes.auth_routes import token_required
from datetime import datetime

organization_bp = Blueprint('organization', __name__)

@organization_bp.route('/organization/setup', methods=['POST'])
@token_required
def setup_organization(current_user):
    """
    Sets up the organization details for the logged-in Super Admin or Admin.
    Updates the existing placeholder organization created during signup.
    """
    # 1. Access Control
    if current_user.role != 'SUPER_ADMIN':
        return jsonify({"message": "Unauthorized. Only a Super Admin can setup the organization."}), 403

    data = request.get_json()
    
    # 2. Validate Required Fields
    required_fields = ['organization_name', 'organization_size', 'industry', 'country']
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        return jsonify({"error": "Validation Error", "message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # 3. Find or Create Organization
    organization = None
    if current_user.organization_id:
        organization = Organization.query.get(current_user.organization_id)

    if not organization:
        # Create new organization (First time setup for Super Admin)
        organization = Organization()
        db.session.add(organization)

    # 4. Update Organization Data
    # Mapping 'organization_size' from request to 'company_size' in DB as per requirements
    try:
        organization.name = data.get('organization_name')
        organization.company_size = data.get('organization_size') # Mapped field
        organization.industry = data.get('industry')
        organization.phone = data.get('phone')
        organization.country = data.get('country')
        organization.state = data.get('state')
        organization.city_or_branch = data.get('city_or_branch')
        
        # Meta fields
        if not organization.created_by:
            organization.created_by = current_user.id
        organization.updated_at = datetime.utcnow()

        db.session.commit()

        # Link Super Admin to this Organization if not already linked
        if not current_user.organization_id:
            current_user.organization_id = organization.id
            db.session.commit()

        return jsonify({
            "message": "Organization setup completed successfully",
            "organization": {
                "id": organization.id,
                "name": organization.name
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Database Error in Organization Setup: {e}")
        return jsonify({"error": "Database error", "message": str(e)}), 500