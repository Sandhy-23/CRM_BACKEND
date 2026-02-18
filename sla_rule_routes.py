from flask import Blueprint, request, jsonify
from extensions import db
from models.sla_rule import SLARule
from routes.auth_routes import token_required

sla_rule_bp = Blueprint('sla_rule_bp', __name__)

@sla_rule_bp.route('/api/sla-rules', methods=['POST'])
@token_required
def create_sla_rule(current_user):
    data = request.get_json()
    
    priority = data.get('priority')
    response_time = data.get('response_time_hours')
    resolution_time = data.get('resolution_time_hours')
    
    if not priority or resolution_time is None:
        return jsonify({'message': 'Priority and Resolution Time are required'}), 400
        
    # Check if rule exists for this priority
    existing_rule = SLARule.query.filter_by(priority=priority).first()
    
    if existing_rule:
        existing_rule.response_time_hours = response_time
        existing_rule.resolution_time_hours = resolution_time
        message = 'SLA Rule updated'
    else:
        new_rule = SLARule(
            priority=priority,
            response_time_hours=response_time or 0,
            resolution_time_hours=resolution_time
        )
        db.session.add(new_rule)
        message = 'SLA Rule created'
        
    db.session.commit()
    return jsonify({'message': message, 'priority': priority}), 201

@sla_rule_bp.route('/api/sla-rules', methods=['GET'])
@token_required
def get_sla_rules(current_user):
    rules = SLARule.query.all()
    return jsonify([{
        'id': r.id,
        'priority': r.priority,
        'response_time_hours': r.response_time_hours,
        'resolution_time_hours': r.resolution_time_hours
    } for r in rules]), 200