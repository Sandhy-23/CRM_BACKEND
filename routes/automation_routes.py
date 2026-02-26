from flask import Blueprint, request, jsonify
from models.automation import AutomationRule
from routes.auth_routes import token_required
from extensions import db
import json

automation_bp = Blueprint('automation_bp', __name__)

@automation_bp.route('/api/automation/rules', methods=['GET'])
@token_required
def get_rules(current_user):
    branch_id = request.args.get("branchId")

    # Always filter by the user's organization for security
    query = AutomationRule.query.filter_by(organization_id=current_user.organization_id)

    if branch_id:
        query = query.filter_by(branch_id=branch_id)
    rules = query.all()

    result = []
    for rule in rules:
        result.append({
            "id": rule.id,
            "name": rule.name,
            "trigger_event": rule.trigger_event,
            "status": rule.status,
            "conditions": json.loads(rule.conditions) if rule.conditions else [],
            "actions": json.loads(rule.actions) if rule.actions else []
        })

    return jsonify(result)

@automation_bp.route("/api/automation/rules", methods=["POST"])
@token_required
def create_rule(current_user):
    data = request.json

    print("[DEBUG] /api/automation/rules Body:", data)

    if not data.get("name"):
        return jsonify({"error": "Rule name required"}), 400

    new_rule = AutomationRule(
        name=data.get("name"),
        trigger_event=data.get("trigger_event"),
        conditions=json.dumps(data.get("conditions", [])),
        actions=json.dumps(data.get("actions", [])),
        branch_id=data.get("branch_id"),
        organization_id=current_user.organization_id,
        status=data.get("status", "active")
    )

    try:
        db.session.add(new_rule)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Rule created successfully"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database error", "message": str(e)}), 500