from flask import Blueprint, request, jsonify
from models.sales_rule import SalesRule
from extensions import db
from routes.auth_routes import token_required
from datetime import datetime

sales_rules_bp = Blueprint("sales_rules", __name__)

@sales_rules_bp.route("/api/sales-rules", methods=["POST"])
@token_required
def create_sales_rule(current_user):
    data = request.get_json()

    if not data or not data.get('name') or not data.get('module'):
        return jsonify({"error": "name and module are required fields"}), 400

    rule = SalesRule(
        name=data["name"],
        module=data["module"],
        condition_field=data.get("condition_field"),
        condition_operator=data.get("condition_operator"),
        condition_value=data.get("condition_value"),
        action_type=data.get("action_type"),
        action_value=data.get("action_value"),
        priority=data.get("priority", 1),
        is_active=data.get("is_active", True),
        created_by=current_user.id,
        organization_id=current_user.organization_id
    )

    db.session.add(rule)
    db.session.commit()

    return jsonify({
        "message": "Sales rule created successfully",
        "rule_id": rule.id
    }), 201

@sales_rules_bp.route("/api/sales-rules", methods=["GET"])
@token_required
def get_sales_rules(current_user):
    rules = SalesRule.query.filter_by(organization_id=current_user.organization_id).order_by(SalesRule.priority).all()

    result = []
    for rule in rules:
        result.append({
            "id": rule.id,
            "name": rule.name,
            "module": rule.module,
            "condition_field": rule.condition_field,
            "condition_operator": rule.condition_operator,
            "condition_value": rule.condition_value,
            "action_type": rule.action_type,
            "action_value": rule.action_value,
            "priority": rule.priority,
            "is_active": rule.is_active
        })

    return jsonify(result)

@sales_rules_bp.route("/api/sales-rules/<int:id>", methods=["PUT"])
@token_required
def update_rule(current_user, id):
    rule = SalesRule.query.filter_by(id=id, organization_id=current_user.organization_id).first_or_404()
    data = request.get_json()

    rule.name = data.get("name", rule.name)
    rule.module = data.get("module", rule.module)
    rule.condition_field = data.get("condition_field", rule.condition_field)
    rule.condition_operator = data.get("condition_operator", rule.condition_operator)
    rule.condition_value = data.get("condition_value", rule.condition_value)
    rule.action_type = data.get("action_type", rule.action_type)
    rule.action_value = data.get("action_value", rule.action_value)
    rule.priority = data.get("priority", rule.priority)
    rule.is_active = data.get("is_active", rule.is_active)

    db.session.commit()
    return jsonify({"message": "Rule updated"})

@sales_rules_bp.route("/api/sales-rules/<int:id>", methods=["DELETE"])
@token_required
def delete_rule(current_user, id):
    rule = SalesRule.query.filter_by(id=id, organization_id=current_user.organization_id).first_or_404()

    db.session.delete(rule)
    db.session.commit()

    return jsonify({"message": "Rule deleted"})