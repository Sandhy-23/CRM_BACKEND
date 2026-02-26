from flask import Blueprint, jsonify
from extensions import db
from models.user import User
from models.organization import Organization
from models.branch import Branch
from routes.auth_routes import token_required

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    # Fetch Organization
    org = Organization.query.get(current_user.organization_id)

    # Fetch Active Branches for this Organization
    branches = Branch.query.filter_by(
        organization_id=current_user.organization_id,
        is_active=True
    ).all()

    active_branches = [b.name for b in branches]

    return jsonify({
        "user": {
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
            "phone": current_user.phone,
            "location": current_user.location,
            "joinedDate": current_user.date_of_joining.strftime("%B %Y") if current_user.date_of_joining else "N/A"
        },
        "organization": {
            "name": org.name if org else "N/A",
            "industry": org.industry if org else "",
            "website": org.website if org else "",
            "address": org.address if org else "",
            "totalEmployees": org.total_employees if org else 0,
            "founded": org.founded_year if org else "",
            "hq": org.hq if org else "",
            "legalName": org.legal_name if org else ""
        },
        "activeBranches": active_branches
    })