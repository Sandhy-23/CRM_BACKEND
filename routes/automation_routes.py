from flask import Blueprint, request, jsonify
from extensions import db
from models.automation import Automation, AutomationRule, AutomationAction
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

# --- Automations CRUD ---
@automation_bp.route('/automations', methods=['POST'])
@token_required
def create_automation(current_user):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    
    new_automation = Automation(
        name=data.get('name', 'Untitled Automation'),
        trigger_event=data.get('trigger_event'),
        is_active=data.get('is_active', True),
        company_id=current_user.organization_id
    )
    
    try:
        db.session.add(new_automation)
        db.session.flush() # Get ID
        
        # Add Rules
        for r in data.get('rules', []):
            rule = AutomationRule(automation_id=new_automation.id, field=r['field'], operator=r['operator'], value=r['value'])
            db.session.add(rule)
            
        # Add Actions
        for a in data.get('actions', []):
            action = AutomationAction(automation_id=new_automation.id, action_type=a['action_type'], action_value=a['action_value'])
            db.session.add(action)
            
        db.session.commit()
        return jsonify({'message': 'Automation created', 'automation': new_automation.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@automation_bp.route('/automations', methods=['GET'])
@token_required
def get_automations(current_user):
    automations = Automation.query.filter_by(
        company_id=current_user.organization_id
    ).all()
    
    return jsonify([a.to_dict() for a in automations]), 200

@automation_bp.route('/automation/rules/<int:rule_id>/toggle', methods=['PUT'])
@token_required
def toggle_rule(current_user, rule_id):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    rule = AutomationRule.query.filter_by(id=rule_id, company_id=current_user.organization_id).first()
    if not rule:
        return jsonify({'message': 'Rule not found'}), 404
        
    rule.is_active = not rule.is_active
    db.session.commit()
    
    return jsonify({'message': f'Rule {"enabled" if rule.is_active else "disabled"}', 'is_active': rule.is_active}), 200