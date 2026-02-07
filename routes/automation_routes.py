from flask import Blueprint, request, jsonify
from extensions import db
from models.automation import AutomationRule, AutomationCondition, AutomationAction, AutomationLog
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
    if not all(k in data for k in ('rule_name', 'trigger_type')):
        return jsonify({'message': 'Missing required fields'}), 400
        
    new_rule = AutomationRule(
        rule_name=data['rule_name'],
        description=data.get('description'),
        trigger_type=data['trigger_type'],
        trigger_from=data.get('trigger_from'),
        trigger_to=data.get('trigger_to'),
        condition_logic=data.get('condition_logic', 'AND'),
        priority=data.get('priority', 1),
        stop_processing=data.get('stop_processing', False),
        is_active=data.get('is_active', True),
        company_id=current_user.organization_id
    )
    
    try:
        db.session.add(new_rule)
        db.session.flush() # Get ID
        
        # Add Conditions
        if 'conditions' in data:
            for cond in data['conditions']:
                new_cond = AutomationCondition(
                    rule_id=new_rule.id,
                    field=cond['field'],
                    operator=cond['operator'],
                    value=cond['value']
                )
                db.session.add(new_cond)
                
        # Add Actions
        if 'actions' in data:
            for act in data['actions']:
                new_act = AutomationAction(
                    rule_id=new_rule.id,
                    action_type=act['action_type'],
                    action_value=act.get('action_value')
                )
                db.session.add(new_act)
        
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
    ).order_by(AutomationRule.priority.asc()).all()
    
    return jsonify([r.to_dict() for r in rules]), 200

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

@automation_bp.route('/automation/logs', methods=['GET'])
@token_required
def get_logs(current_user):
    lead_id = request.args.get('lead_id')
    
    # Explicit join condition required since rule_id is not strictly a ForeignKey in the DB schema yet
    query = AutomationLog.query.join(AutomationRule, AutomationLog.rule_id == AutomationRule.id).filter(AutomationRule.company_id == current_user.organization_id)
    
    if lead_id: query = query.filter(AutomationLog.lead_id == lead_id)
    
    logs = query.order_by(AutomationLog.created_at.desc()).limit(50).all()
    return jsonify([l.to_dict() for l in logs]), 200