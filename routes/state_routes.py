from flask import Blueprint, jsonify
from extensions import db
from models.state import State
from models.branch import Branch
from routes.auth_routes import token_required

state_bp = Blueprint('state', __name__)

@state_bp.route('/api/states', methods=['GET'])
@token_required
def get_states(current_user):
    states = State.query.filter_by(
        organization_id=current_user.organization_id
    ).all()

    response = []

    for state in states:
        branches = Branch.query.filter_by(
            state_id=state.id
        ).all()

        response.append({
            "id": state.id,
            "name": state.name,
            "description": state.description,
            "theme": state.theme,
            "branches": [
                {
                    "id": branch.id,
                    "name": branch.name,
                    "manager": branch.manager_name
                } for branch in branches
            ]
        })

    return jsonify(response)