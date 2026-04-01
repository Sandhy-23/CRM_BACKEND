from flask import Blueprint, request, jsonify
from extensions import db
from models.organization import Organization
from routes.auth_routes import token_required
from datetime import datetime
from sqlalchemy import text, create_engine
from db import get_engine
from tenant_service import create_tenant_database, clone_database_structure, register_tenant, seed_tenant_data
import re

organization_bp = Blueprint('organization', __name__)

@organization_bp.route('/api/organization/setup', methods=['POST'])
@token_required
def setup_organization(current_user):
    """
    Sets up the organization details for the logged-in Super Admin or Admin.
    Updates the existing placeholder organization created during signup.
    """
    # 1. Access Control
    if current_user.role != 'Super Admin':
        return jsonify({"message": "Unauthorized. Only a Super Admin can setup the organization."}), 403

    data = request.get_json()
    print("STEP 1: received data")
    email = current_user.email
    master_engine = get_engine("master_db")
    
    org_name = data.get('organization_name') or data.get('name')
    if not org_name:
        return jsonify({"error": "Organization name is required"}), 400

    try:
        # 🔹 STEP 1 & 2: Check if user already has tenant in registry
        with master_engine.connect() as conn:
            existing = conn.execute(text("""
                SELECT * FROM tenant_registry WHERE super_admin_email = :email
            """), {"email": email}).fetchone()
            
            if existing:
                return jsonify({"message": "Organization already exists for this user"}), 400

        # 🔹 STEP 3 & 4: Generate DB name based on Organization Name
        # Format: tenant_org_name (lowercase, spaces to underscores)
        tenant_db_name = f"tenant_{org_name.strip().lower().replace(' ', '_')}"

        # Update the Organization model in the current session
        # This part is still needed to update the Organization table itself
        # (which is different from tenant_registry)
        # Find or Create Organization (existing logic)
        organization = None
        if current_user.organization_id:
            organization = Organization.query.get(current_user.organization_id)

        print("STEP 3: inserting/updating organization")

        if not organization:
            # Check if an organization already exists for this user (created_by)
            existing_org = Organization.query.filter_by(created_by=current_user.id).first()
            if existing_org:
                return jsonify({
                    "status": "error",
                    "message": "Organization already exists for this user"
                }), 400

            # Create new organization (First time setup for Super Admin)
            organization = Organization()
            db.session.add(organization)

        # 4. Update Organization Data
        # Mapping 'organization_size' from request to 'company_size' in DB as per requirements
        organization.name = org_name
        organization.company_size = data.get('organization_size') # Mapped field
        organization.industry = data.get('industry')
        organization.phone = data.get('phone')
        organization.country = data.get('country')
        organization.state = data.get('state')
        organization.city_or_branch = data.get('city_or_branch')
        organization.db_name = tenant_db_name  # Save the generated DB name
        
        # Meta fields
        if not organization.created_by:
            organization.created_by = current_user.id
        organization.updated_at = datetime.utcnow()

        # Explicit commit for the SQLAlchemy session
        db.session.commit()
        print("STEP 4: insert/update executed")
        print("STEP 5: committed")

        print("STEP 2: creating DB and cloning structure")
        
        # 🔹 STEP 5: Infrastructure Creation
        create_tenant_database(tenant_db_name)
        
        # 🔹 STEP 6: Clone structure from crm_db (Source of Truth)
        clone_database_structure(tenant_db_name, source_db="crm_db")

        # 🔹 STEP 7 & 8: Seed Admin and Defaults (Handled in service)
        seed_tenant_data(tenant_db_name, email)

        # 🔹 STEP 9: Save tenant registry
        # register_tenant updated to use the generated domain
        register_tenant(org_name, tenant_db_name, email)
        # Overriding internal registry call to ensure domain matches the org slug
        with master_engine.begin() as conn:
            conn.execute(text("""
                UPDATE tenant_registry SET tenant_domain = :domain 
                WHERE tenant_db_name = :db
            """), {"domain": org_name.lower().replace(' ', ''), "db": tenant_db_name})

        # ✅ FINAL VERIFICATION: Force direct SQL insert/update into crm_db
        try:
            print("STEP 6: Running direct SQL verify on crm_db")
            db.session.execute(
                text("UPDATE organizations SET name = :name, db_name = :db_name WHERE id = :id"),
                {"name": org_name, "db_name": tenant_db_name, "id": organization.id}
            )
            db.session.commit()
            
            # Verify current DB name
            current_db = db.session.execute(text("SELECT DATABASE()")).scalar()
            print(f"DEBUG: Current Database is {current_db}")
            print("STEP 7: Direct SQL committed")
        except Exception as e:
            print(f"⚠️ Manual update of organization name failed: {e}")

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