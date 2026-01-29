from flask import Blueprint, request, jsonify
from extensions import db
from models.automation_rule import AutomationRule
from routes.auth_routes import token_required
import json

automation_bp = Blueprint('automation', __name__)

# --- Health Check (Requested) ---
@automation_bp.route("/api/automation/health", methods=["GET"])
def automation_health():
    return jsonify({"status": "automation module working"})

# --- Test Endpoint ---
@automation_bp.route("/automation/test", methods=["GET"])
def automation_test():
    return {"message": "Automation module working"}, 200

# --- Automation Rules CRUD ---
@automation_bp.route('/automation-rules', methods=['POST'])
@token_required
def create_rule(current_user):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ('name', 'module', 'trigger_event', 'actions')):
        return jsonify({'message': 'Missing required fields'}), 400
        
    new_rule = AutomationRule(
        name=data['name'],
        module=data['module'],
        trigger_event=data['trigger_event'],
        # Convert dict/list to JSON string for storage
        conditions=json.dumps(data.get('conditions', {})),
        actions=json.dumps(data['actions']),
        is_active=data.get('is_active', True),
        company_id=current_user.organization_id,
        created_by=current_user.id
    )
    
    try:
        db.session.add(new_rule)
        db.session.commit()
        return jsonify({'message': 'Automation rule created', 'rule': new_rule.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@automation_bp.route('/automation-rules', methods=['GET'])
@token_required
def get_rules(current_user):
    rules = AutomationRule.query.filter_by(
        company_id=current_user.organization_id
    ).order_by(AutomationRule.created_at.desc()).all()
    
    return jsonify([r.to_dict() for r in rules]), 200