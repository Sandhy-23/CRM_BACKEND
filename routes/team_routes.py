from flask import Blueprint, request, jsonify
from extensions import db
from models.team import Team, LocationTeamMapping
from routes.auth_routes import token_required

team_bp = Blueprint('teams', __name__)

# STEP 1: Create Teams
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