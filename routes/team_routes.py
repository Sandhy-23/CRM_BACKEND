from flask import Blueprint, request, jsonify
from extensions import db
from models.team import Team, LocationTeamMapping
from models.user import User
from routes.auth_routes import token_required

team_bp = Blueprint('teams', __name__)

# --- TEAM API FOR FRONTEND ---

@team_bp.route('/api/team', methods=['GET'])
@token_required
def get_team_overview(current_user):
    """
    Returns team statistics and list of members for the Team Management page.
    """
    org_id = current_user.organization_id

    # 1. Fetch Members
    members = User.query.filter_by(organization_id=org_id, is_deleted=False).all()
    
    # 2. Calculate Stats
    total_members = len(members)
    active_members = sum(1 for m in members if m.status == 'Active')
    
    members_data = [{
        "id": m.id,
        "name": m.name,
        "role": m.role,
        "email": m.email,
        "status": m.status,
        "last_active": "Today" # Placeholder, or use m.last_active if available
    } for m in members]

    return jsonify({
        "stats": {
            "total_members": total_members,
            "active_members": active_members
        },
        "teamMembers": members_data
    }), 200

# --- EXISTING TEAM MANAGEMENT ROUTES ---

@team_bp.route('/api/teams', methods=['POST'])
@token_required
def create_team(current_user):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'message': 'Team name is required'}), 400
        
    team = Team(
        name=name,
        city=data.get('city'),
        state=data.get('state'),
        country=data.get('country')
    )
    db.session.add(team)
    db.session.commit()
    return jsonify({'message': 'Team created successfully', 'team_id': team.id}), 201

@team_bp.route('/api/teams', methods=['GET'])
@token_required
def get_teams(current_user):
    teams = Team.query.all()
    return jsonify([{
        'id': t.id, 'name': t.name, 'city': t.city, 'country': t.country
    } for t in teams]), 200

# STEP 3: Create Location -> Team Mapping
@team_bp.route('/api/location-mapping', methods=['POST'])
@token_required
def create_location_mapping(current_user):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    team_id = data.get('team_id')
    country = data.get('country') # Country is mandatory for mapping
    
    if not team_id or not country:
        return jsonify({'message': 'Team ID and Country are required'}), 400
        
    # City and State are optional (nullable)
    mapping = LocationTeamMapping(
        city=data.get('city'),
        state=data.get('state'),
        country=country,
        team_id=team_id
    )
    db.session.add(mapping)
    db.session.commit()
    return jsonify({'message': 'Location mapping created successfully', 'id': mapping.id}), 201