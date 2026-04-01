from flask import Blueprint, request, jsonify
from extensions import db
from models.automation import AutomationRule
from models.enterprise_rule import EnterpriseRule
import json

automation_bp = Blueprint('automation', __name__)

@automation_bp.route('/rules', methods=['GET'])
def get_rules():
    try:
        branch_id = request.args.get('branchId')
        
        # Start query
        query = AutomationRule.query
        
        # Filter by branch if provided
        if branch_id:
            query = query.filter_by(branch_id=branch_id)

        # Your model uses 'status' (string), not 'active' (int/bool).
        # If you want only active rules: query = query.filter_by(status='active')
        
        rules = query.all()
        
        results = []
        for r in rules:
            # Parse JSON fields stored as text
            conditions = r.conditions
            actions = r.actions
            try:
                if conditions and isinstance(conditions, str):
                    conditions = json.loads(conditions)
                if actions and isinstance(actions, str):
                    actions = json.loads(actions)
            except:
                pass # Keep as string or whatever it is on error

            results.append({
                "id": r.id,
                "name": r.name,
                "status": r.status,
                "trigger": r.trigger_event,
                "conditions": conditions,
                "actions": actions,
                "branch_id": r.branch_id
            })

        return jsonify(results), 200
    except Exception as e:
        print(f"Error getting rules: {e}")
        return jsonify({"error": str(e)}), 500

@automation_bp.route('/rules', methods=['POST'])
def create_rule():
    try:
        data = request.get_json()
        
        # Handle JSON serialization for DB storage
        conditions = data.get('conditions')
        if isinstance(conditions, (dict, list)):
            conditions = json.dumps(conditions)
            
        actions = data.get('actions')
        if isinstance(actions, (dict, list)):
            actions = json.dumps(actions)

        new_rule = AutomationRule(
            name=data.get('name'),
            branch_id=data.get('branch_id'),
            organization_id=data.get('organization_id', 1),
            status=data.get('status', 'active'),
            trigger_event=data.get('trigger'),
            conditions=conditions,
            actions=actions
        )
        
        db.session.add(new_rule)
        db.session.commit()
        
        return jsonify({"message": "Rule created successfully", "id": new_rule.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@automation_bp.route('/rules/<int:rule_id>', methods=['PUT', 'DELETE'])
def manage_rule(rule_id):
    try:
        rule = AutomationRule.query.get(rule_id)
        if not rule:
            return jsonify({"error": "Rule not found"}), 404

        if request.method == 'DELETE':
            db.session.delete(rule)
            db.session.commit()
            return jsonify({"message": "Rule deleted"}), 200
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            rule.name = data.get('name', rule.name)
            rule.status = data.get('status', rule.status)
            rule.trigger_event = data.get('trigger', rule.trigger_event)
            
            if 'conditions' in data:
                conditions = data['conditions']
                if isinstance(conditions, (dict, list)):
                    conditions = json.dumps(conditions)
                rule.conditions = conditions
                
            if 'actions' in data:
                actions = data['actions']
                if isinstance(actions, (dict, list)):
                    actions = json.dumps(actions)
                rule.actions = actions
                
            db.session.commit()
            return jsonify({"message": "Rule updated"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@automation_bp.route("/enterprise-rules", methods=["GET"])
def get_enterprise_rules():
    try:
        rules = EnterpriseRule.query.all()
        return jsonify([rule.to_dict() for rule in rules]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500