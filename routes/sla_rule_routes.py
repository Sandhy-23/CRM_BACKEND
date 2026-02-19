from flask import Blueprint, jsonify, request

# Blueprint must be defined at TOP LEVEL
sla_rule_bp = Blueprint("sla_rule", __name__, url_prefix="/api/sla-rules")


@sla_rule_bp.route("/", methods=["GET"])
def get_sla_rules():
    return jsonify({"message": "SLA Rules working"})


@sla_rule_bp.route("/", methods=["POST"])
def create_sla_rule():
    data = request.json
    return jsonify({"message": "SLA Rule created", "data": data})